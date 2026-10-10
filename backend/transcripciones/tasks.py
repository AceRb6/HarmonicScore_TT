"""
Tareas asincronas (Celery) para el procesamiento de audio.

Flujo:
  Django guarda el audio (PENDIENTE) -> encola procesar_audio ->
  el worker envia el audio al ml-service (otra maquina de la red) ->
  consulta el estado hasta que termine -> descarga el PDF ->
  lo guarda en media/audios/pdf/ y marca EXITO / ERROR.

La URL del ml-service se toma de la variable de entorno ML_SERVICE_URL
(ej. http://192.168.1.50:8000). Ver docker-compose.yml / .env.
"""
import os
import time
import logging

import requests
from celery import shared_task
from django.core.files.base import ContentFile

from .models import Transcripcion

log = logging.getLogger(__name__)

ML_SERVICE_URL = os.environ.get('ML_SERVICE_URL', 'http://127.0.0.1:8000').rstrip('/')
INTERVALO_POLLING_S = int(os.environ.get('ML_POLL_INTERVAL', '5'))
TIEMPO_MAXIMO_S = int(os.environ.get('ML_TIMEOUT', '1800'))  # 30 min


def _marcar_error(t: Transcripcion, mensaje: str):
    t.estado = 'ERROR'
    t.detalles_error = mensaje[:2000]
    t.save(update_fields=['estado', 'detalles_error', 'fecha_completado'])
    log.error("Transcripcion %s fallo: %s", t.id, mensaje)


@shared_task(bind=True)
def procesar_audio(self, transcripcion_id: str):
    try:
        t = Transcripcion.objects.get(id=transcripcion_id)
    except Transcripcion.DoesNotExist:
        log.error("Transcripcion %s no existe", transcripcion_id)
        return

    t.estado = 'PROCESANDO'
    t.save(update_fields=['estado', 'fecha_completado'])

    # 1. Enviar audio al ml-service
    try:
        with t.ruta_audio_original.open('rb') as f:
            nombre = os.path.basename(t.ruta_audio_original.name)
            r = requests.post(
                f'{ML_SERVICE_URL}/api/transcribe',
                files={'audio': (nombre, f)},
                data={'user_id': str(t.usuario_id)},
                timeout=120,
            )
    except requests.RequestException as e:
        return _marcar_error(t, f'No se pudo conectar con el servicio ML ({ML_SERVICE_URL}): {e}')

    if r.status_code not in (200, 202):
        detalle = r.json().get('detail', r.text) if r.headers.get('content-type', '').startswith('application/json') else r.text
        return _marcar_error(t, f'El servicio ML rechazo el audio: {detalle}')

    ml_job_id = r.json().get('job_id')
    if not ml_job_id:
        return _marcar_error(t, 'El servicio ML no devolvio job_id')

    # 2. Polling del estado
    inicio = time.time()
    while True:
        if time.time() - inicio > TIEMPO_MAXIMO_S:
            return _marcar_error(t, 'Tiempo de procesamiento excedido')
        time.sleep(INTERVALO_POLLING_S)
        try:
            s = requests.get(f'{ML_SERVICE_URL}/api/transcribe/{ml_job_id}', timeout=30)
            s.raise_for_status()
            estado = s.json()
        except requests.RequestException as e:
            log.warning("Polling fallo (%s), reintentando...", e)
            continue

        if estado.get('status') == 'processing':
            continue
        if estado.get('status') == 'failed':
            return _marcar_error(t, estado.get('detail') or 'Error en el procesamiento')
        if estado.get('status') == 'completed':
            break

    # 3. Descargar el PDF y guardarlo en media/audios/pdf/
    try:
        pdf = requests.get(f"{ML_SERVICE_URL}{estado.get('pdf_url', f'/api/download/{ml_job_id}')}", timeout=120)
        pdf.raise_for_status()
    except requests.RequestException as e:
        return _marcar_error(t, f'No se pudo descargar el PDF: {e}')

    base = os.path.splitext(t.titulo_audio)[0]
    t.ruta_archivo_pdf.save(f'{base}_harmonic_score.pdf', ContentFile(pdf.content), save=False)

    metrics = estado.get('metrics') or {}
    score = metrics.get('harmonic_score')
    if isinstance(score, (int, float)):
        t.harmonic_score = float(score)

    t.estado = 'EXITO'
    t.detalles_error = None
    t.save()
    log.info("Transcripcion %s completada", t.id)
