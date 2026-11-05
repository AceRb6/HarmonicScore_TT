"""
Tareas asincronas (Celery) para el procesamiento de audio.

Flujo:
  Django guarda el audio (PENDIENTE) -> encola procesar_audio ->
  el worker envia el audio al ml-service (otra maquina de la red) ->
  consulta el estado hasta que termine -> descarga el PDF ->
  lo guarda en media/audios/pdf/ y marca EXITO / ERROR.

La URL del ml-service se toma de la variable de entorno ML_SERVICE_URL
(ej. http://192.168.1.50:8000). Ver docker-compose.yml / .env.

NOTA de naming (RF-06 / CU-06): el nombre final del archivo NO se reconstruye
aquí. La capa de dominio (ml-service) ya decidió el patrón
{nombre_original}_harmonic_score_{timestamp}; Django lo HEREDA del header
Content-Disposition de la respuesta de descarga (Ilustración 39), replicando el
contrato que ya respeta un navegador. Esto elimina la duplicación de heurísticas
de saneado entre microservicios y el sufijo opaco anti-colisión que Django
inyectaba al re-guardar archivos homónimos (que ocupaba el puesto del timestamp).
"""
import os
import time
import logging
from urllib.parse import unquote   # <-- CAMBIO: stdlib, sin 're'

import requests
from celery import shared_task
from django.core.files.base import ContentFile

from .models import Transcripcion

log = logging.getLogger(__name__)

ML_SERVICE_URL = os.environ.get('ML_SERVICE_URL', 'http://127.0.0.1:8000').rstrip('/')
INTERVALO_POLLING_S = int(os.environ.get('ML_POLL_INTERVAL', '5'))
TIEMPO_MAXIMO_S = int(os.environ.get('ML_TIMEOUT', '1800'))  # 30 min


def _filename_de(disposition, fallback: str) -> str:
    """Extrae el nombre del header Content-Disposition sin 're'.
    Soporta filename="ascii" y filename*=UTF-8''<percent-encoded> (RFC 5987).
    Si el header falta o no trae filename, devuelve el fallback (único por t.id,
    que es UUID => nunca colisiona => Django no mete '_XXXXXXX')."""
    if not disposition:
        return fallback
    # RFC 5987 (no-ASCII): filename*=UTF-8''<codificado>  (tiene prioridad)
    m = "filename*="
    i = disposition.find(m)
    if i != -1:
        resto = disposition[i + len(m):].split(";")[0].strip()
        if "''" in resto:
            resto = resto.split("''", 1)[1]
        return unquote(resto.strip().strip('"'))
    # Clásico: filename="..."  (o sin comillas)
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
        detalle = r.json.get('detail', r.text) if r.headers.get('content-type', '').startswith('application/json') else r.text
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

    # 3. Descargar el PDF y el MusicXML y guardarlos en media/
    try:
        pdf = requests.get(f"{ML_SERVICE_URL}/api/download/{ml_job_id}?format=pdf", timeout=120)
        pdf.raise_for_status()

        xml = requests.get(f"{ML_SERVICE_URL}/api/download/{ml_job_id}?format=xml", timeout=120)
        xml.raise_for_status()
    except requests.RequestException as e:
        return _marcar_error(t, f'No se pudo descargar los archivos: {e}')

    # <-- CAMBIO: hereda el nombre RF-06 del ml-service (no lo reinventa).
    # Fallback único por t.id (UUID): nunca colisiona => Django no mete '_XXXXXXX'.
    # El log DIAG es TEMPORAL: confirma una vez que el header llega limpio y bórralo.
    log.info("DIAG content-disposition pdf=%r xml=%r",
             pdf.headers.get("content-disposition"),
             xml.headers.get("content-disposition"))

    fb = f"{t.id}_harmonic_score"
    nombre_pdf = _filename_de(pdf.headers.get("content-disposition"), fb + ".pdf")
    nombre_xml = _filename_de(xml.headers.get("content-disposition"), fb + ".musicxml")

    t.ruta_archivo_pdf.save(nombre_pdf, ContentFile(pdf.content), save=False)
    t.ruta_archivo_mxl.save(nombre_xml, ContentFile(xml.content), save=False)

    metrics = estado.get('metrics') or {}
    score = metrics.get('harmonic_score')
    if isinstance(score, (int, float)):
        t.harmonic_score = float(score)

    t.estado = 'EXITO'
    t.detalles_error = None
    t.save()