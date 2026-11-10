"""
Orquestador del pipeline de transcripción (Ciclo 3 - Versión Final Corregida).

Flujo: audio (RF-01/02/03) → CQT análisis (RF-09) → polifonía por entropía (RF-08)
     → inferencia YourMT3+ MoE (RF-10) → post-procesamiento (RF-11)
     → partitura PDF (RF-12/RF-13).

Nota de arquitectura: el checkpoint YourMT3+ computa su propia representación interna 
(mel, sr=16 kHz) desde la forma de onda cruda; por eso el modelo recibe 
la RUTA del audio y no un tensor de CQT. La CQT cumple el rol 
de análisis espectral (RF-08/RF-09). No existe etapa `to_tensor`.
"""
import logging
import time
import unicodedata
from pathlib import Path
from typing import Tuple, Dict, Any
from pipeline.post_stage import detectar_instrumento_por_modelo
import torch

import settings as config
from pipeline import audio_stage, cqt_stage, model_stage, post_stage, score_stage

log = logging.getLogger("harmonic.orchestrator")

def normalizar_texto(texto: str) -> str:
    """
    Elimina acentos y caracteres de combinación de un texto (pre-filtro).
    Ejemplo: 'Nomás_acotado' -> 'Nomas_acotado'
    Nota: La limpieza profunda con regex se realiza en score_stage.limpiar_titulo.
    """
    texto_normalizado = unicodedata.normalize('NFD', texto)
    return ''.join(c for c in texto_normalizado if not unicodedata.combining(c))


class Orchestrator:
    def run(self, audio_path: Path, out_name: str, on_stage=None) -> Tuple[Path, Dict[str, Any]]:
        """
        Ejecuta el pipeline completo de transcripción musical.
        """
        metrics = {}
        t0 = time.perf_counter()

        def time_it(name: str, fn, *args, **kwargs):
            if on_stage:
                on_stage(name)  # Reporte de progreso real hacia el frontend
            ts = time.perf_counter()
            out = fn(*args, **kwargs)
            metrics[f"{name}_ms"] = round((time.perf_counter() - ts) * 1000, 1)
            return out

        try:
            # 1) Carga y validación técnica (RF-02/RF-03)
            # CORREGIDO: Desempaquetamos los 4 valores que retorna audio_stage.load_audio
            y, sr, duration, audio_metrics = time_it("audio_load", audio_stage.load_audio, audio_path)
            
            # Fusionar las métricas de audio al diccionario general
            metrics.update(audio_metrics)

            # 2) Representación CQT (RF-09, solo para análisis espectral)
            mag = time_it("cqt", cqt_stage.compute_cqt, y)

            # 3) Clasificación monofónico/polifónico por entropía espectral (RF-08)
            entropy, level = time_it("polyphony", cqt_stage.classify_polyphony, mag)
            metrics["spectral_entropy"] = round(entropy, 4)
            metrics["polyphony_level"] = level

            # 4) Inferencia con el modelo real (RF-10): consume el audio, no la CQT
            raw_notes = time_it("model", model_stage.infer_notes, audio_path)
            
            # Validación temprana: si el modelo no detectó nada, abortar con mensaje claro
            if not raw_notes:
                raise ValueError("El modelo no detectó ninguna nota musical en el audio proporcionado.")

            instrumento_detectado = detectar_instrumento_por_modelo(raw_notes)
            log.info(f"🎵 Instrumento detectado: {instrumento_detectado}")
            es_polifonico = (level != "monofonico")

            # 5) Post-procesamiento con reglas musicales (RF-11)
            # Aquí ocurre la magia: NMS, corrección de octava, cuantización y fusión
            post_result = time_it("post", post_stage.refine, raw_notes, 
                      mag_cqt=mag,
                      sr=config.CQT_PARAMS["sr"], 
                      hop_length=config.CQT_PARAMS["hop_length"],
                      es_percusion=False,  # Asumimos que no es percusión
                      es_polifonico=es_polifonico,
                      instrumento=instrumento_detectado)
            
            # Extraer resultados refinados del diccionario
            final_notes = post_result["notes"]
            estimated_bpm = post_result["bpm"]
            estimated_time_sig = post_result["time_signature"]
            
            # Guardar métricas clave del post-procesamiento (oro para el Capítulo 6)
            metrics["n_notes_raw"] = len(raw_notes)
            metrics["n_notes_final"] = len(final_notes)
            metrics["estimated_bpm"] = estimated_bpm
            metrics["time_signature"] = estimated_time_sig

            # 6) Generación de partitura y PDF (RF-12/RF-13)
            pdf_path = config.OUTPUT_DIR / out_name

            # Limpieza básica del título para el log (score_stage hace la limpieza profunda con regex)
            base = out_name.split('_harmonic_score_')[0]
            parts = base.rsplit('_', 1)
            if len(parts) == 2 and any(c.isupper() or c.isdigit() for c in parts[1]):
                base = parts[0]
            base = normalizar_texto(base)
            titulo_pieza = base.replace('-', ' ').replace('_', ' ').title()
            
            # ¡CRÍTICO! Pasamos `final_notes` (no `raw_notes`) al generador de partituras
            generated_pdf_path = time_it("score_pdf", score_stage.build_score, final_notes, pdf_path, 
                                         bpm=estimated_bpm, 
                                         time_signature=estimated_time_sig,
                                         title=titulo_pieza,
                                         instrumento=instrumento_detectado) 

            # Métricas de hardware (evidencia TT-II vs RNF-01/02)
            metrics["total_ms"] = round((time.perf_counter() - t0) * 1000, 1)
            if torch.cuda.is_available():
                metrics["vram_peak_mb"] = round(torch.cuda.max_memory_allocated() / 1e6, 1)

            log.info("Pipeline OK | %d notas finales (de %d crudas) | entropía=%.3f (%s) | %.1f ms | %s",
                     len(final_notes), len(raw_notes), entropy, level, metrics["total_ms"], config.DEVICE)
            
            return generated_pdf_path, metrics

        except ValueError as ve:
            log.error(f"Error de validación en el pipeline: {ve}")
            raise
        except Exception as e:
            log.error(f"Error crítico en el pipeline: {e}", exc_info=True)
            raise RuntimeError(f"Fallo en la transcripción: {e}") from e