"""
Adaptador YourMT3+ v3 — Inferencia segmentada con batch paralelo

Problema resuelto (H-27, hipótesis A confirmada):
El método `inference_file()` del repo oficial tiene un bug en el manejo de
estado/cache del decoder autoregresivo entre ventanas, causando colapso en
ventanas 2+ cuando se procesan en una sola llamada.

Solución:
- Cada ventana se procesa como ítem independiente (llamada fresca)
- Batch paralelo para aprovechar GPU (mejora latencia, RNF-01)
- Solape 50% para no cortar notas en fronteras
- Fusión de eventos duplicados en el solape

Validación: exp_midwindow.py confirmó que todas las ventanas (0, 2, 10, 30, 50)
producen eventos cuando se llaman de forma independiente.

Autor: Harmonic Score Team
Fecha: 2026-10-04
"""
import sys
import logging
from pathlib import Path
from typing import List

import numpy as np
import torch

ML = Path(__file__).resolve().parents[1]
SRC = ML / "models" / "amt" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import settings as config
from utils.audio import slice_padded_array
from utils.event2note import note_event2note

log = logging.getLogger("harmonic.ymt3_adapter_v3")

SEG = config.MODEL_AUDIO["window"]          # 32767 muestras
SR = config.MODEL_AUDIO["sr"]               # 16000 Hz
SEG_SEC = SEG / SR                          # ~2.048 s por ventana


class YMT3AdapterV3:
    """Adaptador con inferencia segmentada y batch paralelo."""
    
    _instance = None
    
    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._load()
        return cls._instance
    
    def _load(self):
        """Carga el modelo."""
        import platform
        if platform.system() == "Windows":
            original_compile = torch.compile
            torch.compile = lambda *args, **kwargs: (lambda f: f)
            log.info("torch.compile deshabilitado (Windows)")
        
        log.info("Cargando checkpoint real (v3): %s", config.CHECKPOINT_PATH)
        from pipeline.model_stage import _find_model_class
        cls = _find_model_class()
        self.model = cls.load_from_checkpoint(
            str(config.CHECKPOINT_PATH), map_location="cpu")
        self.model.eval()
        self.model.to(config.DEVICE)
        
        if not hasattr(self.model, 'task_manager'):
            raise RuntimeError("Modelo sin task_manager")
        self.task_manager = self.model.task_manager
        
        n = sum(p.numel() for p in self.model.parameters())
        log.info("YMT3Adapter v3 listo: %.1fM params en %s", n / 1e6, config.DEVICE)
    
    @torch.no_grad()
    def transcribe(self, audio_path: Path, hop_frac: float = 0.5, bsz: int = 8):
        """Transcribe audio con inferencia segmentada y batch paralelo.
        
        Args:
            audio_path: ruta al archivo de audio
            hop_frac: fracción de solape entre ventanas (0.5 = 50%)
            bsz: tamaño de batch para procesamiento paralelo
        
        Returns:
            Lista de objetos Note con onset/offset/pitch/velocity
        """
        import librosa
        y, sr = librosa.load(str(audio_path), sr=SR, mono=True)
        
        rms_raw = float(np.sqrt(np.mean(y ** 2)))
        peak_raw = float(np.max(np.abs(y)))
        log.info("Audio crudo: %d muestras | RMS=%.4f | pico=%.4f | duración=%.1f s",
                 len(y), rms_raw, peak_raw, len(y)/sr)
        
        # Normalización de amplitud (H-27: mejora marginal)
        if getattr(config, "NORMALIZE_INPUT", True):
            peak = float(np.max(np.abs(y))) + 1e-8
            y = np.clip(y / peak, -1.0, 1.0) * config.NORMALIZE_TARGET
            log.info("Entrada normalizada a pico %.2f (gain=%.2f)",
                     config.NORMALIZE_TARGET, config.NORMALIZE_TARGET / peak)
        
        x = y.astype(np.float32).reshape(1, -1)
        
        # Ventaneo con solape
        hop = int(SEG * hop_frac)
        hop_sec = hop / SR
        segs = slice_padded_array(x, slice_length=SEG, slice_hop=hop, pad=True)
        segs = segs.astype(np.float32)
        n_seg = segs.shape[0]
        log.info("Ventanas: %d x %.3f s | hop=%.1f%% | batch=%d",
                n_seg, SEG_SEC, hop_frac * 100, bsz)
        
        # Inferencia por batch paralelo
        all_notes = []
        for i in range(0, n_seg, bsz):
            batch_segs = segs[i:i+bsz]
            batch_tensor = torch.from_numpy(batch_segs).unsqueeze(1).to(self.model.device)
            
            # Llamada fresca: cada ventana es ítem independiente
            preds = self.model.inference(batch_tensor, None)
            preds_np = preds.detach().cpu().numpy()  # (batch, C, L)
            
            # Procesar cada ventana del batch
            for j in range(preds_np.shape[0]):
                window_idx = i + j
                t0 = window_idx * hop_sec
                pred = preds_np[j]
                
                if pred.ndim == 2:
                    pred = pred[None, ...]
                
                # Decodificar cada canal
                for c in range(pred.shape[1]):
                    tok = [int(t) for t in pred[0, c]]
                    
                    if window_idx < 3 and c < 3:
                        log.info("ventana %d canal %d tokens (primeros 12): %s",
                                window_idx, c, tok[:12])
                    
                    out = self.task_manager.detokenize(tok)
                    note_events, tie_events = out[0], out[1]
                    
                    # Desplazar eventos a tiempo absoluto
                    for ev in list(note_events) + list(tie_events):
                        if hasattr(ev, 'onset') and ev.onset is not None:
                            ev.onset += t0
                        if hasattr(ev, 'offset') and ev.offset is not None:
                            ev.offset += t0
                    
                    try:
                        seg_notes, err_cnt = note_event2note(note_events, tie_events)
                        all_notes.extend(seg_notes)
                    except TypeError as e:
                        log.debug("ventana %d canal %d omitido: %s", window_idx, c, e)
                        continue
        
        # Ordenar y fusionar duplicados en solape
        all_notes.sort(key=lambda n: n.onset)
        notes = self._merge_overlap(all_notes, overlap_sec=hop_sec)
        
        # Métrica de cobertura
        if notes:
            last_onset = notes[-1].onset
            coverage = last_onset / (n_seg * hop_sec)
            log.info("Notas: %d | último onset: %.2f s | cobertura: %.1f%% | fusionadas: %d",
                    len(notes), last_onset, 100 * coverage, len(all_notes) - len(notes))
        else:
            log.warning("No se detectaron notas en el audio.")
        
        return notes
    
    def _merge_overlap(self, notes: List, overlap_sec: float, tol_ms: float = 50) -> List:
        """Fusiona notas duplicadas en el solape.
        
        Criterios:
        - Mismo pitch
        - |onset_A - onset_B| < tol_ms
        - Conservar la de mayor duración
        """
        if not notes:
            return notes
        
        merged = [notes[0]]
        tol = tol_ms / 1000.0
        
        for note in notes[1:]:
            prev = merged[-1]
            # ¿Es duplicado en solape?
            if (note.pitch == prev.pitch and
                abs(note.onset - prev.onset) < tol):
                # Conservar la de mayor duración
                if note.offset - note.onset > prev.offset - prev.onset:
                    merged[-1] = note
            else:
                merged.append(note)
        
        return merged


def infer_notes_v3(audio_path: Path):
    """API compatible con model_stage.infer_notes() usando adapter v3."""
    raw = YMT3AdapterV3.get().transcribe(audio_path)
    return [{
        "pitch": int(n.pitch),
        "onset": float(n.onset),
        "offset": float(n.offset),
        "velocity": int(n.velocity),
        "instrument": int(n.program),
        "is_drum": bool(n.is_drum),
        "confidence": 1.0,
        "backend": "ymt3_v3",
    } for n in raw]