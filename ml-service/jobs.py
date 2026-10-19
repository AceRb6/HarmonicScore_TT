"""Gestión de trabajos con los estados de RF-05."""
import time
import uuid
import threading
from enum import Enum
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass, field

import settings as config

class JobStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Job:
    job_id: str
    original_name: str
    status: JobStatus = JobStatus.PROCESSING
    pdf_path: Optional[Path] = None
    xml_path: Optional[Path] = None  # <-- AGREGADO: Para guardar la ruta del MusicXML
    metrics: Dict = field(default_factory=dict)
    error: Optional[str] = None
    stage: str = "queued"
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
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].stage = stage

    # <-- ACTUALIZADO: Ahora recibe y guarda también la ruta del XML
    def complete(self, job_id: str, pdf_path: Path, xml_path: Path, metrics: Dict) -> None:
        with self._lock:
            j = self._jobs[job_id]
            j.status = JobStatus.COMPLETED
            j.pdf_path = pdf_path
            j.xml_path = xml_path
            j.metrics = metrics

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            j = self._jobs[job_id]
            j.status = JobStatus.FAILED
            j.error = error