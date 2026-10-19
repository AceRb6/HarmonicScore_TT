"""
Etapa 3: Inferencia con YourMT3+ MoE (checkpoint local).
CICLO 3: Implementación de ventanas con solapamiento (Overlap-Add) 
según Sección 6.3.1 del reporte técnico para maximizar el recall.
"""
import sys
import inspect
import logging
from pathlib import Path

import numpy as np
import torch
import librosa

ML = Path(__file__).resolve().parents[1]
SRC = ML / "models" / "amt" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import settings as config 
from utils.audio import slice_padded_array
from utils.event2note import note_event2note

log = logging.getLogger("harmonic.model_stage")

# --- Configuración de Ventanas (Ciclo 3) ---
SEG = config.MODEL_AUDIO["window"]          # 32767 muestras
SR = config.MODEL_AUDIO["sr"]               # 16000 Hz
SEG_SEC = SEG / SR                          # ~2.048 s por ventana
OVERLAP_RATIO = 0.15                        # 15% de solapamiento (Reporte §6.3.1)
SEG_HOP = int(SEG * (1 - OVERLAP_RATIO))    # Hop real con solapamiento (~27851 muestras)


# ---------------------------------------------------------------------
# Carga del modelo
# ---------------------------------------------------------------------
def _find_model_class():
    """Descubre la clase del modelo por duck typing."""
    import model.ymt3 as ymt3_mod
    candidates = [
        obj for _, obj in inspect.getmembers(ymt3_mod, inspect.isclass)
        if obj.__module__ == ymt3_mod.__name__
        and callable(getattr(obj, "inference_file", None))
        and callable(getattr(obj, "load_from_checkpoint", None))
    ]
    if not candidates:
        raise RuntimeError("No se encontró la clase del modelo en model/ymt3.py")
    log.info("Clase del modelo detectada: %s", candidates[0].__name__)
    return candidates[0]


class RealModel:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._load()
        return cls._instance

    def _load(self):
        import platform
        if platform.system() == "Windows":
            import torch
            original_compile = torch.compile
            torch.compile = lambda *args, **kwargs: (lambda f: f)
            log.info("torch.compile deshabilitado (Windows workaround)")
        
        log.info("Cargando checkpoint real: %s", config.CHECKPOINT_PATH)
        cls = _find_model_class()
        self.model = cls.load_from_checkpoint(str(config.CHECKPOINT_PATH),
                                              map_location=config.DEVICE)
        self.model.eval()
        self.model.to(config.DEVICE)
        
        if not hasattr(self.model, 'task_manager'):
            raise RuntimeError("El modelo cargado no tiene task_manager.")
        self.task_manager = self.model.task_manager
        
        n = sum(p.numel() for p in self.model.parameters())
        log.info("Modelo real listo: %.1fM params en %s", n / 1e6, config.DEVICE)

    @torch.no_grad()
    def transcribe(self, audio_path: Path):
        """
        Transcribe audio a notas musicales usando YourMT3+ MoE.
        CICLO 3: Ventanas con solapamiento, normalización y manejo robusto de errores.
        """
        try:
            # 1) Audio 16 kHz
            y, sr = librosa.load(str(audio_path), sr=SR, mono=True)
            
            # Normalizamos al valor máximo y escalamos al 95% del rango
            y = librosa.util.normalize(y, norm=np.inf) * 0.95
            x = y.astype(np.float32).reshape(1, -1)
            
            log.info("Entrada: %d muestras (%.2f s) | RMS=%.4f | pico=%.4f (Normalizado)",
                     x.shape[-1], x.shape[-1]/SR, 
                     float(np.sqrt(np.mean(x ** 2))), float(np.max(np.abs(x))))

            # 2) Ventanas con 15% de solapamiento
            segs = slice_padded_array(x, slice_length=SEG, slice_hop=SEG_HOP, pad=True)
            segs = segs.astype(np.float32)
            segs_t = torch.from_numpy(segs).unsqueeze(1)
            
            n_segments = segs_t.shape[0]
            log.info("Ventanas: %d x %.3f s (hop=%d muestras, solapamiento=%.0f%%)", 
                     n_segments, SEG_SEC, SEG_HOP, OVERLAP_RATIO*100)
            
            # 3) Inferencia autoregresiva
            preds_list, _ = self.model.inference_file(bsz=1, audio_segments=segs_t)
            log.info("Inferencia completada. preds_list: %d elementos", len(preds_list))

            # 4) Decodificación por ventana
            notes = []
            skipped = 0
            seg_idx = 0
            
            for pred in preds_list:
                pred = np.asarray(pred)
                if pred.ndim == 2:
                    pred = pred[None, ...]
                
                for s in range(pred.shape[0]):
                    t0 = seg_idx * SEG_HOP / SR
                    
                    for c in range(pred.shape[1]):
                        tok = [int(t) for t in pred[s, c]]
                        
                        if seg_idx < 3 and c < 2:
                            log.info("seg %d canal %d tokens (primeros 20): %s", seg_idx, c, tok[:20])
                        
                        out = self.task_manager.detokenize(tok, start_time=t0)
                        note_events, tie_events = out[0], out[1]
                        
                        try:
                            seg_notes, err_cnt = note_event2note(note_events, tie_events)
                        except Exception as e:
                            skipped += 1
                            log.warning("seg %d canal %d omitido por error en note_event2note: %s", seg_idx, c, e)
                            continue
                        
                        if err_cnt:
                            log.debug("canal %d seg %d: %s", c, seg_idx, dict(err_cnt))
                        
                        # FILTRO DE SEGURIDAD: Solo agregar notas con onset y offset válidos
                        if seg_notes:
                            for n in seg_notes:
                                if getattr(n, 'onset', None) is not None and getattr(n, 'offset', None) is not None:
                                    notes.append(n)
                                else:
                                    skipped += 1
                        else:
                            skipped += 1
                            
                    seg_idx += 1

            # 5) Fusión de notas solapadas (Garantizamos que notes sea una lista)
            if not notes:
                log.warning("No se detectaron notas válidas en el audio.")
                return []  # <-- RETORNO SEGURO

            notes.sort(key=lambda n: n.onset)
            notes_fused = self._merge_overlapping_notes(notes)
            
            log.info("✅ RESULTADO: Notas detectadas: %d | Después de fusión: %d | Canales omitidos: %d", 
                     len(notes), len(notes_fused), skipped)
            
            return notes_fused
            
        except Exception as e:
            log.error("Error crítico en transcribe: %s", e, exc_info=True)
            return []  # <-- RETORNO SEGURO ANTE CUALQUIER FALLO
                    

    def _merge_overlapping_notes(self, notes, overlap_threshold_ms=100):
        """Fusiona notas que aparecen en múltiples ventanas solapadas."""
        if not notes:
            return []
        
        merged = []
        used = [False] * len(notes)
        overlap_threshold_s = overlap_threshold_ms / 1000.0
        
        for i, note_i in enumerate(notes):
            if used[i]:
                continue
            
            best_note = note_i
            for j in range(i + 1, len(notes)):
                if used[j]:
                    continue
                
                note_j = notes[j]
                if note_j.onset - note_i.onset > overlap_threshold_s:
                    break
                
                same_pitch = abs(note_i.pitch - note_j.pitch) <= 1
                close_onset = abs(note_i.onset - note_j.onset) < overlap_threshold_s
                close_offset = abs(note_i.offset - note_j.offset) < overlap_threshold_s
                
                if same_pitch and close_onset and close_offset:
                    best_note.onset = min(note_i.onset, note_j.onset)
                    best_note.offset = max(note_i.offset, note_j.offset)
                    best_note.velocity = max(note_i.velocity, note_j.velocity)
                    used[j] = True
            
            merged.append(best_note)
            used[i] = True
        
        return merged

# ---------------------------------------------------------------------
# Fallback baseline Ciclo 1 (sin cambios)
# ---------------------------------------------------------------------
def _baseline_notes(audio_path: Path):
    from pipeline import cqt_stage
    import librosa
    from scipy.signal import find_peaks
    y, _ = librosa.load(str(audio_path), sr=config.CQT_PARAMS["sr"], mono=True)
    mag = cqt_stage.compute_cqt(y)
    mag_n = mag / (mag.max() + 1e-10)
    freqs = config.CQT_PARAMS["fmin"] * (2 ** (np.arange(mag.shape[1]) / 12.0))
    midis = np.round(librosar.hz_to_midi(freqs)).astype(int)
    notes = []
    for t in range(mag_n.shape[0]):
        peaks, props = find_peaks(mag_n[t], height=0.35, distance=2, prominence=0.1)
        for pk, h in zip(peaks, props["peak_heights"]):
            notes.append(type("N", (), dict(
                is_drum=False, program=0, onset=t / config.FRAME_RATE,
                offset=(t + 1) / config.FRAME_RATE,
                pitch=int(midis[pk]), velocity=int(min(127, h * 127))))())
    return notes


# ---------------------------------------------------------------------
# API única para el orquestador
# ---------------------------------------------------------------------
def infer_notes(audio_path: Path):
    """Retorna lista de dicts estándar para post_stage y score_stage."""
    if config.MODEL_BACKEND == "real":
        raw = RealModel.get().transcribe(audio_path)
    else:
        raw = _baseline_notes(audio_path)
    
    # BLINDAJE FINAL: Si raw es None o no es iterable, devolver lista vacía
    if not raw:
        return []
        
    return [{
        "pitch": int(n.pitch),
        "onset": float(n.onset),
        "offset": float(n.offset),
        "velocity": int(n.velocity),
        "instrument": int(n.program),
        "is_drum": bool(n.is_drum),
        "confidence": 1.0,
    } for n in raw]