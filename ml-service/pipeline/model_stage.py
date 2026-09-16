"""
Etapa 3: Inferencia con YourMT3+ MoE (checkpoint local).
Cadena oficial verificada contra el repo de entrenamiento:
  model/ymt3.py:459,508 | utils/task_manager.py:346 | utils/event2note.py:157
Incluye fallback baseline (peak-picking) conmutado por config.MODEL_BACKEND
para garantizar el cierre del Entregable 1 si el checkpoint diera problemas.
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

SEG = config.MODEL_AUDIO["window"]          # 32767 muestras
SR = config.MODEL_AUDIO["sr"]               # 16000 Hz
SEG_SEC = SEG / SR                          # ~2.048 s por ventana


# ---------------------------------------------------------------------
# Carga del modelo (clase descubierta dinámicamente: no asumimos nombre)
# ---------------------------------------------------------------------
def _find_model_class():
    """Descubre la clase del modelo por duck typing, no por identidad de paquete.

    En Lightning 2.x, `lightning` y `pytorch_lightning` son paquetes espejo con
    objetos de clase DISTINTOS; un issubclass cruzado falla. Por eso buscamos
    la clase definida en model/ymt3.py que exponga la API de LightningModule
    (load_from_checkpoint) y la del repo (inference_file).
    """
    import model.ymt3 as ymt3_mod
    candidates = [
        obj for _, obj in inspect.getmembers(ymt3_mod, inspect.isclass)
        if obj.__module__ == ymt3_mod.__name__
        and callable(getattr(obj, "inference_file", None))
        and callable(getattr(obj, "load_from_checkpoint", None))
    ]
    if not candidates:
        raise RuntimeError("No se encontró la clase del modelo en model/ymt3.py")
    log.info("Clase del modelo detectada: %s (MRO: %s)",
             candidates[0].__name__,
             " -> ".join(c.__name__ for c in candidates[0].__mro__[1:4]))
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
        # Workaround: torch.compile no está soportado en Windows (PyTorch 2.1.2)
        import platform
        if platform.system() == "Windows":
            import torch
            original_compile = torch.compile
            torch.compile = lambda *args, **kwargs: (lambda f: f)  # no-op decorator
            log.info("torch.compile deshabilitado (Windows)")
        
        log.info("Cargando checkpoint real: %s", config.CHECKPOINT_PATH)
        cls = _find_model_class()
        self.model = cls.load_from_checkpoint(str(config.CHECKPOINT_PATH),
                                              map_location="cpu")
        self.model.eval()
        self.model.to(config.DEVICE)
        
        # El TaskManager ya está montado en el modelo por __init__
        # (ver model/ymt3.py línea ~107: self.task_manager = task_manager)
        if not hasattr(self.model, 'task_manager'):
            raise RuntimeError("El modelo cargado no tiene task_manager. "
                             "El checkpoint puede estar corrupto.")
        self.task_manager = self.model.task_manager
        
        n = sum(p.numel() for p in self.model.parameters())
        log.info("Modelo real listo: %.1fM params en %s", n / 1e6, config.DEVICE)

    @torch.no_grad()
    def transcribe(self, audio_path: Path):
        """
        Transcribe audio a notas musicales usando YourMT3+ MoE.
        """
        # 1) Audio 16 kHz usando librosa (maneja MP3/WAV nativamente, devuelve float32)
        y, sr = librosa.load(str(audio_path), sr=SR, mono=True)
        
        # Normalizar a rango [-1, 1] y asegurar float32
        x = y.astype(np.float32).reshape(1, -1)
        
        # 0) Diagnóstico de la entrada (evidencia para root-cause)
        log.info("Entrada: %d muestras | RMS=%.4f | pico=%.4f",
                 x.shape[-1], float(np.sqrt(np.mean(x ** 2))), float(np.max(np.abs(x))))

        # 2) Ventanas de 32767 muestras sin solapamiento
        segs = slice_padded_array(x, slice_length=SEG, slice_hop=SEG, pad=True)
        segs = segs.astype(np.float32)
        segs_t = torch.from_numpy(segs).unsqueeze(1)          # (n_seg, 1, SEG)
        log.info("Ventanas: %d x %.3f s", segs_t.shape[0], SEG_SEC)
        
        # 3) Inferencia autoregresiva oficial
        preds_list, _ = self.model.inference_file(bsz=1, audio_segments=segs_t)
        log.info("preds_list: %d elementos | shape[0]=%s | shape[-1]=%s",
                 len(preds_list),
                 np.asarray(preds_list[0]).shape,
                 np.asarray(preds_list[-1]).shape)

        # 4) Decodificación por ventana y por canal, con contención de eventos huérfanos
        notes = []
        skipped = 0
        seg_idx = 0
        for pred in preds_list:
            pred = np.asarray(pred)
            if pred.ndim == 2:
                pred = pred[None, ...]
            for s in range(pred.shape[0]):
                t0 = seg_idx * SEG_SEC
                for c in range(pred.shape[1]):
                    tok = [int(t) for t in pred[s, c]]
                    if seg_idx < 3 and c < 3:                  # testigo: primeras ventanas
                        log.info("seg %d canal %d tokens: %s", seg_idx, c, tok[:24])
                    out = self.task_manager.detokenize(tok, start_time=t0)
                    note_events, tie_events = out[0], out[1]
                    try:
                        seg_notes, err_cnt = note_event2note(note_events, tie_events)
                    except TypeError as e:
                        # note-off huérfano (onset=None) en secuencia degenerada:
                        # se omite el canal sin abortar el job (fragilidad del repo oficial)
                        skipped += 1
                        log.debug("seg %d canal %d omitido por eventos malformados: %s",
                                  seg_idx, c, e)
                        continue
                    if err_cnt:
                        log.debug("canal %d seg %d: %s", c, seg_idx, dict(err_cnt))
                    notes.extend(seg_notes)
                seg_idx += 1

        notes.sort(key=lambda n: n.onset)
        log.info("Notas detectadas: %d | canales omitidos: %d", len(notes), skipped)
        return notes


# ---------------------------------------------------------------------
# Fallback baseline Ciclo 1 (peak-picking sobre CQT) — seguro de entrega
# ---------------------------------------------------------------------
def _baseline_notes(audio_path: Path):
    from pipeline import cqt_stage
    import librosa
    from scipy.signal import find_peaks
    y, _ = librosa.load(str(audio_path), sr=config.CQT_PARAMS["sr"], mono=True)
    mag = cqt_stage.compute_cqt(y)
    mag_n = mag / (mag.max() + 1e-10)
    freqs = config.CQT_PARAMS["fmin"] * (2 ** (np.arange(mag.shape[1]) / 12.0))
    midis = np.round(librosa.hz_to_midi(freqs)).astype(int)
    notes = []
    for t in range(mag_n.shape[0]):
        peaks, props = find_peaks(mag_n[t], height=0.35, distance=2, prominence=0.1)
        for pk, h in zip(peaks, props["heights"]):
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
    
    return [{
        "pitch": int(n.pitch),
        "onset": float(n.onset),
        "offset": float(n.offset),
        "velocity": int(n.velocity),
        "instrument": int(n.program),
        "is_drum": bool(n.is_drum),
        "confidence": 1.0,
    } for n in raw]