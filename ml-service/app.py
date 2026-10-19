"""Harmonic Score — ml-service. Contrato REST según Ilustración 39 del reporte."""
import json
import logging
import datetime
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

import settings as config
from jobs import JobManager, JobStatus
from pipeline.orchestrator import Orchestrator
from pipeline import model_stage

import librosa

def validar_duracion(path: Path, max_segundos: int = 360):
    """Valida que el audio no exceda la duración máxima (RF-04)."""
    try:
        duracion = librosa.get_duration(path=str(path))
        if duracion > max_segundos:
            # Eliminamos el archivo antes de lanzar el error para no dejar basura
            path.unlink(missing_ok=True)
            raise HTTPException(
                400, 
                f"Duración excedida. El archivo no debe superar los {max_segundos//60} minutos."
            )
    except Exception as e:
        path.unlink(missing_ok=True) # Limpieza en caso de error de librosa
        if "duration" in str(e).lower():
            raise HTTPException(400, "No se pudo determinar la duración del audio")
        raise

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("ml-service")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Precarga del modelo en startup; fallback a baseline si falla."""
    if config.MODEL_BACKEND == "real":
        log.info("Precargando modelo en startup...")
        try:
            model_stage.RealModel.get()
            log.info("Modelo precargado exitosamente")
        except Exception as e:
            log.error("Error precargando modelo: %s", e)
            log.warning("Cambiando a baseline por error de carga")
            config.MODEL_BACKEND = "baseline"
    yield


app = FastAPI(title="Harmonic Score ML Service", version="0.3.0", lifespan=lifespan)

# <-- CORREGIDO: Se agrega '*' o la IP de tu red local para evitar bloqueos del navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*", # Permite cualquier origen en desarrollo (cambiar a lista específica en producción)
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://10.100.79.61:8001", # Tu IP de red local
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs = JobManager()
orch = Orchestrator()
AUDIT = config.LOG_DIR / "audit.jsonl"          # RF-15


def audit(entry: dict):
    # Aseguramos que el directorio exista antes de escribir
    config.LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(AUDIT, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


@app.get("/")
def root():
    return {"service": "ml-service", "status": "ok", "device": str(config.DEVICE)}


@app.post("/api/transcribe", status_code=202)
async def transcribe(
    background: BackgroundTasks,
    audio: UploadFile = File(...),
    user_id: str = Form(None),
):
    # RF-02: Validación de formato
    ext = Path(audio.filename or "").suffix.lower()
    if ext not in config.ALLOWED_EXT:
        raise HTTPException(
            400, "Formato no soportado. Solo se aceptan archivos MP3 o WAV")

    data = await audio.read()
    
    # RF-03: Validación de tamaño (50 MB)
    if len(data) > config.MAX_BYTES:
        raise HTTPException(
            400, "Tamaño excedido. El archivo no debe superar los cincuenta megabytes")

    job = jobs.create(original_name=Path(audio.filename).stem)
    dest = config.UPLOAD_DIR / f"{job.job_id}{ext}"
    
    # Guardamos el archivo para poder validarlo con librosa
    dest.write_bytes(data)

    # <-- CORREGIDO: Ahora SÍ llamamos a la función de validación de duración (RF-04)
    # Si falla, lanza HTTPException y FastAPI la maneja, pero debemos asegurar la limpieza
    try:
        validar_duracion(dest, max_segundos=360)
    except HTTPException:
        raise # Re-lanzamos la excepción para que FastAPI la devuelva al cliente

    # Si pasa la validación, lo mandamos al background
    background.add_task(process, job.job_id, dest)
    
    return {
        "job_id": job.job_id, 
        "status": JobStatus.PROCESSING.value,
        "message": "Transcripción en proceso"
    }


def process(job_id: str, path: Path):
    job = jobs.get(job_id)
    try:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_name = f"{job.original_name}_harmonic_score_{ts}.pdf"
        pdf_path = config.OUTPUT_DIR / out_name
        
        # El XML se genera con el mismo nombre base, solo cambia la extensión
        xml_path = pdf_path.with_suffix('.musicxml') 
        
        pdf, metrics = orch.run(path, out_name,
                                on_stage=lambda s: jobs.set_stage(job_id, s))
        
        # <-- ACTUALIZADO: Pasamos ambas rutas al job manager
        jobs.complete(job_id, pdf_path, xml_path, metrics)
        audit({"job_id": job_id, "file": job.original_name,
               "status": "completed", **metrics})
    except Exception as e:
        log.exception("Job %s falló", job_id)
        jobs.fail(job_id, str(e))
        audit({"job_id": job_id, "status": "failed", "error": str(e)})
    finally:
        path.unlink(missing_ok=True)


@app.get("/api/transcribe/{job_id}")
def status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job no encontrado")
    if job.status == JobStatus.PROCESSING:
        return {"job_id": job_id, "status": "processing", "stage": job.stage}
    if job.status == JobStatus.FAILED:
        return {"job_id": job_id, "status": "failed", "detail": job.error}
    return {"job_id": job_id, "status": "completed",
            "pdf_url": f"/api/download/{job_id}", "metrics": job.metrics}


@app.get("/api/download/{job_id}")
def download(job_id: str, format: str = "pdf"):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job no encontrado")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(400, "La transcripción aún se encuentra en proceso")
    
    # Si piden XML y existe, servir el XML
    if format.lower() == "xml" and job.xml_path and job.xml_path.exists():
        return FileResponse(job.xml_path, media_type="application/xml",
                            filename=job.xml_path.name)
                            
    # Por defecto, servir el PDF
    return FileResponse(job.pdf_path, media_type="application/pdf",
                        filename=job.pdf_path.name)


if __name__ == "__main__":
    import uvicorn
    # <-- CRÍTICO: host="0.0.0.0" permite que Docker lo alcance
    uvicorn.run(app, host="0.0.0.0", port=8000)