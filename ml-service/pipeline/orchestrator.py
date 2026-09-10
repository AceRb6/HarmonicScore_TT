"""Orquestador Ciclo 1: encadena etapas con telemetría por etapa (RNF-01/02, R06)."""
import time
import logging

import torch
import psutil

import settings as config
from pipeline import audio_stage, cqt_stage, model_stage, post_stage, score_stage

log = logging.getLogger("ml-service.orchestrator")


class Orchestrator:
    def run(self, audio_path, out_name, on_stage=None):
        """Ejecuta el pipeline completo. Retorna (pdf_path, metrics)."""
        metrics = {}
        t0 = time.perf_counter()
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()

        def time_it(name, fn, *args):
            if on_stage:
                on_stage(name)
            ts = time.perf_counter()
            out = fn(*args)
            metrics[f"{name}_ms"] = round((time.perf_counter() - ts) * 1000, 1)
            return out

        # Pipeline: audio → CQT → polifonía → modelo → post → partitura
        y, sr, duration = time_it("audio_load", audio_stage.load_audio, audio_path)
        mag = time_it("cqt", cqt_stage.compute_cqt, y)
        entropy, level = time_it("polyphony", cqt_stage.classify_polyphony, mag)
        tensor = cqt_stage.to_tensor(mag)                 # (1,1,T,264)
        notes = time_it("model", model_stage.infer_notes, audio_path)
        notes = time_it("post", post_stage.refine, notes)
        pdf_path = config.OUTPUT_DIR / out_name
        time_it("score_pdf", score_stage.build_score, notes, pdf_path)

        metrics.update({
            "duration_s": round(duration, 2),
            "tensor_shape": list(tensor.shape),
            "spectral_entropy": round(entropy, 4),
            "polyphony": level,
            "n_notes": len(notes),
            "model": "baseline_peakpick_c1",              # etiquetado honesto
            "device": str(config.DEVICE),
            "total_ms": round((time.perf_counter() - t0) * 1000, 1),
            "ram_mb": round(psutil.Process().memory_info().rss / 1024**2, 1),
        })
        if torch.cuda.is_available():
            metrics["vram_peak_mb"] = round(
                torch.cuda.max_memory_allocated() / 1024**2, 1)

        log.info("Pipeline OK | %s notas | %s ms | %s",
                 len(notes), metrics["total_ms"], metrics["device"])
        return pdf_path, metrics