"""Gestión de trabajos con los estados de RF-05."""
import time
import uuid
import threading
from enum import Enum
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, field

import settings as config  # ← renombrado para evitar colisión con models/amt/src/config


class JobStatus(str, Enum):
    PROCESSING = "processing"     # "En proceso"
    COMPLETED = "completed"       # "Finalizado"
    FAILED = "failed"             # "Error en el procesamiento"


@dataclass
class Job:
    # 1) Campos SIN default primero (obligatorio en dataclasses)
    job_id: str
    original_name: str
    # 2) Campos CON default después
    status: JobStatus = JobStatus.PROCESSING
    pdf_path: Optional[Path] = None
    metrics: Dict = field(default_factory=dict)
    error: Optional[str] = None
    stage: str = "queued"                       # etapa actual para el progreso real
    created_at: float = field(default_factory=time.time)


class JobManager:
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, original_name: str) -> Job:
        job = Job(job_id=uuid.uuid4().hex, original_name=original_name)
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def set_stage(self, job_id: str, stage: str) -> None:
        """Publica la etapa actual del pipeline (progreso real del front)."""
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].stage = stage

    def complete(self, job_id: str, pdf_path: Path, metrics: Dict) -> None:
        with self._lock:
            j = self._jobs[job_id]
            j.status = JobStatus.COMPLETED
            j.pdf_path = pdf_path
            j.metrics = metrics

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            j = self._jobs[job_id]
            j.status = JobStatus.FAILED
            j.error = error