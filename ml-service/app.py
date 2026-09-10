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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs = JobManager()
orch = Orchestrator()
AUDIT = config.LOG_DIR / "audit.jsonl"          # RF-15


def audit(entry: dict):
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
    # RF-02
    ext = Path(audio.filename or "").suffix.lower()
    if ext not in config.ALLOWED_EXT:
        raise HTTPException(
            400, "Formato no soportado. Solo se aceptan archivos MP3 o WAV")

    data = await audio.read()
    # RF-03
    if len(data) > config.MAX_BYTES:
        raise HTTPException(
            400, "Tamaño excedido. El archivo no debe superar los cincuenta megabytes")

    job = jobs.create(original_name=Path(audio.filename).stem)
    dest = config.UPLOAD_DIR / f"{job.job_id}{ext}"
    dest.write_bytes(data)

    background.add_task(process, job.job_id, dest)
    return {"job_id": job.job_id, "status": JobStatus.PROCESSING.value,
            "message": "Transcripción en proceso"}


def process(job_id: str, path: Path):
    job = jobs.get(job_id)
    try:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        out_name = f"{job.original_name}_harmonic_score_{ts}.pdf"   # RF-06
        pdf, metrics = orch.run(path, out_name,
                                on_stage=lambda s: jobs.set_stage(job_id, s))
        jobs.complete(job_id, pdf, metrics)
        audit({"job_id": job_id, "file": job.original_name,
               "status": "completed", **metrics})
    except Exception as e:
        log.exception("Job %s falló", job_id)
        jobs.fail(job_id, str(e))
        audit({"job_id": job_id, "status": "failed", "error": str(e)})
    finally:
        path.unlink(missing_ok=True)             # RF-07


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
def download(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job no encontrado")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(400, "La transcripción aún se encuentra en proceso")
    return FileResponse(job.pdf_path, media_type="application/pdf",
                        filename=job.pdf_path.name)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)