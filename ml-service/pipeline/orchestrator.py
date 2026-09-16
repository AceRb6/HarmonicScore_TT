"""
Orquestador del pipeline de transcripción (Ciclo 1).

Flujo: audio (RF-01/02/03) → CQT análisis (RF-09) → polifonía por entropía (RF-08)
     → inferencia YourMT3+ MoE (RF-10) → post-procesamiento (RF-11)
     → partitura PDF (RF-12/RF-13).

Nota de arquitectura (documentar en TT-II): el checkpoint YourMT3+ computa su
propia representación interna (mel, sr=16 kHz) desde la forma de onda cruda;
por eso el modelo recibe la RUTA del audio y no un tensor de CQT. La CQT cumple
el rol de análisis espectral (RF-08/RF-09). No existe etapa `to_tensor`.
"""
import logging
import time
from pathlib import Path

import torch

import settings as config
from pipeline import audio_stage, cqt_stage, model_stage, post_stage, score_stage

log = logging.getLogger("harmonic.orchestrator")


class Orchestrator:
    def run(self, audio_path: Path, out_name: str, on_stage=None):
        metrics = {}
        t0 = time.perf_counter()

        def time_it(name, fn, *args):
            if on_stage:
                on_stage(name)                      # progreso real hacia el front
            ts = time.perf_counter()
            out = fn(*args)
            metrics[f"{name}_ms"] = round((time.perf_counter() - ts) * 1000, 1)
            return out

        # 1) Carga y validación técnica (RF-02/RF-03; msn4 CU-04 dentro de audio_stage)
        y, sr, duration = time_it("audio_load", audio_stage.load_audio, audio_path)
        metrics["duration_s"] = round(duration, 2)

        # 2) Representación CQT (RF-09, solo análisis)
        mag = time_it("cqt", cqt_stage.compute_cqt, y)

        # 3) Clasificación monofónico/polifónico por entropía espectral (RF-08)
        entropy, level = time_it("polyphony", cqt_stage.classify_polyphony, mag)
        metrics["spectral_entropy"] = round(entropy, 4)
        metrics["polyphony_level"] = level

        # 4) Inferencia con el modelo real (RF-10): consume el audio, no la CQT
        notes = time_it("model", model_stage.infer_notes, audio_path)

        # 5) Post-procesamiento con reglas musicales (RF-11)
        notes = time_it("post", post_stage.refine, notes)
        metrics["n_notes"] = len(notes)

        # 6) Generación de partitura y PDF (RF-12/RF-13)
        pdf_path = config.OUTPUT_DIR / out_name
        time_it("score_pdf", score_stage.build_score, notes, pdf_path)

        # Métricas de hardware (evidencia TT-II vs RNF-01/02)
        metrics["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
        if torch.cuda.is_available():
            metrics["vram_peak_mb"] = round(torch.cuda.max_memory_allocated() / 1e6, 1)

        log.info("Pipeline OK | %d notas | entropía=%.3f (%s) | %.1f ms | %s",
                 len(notes), entropy, level, metrics["total_ms"], config.DEVICE)
        return pdf_path, metrics