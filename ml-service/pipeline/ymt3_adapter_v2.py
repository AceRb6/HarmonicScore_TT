"""
Adaptador YourMT3+ para Harmonic Score — Versión 2 (CORREGIDO)

Problema resuelto: el método `inference_file()` del repo oficial tiene el
parámetro `subtask_key` comentado, lo que impide el condicionamiento por tarea
en el decoder. Este adaptador:

1. Construye los `task_tokens` manualmente desde `subtask_key="default"`
2. Llama a `model.inference()` (método sano) en lugar de `inference_file()`
3. Procesa predicciones batch por batch (evita concatenación con L variable)
4. Mantiene compatibilidad con la API de `model_stage`

Corrección v2.1: procesamiento directo sin concatenación para manejar
secuencias de longitud variable (decodificación autoregresiva cached).

Referencia técnica:
- `ymt3.py:365-410` (inference_file con subtask_key comentado)
- `ymt3.py:317-360` (inference con task conditioning activo)
- `utils/task_manager.py` (get_eval_subtask_prefix_dict)

Autor: Harmonic Score Team (derivado de YourMT3+ original)
Fecha: 2026-10-04
"""
import sys
import inspect
import logging
from pathlib import Path
from typing import List, Optional

import numpy as np
import torch

ML = Path(__file__).resolve().parents[1]
SRC = ML / "models" / "amt" / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import settings as config
from utils.audio import slice_padded_array
from utils.event2note import note_event2note

log = logging.getLogger("harmonic.ymt3_adapter")

SEG = config.MODEL_AUDIO["window"]          # 32767 muestras
SR = config.MODEL_AUDIO["sr"]               # 16000 Hz
SEG_SEC = SEG / SR                          # ~2.048 s por ventana


class YMT3Adapter:
    """Adaptador con condicionamiento de tarea corregido.
    
    Diferencias con la llamada directa a `inference_file`:
    - Construye `task_tokens` desde `subtask_key` manualmente
    - Llama a `inference()` por batch (método con condicionamiento activo)
    - Procesa predicciones directamente sin concatenar (maneja L variable)
    - Aplica offset temporal explícito post-detokenize (H-26)
    """
    
    _instance = None
    
    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._load()
        return cls._instance
    
    def _load(self):
        """Carga el modelo y cachea los task tokens por subtask."""
        import platform
        if platform.system() == "Windows":
            original_compile = torch.compile
            torch.compile = lambda *args, **kwargs: (lambda f: f)
            log.info("torch.compile deshabilitado (Windows)")
        
        log.info("Cargando checkpoint real (v2): %s", config.CHECKPOINT_PATH)
        from pipeline.model_stage import _find_model_class
        cls = _find_model_class()
        self.model = cls.load_from_checkpoint(
            str(config.CHECKPOINT_PATH), map_location="cpu")
        self.model.eval()
        self.model.to(config.DEVICE)
        
        if not hasattr(self.model, 'task_manager'):
            raise RuntimeError("Modelo sin task_manager")
        self.task_manager = self.model.task_manager
        
        # Cache de task tokens por subtask (evita reconstrucción por ventana)
        self._subtask_tokens_cache = {}
        
        n = sum(p.numel() for p in self.model.parameters())
        log.info("YMT3Adapter v2 listo: %.1fM params en %s", n / 1e6, config.DEVICE)
    
    def _get_subtask_tokens(self, subtask_key: str, batch_size: int) -> Optional[torch.Tensor]:
        """Construye y cachea los tokens de subtask para un batch dado.
        
        Retorna: tensor (batch_size, task_len) en el device correcto, o None
                 si el subtask no existe en el task_manager.
        """
        if subtask_key is None:
            return None
        
        cache_key = (subtask_key, batch_size)
        if cache_key not in self._subtask_tokens_cache:
            try:
                prefix_dict = self.task_manager.get_eval_subtask_prefix_dict()
                if subtask_key not in prefix_dict:
                    log.warning("subtask_key '%s' no encontrado; disponibles: %s",
                               subtask_key, list(prefix_dict.keys()))
                    return None
                prefix_ids = prefix_dict[subtask_key]
                base_token = torch.LongTensor(prefix_ids).to(self.model.device)
                self._subtask_tokens_cache[cache_key] = base_token.expand(batch_size, -1)
            except Exception as e:
                log.warning("No se pudieron construir task_tokens: %s", e)
                return None
        
        return self._subtask_tokens_cache[cache_key]
    
    @torch.no_grad()
    def transcribe(self, audio_path: Path, subtask_key: str = "default"):
        """Transcribe audio con condicionamiento de tarea correctamente cableado.
        
        Args:
            audio_path: ruta al archivo de audio
            subtask_key: clave de subtask para condicionamiento (default: "default")
        
        Returns:
            Lista de objetos Note con onset/offset/pitch/velocity
        """
        import librosa
        y, sr = librosa.load(str(audio_path), sr=SR, mono=True)
        
        rms_raw = float(np.sqrt(np.mean(y ** 2)))
        peak_raw = float(np.max(np.abs(y)))
        log.info("Audio crudo: %d muestras | RMS=%.4f | pico=%.4f | duración=%.1f s",
                 len(y), rms_raw, peak_raw, len(y)/sr)
        
        # Normalización de amplitud (H-27: mejora marginal, no cura OOD)
        if getattr(config, "NORMALIZE_INPUT", True):
            peak = float(np.max(np.abs(y))) + 1e-8
            y = np.clip(y / peak, -1.0, 1.0) * config.NORMALIZE_TARGET
            log.info("Entrada normalizada a pico %.2f (gain=%.2f)",
                     config.NORMALIZE_TARGET, config.NORMALIZE_TARGET / peak)
        
        x = y.astype(np.float32).reshape(1, -1)
        rms_final = float(np.sqrt(np.mean(x ** 2)))
        peak_final = float(np.max(np.abs(x)))
        log.info("Audio final: RMS=%.4f | pico=%.4f", rms_final, peak_final)
        
        # Ventaneo
        segs = slice_padded_array(x, slice_length=SEG, slice_hop=SEG, pad=True)
        segs = segs.astype(np.float32)
        segs_t = torch.from_numpy(segs).unsqueeze(1)  # (n_seg, 1, SEG)
        n_seg = segs_t.shape[0]
        log.info("Ventanas: %d x %.3f s | subtask_key='%s'", n_seg, SEG_SEC, subtask_key)
        
        # Decodificación con offset explícito (H-26)
        def _shift_events(events, dt):
            for ev in events:
                if hasattr(ev, 'onset') and ev.onset is not None:
                    ev.onset += dt
                if hasattr(ev, 'offset') and ev.offset is not None:
                    ev.offset += dt
        
        notes = []
        skipped = 0
        windows_with_notes = 0
        
        # Inferencia por batch con task tokens construidos manualmente
        # NOTA: llamamos a inference() directamente, NO a inference_file()
        bsz = 1  # batch size pequeño para VRAM
        
        for i in range(0, n_seg, bsz):
            batch_segs = segs_t[i:i+bsz].to(self.model.device)
            current_bsz = batch_segs.shape[0]
            
            # Construir task tokens para este batch
            task_tokens = self._get_subtask_tokens(subtask_key, current_bsz)
            if task_tokens is not None and i == 0:
                log.info("Task tokens construidos: shape=%s | ids=%s",
                        tuple(task_tokens.shape), task_tokens[0].tolist()[:8])
            
            # Llamada directa a inference() (método con condicionamiento activo)
            if self.model.test_pitch_shift_layer is not None:
                preds, _ = self.model.inference(batch_segs, task_tokens)
            else:
                preds = self.model.inference(batch_segs, task_tokens)
            
            # Convertir a numpy (shape: (bsz, num_channels, seq_len))
            preds_np = preds.detach().cpu().numpy()
            
            # Procesar este batch inmediatamente (evita concatenación con L variable)
            for j in range(preds_np.shape[0]):
                pred = preds_np[j]
                if pred.ndim == 2:
                    pred = pred[None, ...]
                
                # Calcular offset temporal para esta ventana específica
                window_idx = i + j
                t0 = window_idx * SEG_SEC
                
                window_has_notes = False
                
                for c in range(pred.shape[1]):
                    tok = [int(t) for t in pred[0, c]]
                    
                    if window_idx < 3 and c < 3:
                        log.info("ventana %d canal %d tokens (primeros 24): %s", 
                                window_idx, c, tok[:24])
                    
                    out = self.task_manager.detokenize(tok)
                    note_events, tie_events = out[0], out[1]
                    
                    _shift_events(note_events, t0)
                    _shift_events(tie_events, t0)
                    
                    try:
                        seg_notes, err_cnt = note_event2note(note_events, tie_events)
                    except TypeError as e:
                        skipped += 1
                        log.debug("ventana %d canal %d omitido: %s", window_idx, c, e)
                        continue
                    
                    if err_cnt:
                        log.debug("canal %d ventana %d: %s", c, window_idx, dict(err_cnt))
                    
                    if seg_notes:
                        window_has_notes = True
                    
                    notes.extend(seg_notes)
                
                if window_has_notes:
                    windows_with_notes += 1
        
        notes.sort(key=lambda n: n.onset)
        
        # Métrica de cobertura
        if notes:
            last_onset = notes[-1].onset
            coverage = last_onset / (n_seg * SEG_SEC)
            log.info("Notas: %d | último onset: %.2f s | cobertura: %.1f%% | omitidos: %d | ventanas con notas: %d/%d",
                    len(notes), last_onset, 100 * coverage, skipped, windows_with_notes, n_seg)
            if coverage < 0.5:
                log.warning("⚠️ COLAPSO TEMPORAL: cobertura < 50%%. Fine-tuning requerido.")
        else:
            log.warning("No se detectaron notas en el audio.")
        
        return notes


def infer_notes_v2(audio_path: Path):
    """API compatible con model_stage.infer_notes() pero usando el adaptador v2."""
    raw = YMT3Adapter.get().transcribe(audio_path)
    return [{
        "pitch": int(n.pitch),
        "onset": float(n.onset),
        "offset": float(n.offset),
        "velocity": int(n.velocity),
        "instrument": int(n.program),
        "is_drum": bool(n.is_drum),
        "confidence": 1.0,
        "backend": "ymt3_v2",
    } for n in raw]