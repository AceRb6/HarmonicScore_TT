"""
Tareas asincronas (Celery) para el procesamiento de audio.

Flujo:
  Django guarda el audio (PENDIENTE) -> encola procesar_audio ->
  el worker envia el audio al ml-service (otra maquina de la red) ->
  consulta el estado hasta que termine -> descarga el PDF ->
  lo guarda en media/audios/pdf/ y marca EXITO / ERROR ->
  publica evento push (Redis Pub/Sub) para actualizar la tabla del frontend
  unicamente en el instante en que el worker reporta fallo o completado.

La URL del ml-service se toma de la variable de entorno ML_SERVICE_URL
(ej. http://192.168.1.50:8000). Ver docker-compose.yml / .env.
"""
import json
import os
import time
import logging
from urllib.parse import unquote
from django.utils.text import slugify
from datetime import datetime
import redis
import requests
from celery import shared_task
from django.conf import settings
from django.core.files.base import ContentFile

from .models import Transcripcion

log = logging.getLogger(__name__)

ML_SERVICE_URL = os.environ.get('ML_SERVICE_URL', 'http://127.0.0.1:8000').rstrip('/')
INTERVALO_POLLING_S = int(os.environ.get('ML_POLL_INTERVAL', '5'))
TIEMPO_MAXIMO_S = int(os.environ.get('ML_TIMEOUT', '1800'))  # 30 min


def _notificar_evento_worker(t: Transcripcion):
    """
    Publica en Redis Pub/Sub cuando el worker termina (EXITO o ERROR),
    para que el endpoint SSE de Django despierte al navegador y actualice
    la tabla solo cuando cambia a completado o fallido (sin polling).
    """
    try:
        redis_url = getattr(settings, 'CELERY_BROKER_URL', os.environ.get('CELERY_BROKER_URL', 'redis://redis:6379/0'))
        cliente = redis.Redis.from_url(redis_url, decode_responses=True)
        canal = f"hs:eventos:usuario:{t.usuario_id}"
        payload = json.dumps({
            'job_id': str(t.id),
            'titulo': t.titulo_audio,
            'estado': 'completado' if t.estado == 'EXITO' else 'error',
            'estado_db': t.estado,
        })
        cliente.publish(canal, payload)
    except Exception as exc:
        log.warning("No se pudo publicar evento SSE para transcripcion %s: %s", t.id, exc)


def _filename_de(disposition, fallback: str) -> str:
    """Extrae el nombre del header Content-Disposition sin 're'."""
    if not disposition:
        return fallback
    m = "filename*="
    i = disposition.find(m)
    if i != -1:
        resto = disposition[i + len(m):].split(";")[0].strip()
        if "''" in resto:
            resto = resto.split("''", 1)[1]
        return unquote(resto.strip().strip('"'))
    m = "filename="
    i = disposition.find(m)
    if i == -1:
        return fallback
    return disposition[i + len(m):].split(";")[0].strip().strip('"')


def _marcar_error(t: Transcripcion, mensaje: str):
    t.estado = 'ERROR'
    t.detalles_error = mensaje[:2000]
    t.save(update_fields=['estado', 'detalles_error', 'fecha_completado'])
    log.error("Transcripcion %s fallo: %s", t.id, mensaje)
    _notificar_evento_worker(t)


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

    # 2. Polling del estado entre el worker y el ml-service
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

    # 3. Descargar el PDF y el MusicXML y guardarlos en media/
    try:
        pdf = requests.get(f"{ML_SERVICE_URL}/api/download/{ml_job_id}?format=pdf", timeout=120)
        pdf.raise_for_status()

        xml = requests.get(f"{ML_SERVICE_URL}/api/download/{ml_job_id}?format=xml", timeout=120)
        xml.raise_for_status()
    except requests.RequestException as e:
        return _marcar_error(t, f'No se pudo descargar los archivos: {e}')

    base_limpio = slugify(t.titulo_audio, allow_unicode=False)
    if not base_limpio:
        base_limpio = f"transcripcion_{t.id}"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_pdf = f"{base_limpio}_harmonic_score_{timestamp}.pdf"
    nombre_xml = f"{base_limpio}_harmonic_score_{timestamp}.musicxml"

    t.ruta_archivo_pdf.save(nombre_pdf, ContentFile(pdf.content), save=False)
    t.ruta_archivo_mxl.save(nombre_xml, ContentFile(xml.content), save=False)

    metrics = estado.get('metrics') or {}
    score = metrics.get('harmonic_score')
    if isinstance(score, (int, float)):
        t.harmonic_score = float(score)

    t.estado = 'EXITO'
    t.detalles_error = None
    t.save()

    # 4. Notificar al frontend que la transcripcion ya esta completa
    _notificar_evento_worker(t)
