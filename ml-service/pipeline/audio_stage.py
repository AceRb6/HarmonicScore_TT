"""
Etapa 1: carga y validación técnica del audio (RF-01, RF-02, RF-03).

Responsabilidades:
- Validar existencia y accesibilidad del archivo
- Cargar audio con parámetros estandarizados (44.1 kHz, mono)
- Validar duración (0.5s - 360s)
- Normalizar amplitud al 95% del pico (mejora documentada en Sección 6.3.1)
- Retornar métricas de calidad de señal para debugging
"""
import logging
from pathlib import Path
from typing import Tuple

import librosa
import numpy as np

import settings as config

log = logging.getLogger("harmonic.audio_stage")


def load_audio(path: Path) -> Tuple[np.ndarray, int, float, dict]:
    """
    Carga y valida un archivo de audio.
    
    Args:
        path: Ruta al archivo de audio (MP3 o WAV)
        
    Returns:
        Tuple conteniendo:
        - y: Array de audio normalizado (numpy.ndarray)
        - sr: Sample rate (int)
        - duration: Duración en segundos (float)
        - metrics: Diccionario con métricas de calidad de señal
        
    Raises:
        FileNotFoundError: Si el archivo no existe
        ValueError: Si la duración está fuera del rango permitido
        RuntimeError: Si hay error al decodificar el audio
    """
    path = Path(path)
    
    # 1. Validar existencia del archivo
    if not path.exists():
        raise FileNotFoundError(f"Archivo no encontrado: {path}")
    
    if not path.is_file():
        raise ValueError(f"La ruta no es un archivo válido: {path}")
    
    # 2. Cargar audio con parámetros estandarizados
    try:
        log.info(f"Cargando audio: {path.name} ({path.stat().st_size / 1e6:.2f} MB)")
        y, sr = librosa.load(str(path), sr=config.CQT_PARAMS["sr"], mono=True)
    except Exception as e:
        log.error(f"Error al decodificar audio: {e}")
        raise RuntimeError(f"No se pudo decodificar el archivo de audio: {e}") from e
    
    # 3. Calcular duración
    duration = len(y) / sr
    
    # 4. Validar duración (RF-04: máximo 6 minutos)
    if duration > config.MAX_DURATION_S:
        log.warning(f"Duración excedida: {duration:.2f}s > {config.MAX_DURATION_S}s")
        raise ValueError(
            f"Duración excedida ({duration:.1f}s). "
            f"El archivo no debe superar los {config.MAX_DURATION_S // 60} minutos"
        )
    
    if duration < 0.5:
        log.warning(f"Audio demasiado corto: {duration:.2f}s")
        raise ValueError("Audio demasiado corto para transcribir (mínimo 0.5 segundos)")
    
    # 5. Calcular métricas de calidad de señal (ANTES de normalizar)
    rms_original = float(np.sqrt(np.mean(y ** 2)))
    peak_original = float(np.max(np.abs(y)))
    
    # 6. Normalizar amplitud al 95% del pico (mejora documentada en Sección 6.3.1)
    # Esto asegura que el modelo reciba una señal con rango dinámico consistente
    if peak_original > 0:
        y = librosa.util.normalize(y, norm=np.inf) * 0.95
        log.info(f"Audio normalizado: RMS={rms_original:.4f} → pico={peak_original:.4f} → 0.95")
    else:
        log.warning("Audio silencioso (pico = 0), no se puede normalizar")
    
    # 7. Calcular métricas finales
    metrics = {
        "duration_s": round(duration, 2),
        "sample_rate": sr,
        "samples": len(y),
        "rms_original": round(rms_original, 4),
        "peak_original": round(peak_original, 4),
        "rms_normalized": round(float(np.sqrt(np.mean(y ** 2))), 4),
        "peak_normalized": round(float(np.max(np.abs(y))), 4),
        "file_size_mb": round(path.stat().st_size / 1e6, 2)
    }
    
    log.info(
        f"Audio cargado: {duration:.2f}s | {sr}Hz | "
        f"RMS={metrics['rms_normalized']:.4f} | pico={metrics['peak_normalized']:.4f}"
    )
    
    return y, sr, duration, metrics