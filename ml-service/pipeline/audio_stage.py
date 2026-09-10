"""Etapa 1: carga y validación técnica del audio."""
import librosa
import settings as config


def load_audio(path):
    """Retorna (y, sr, duración_s). Valida duración mínima y máxima."""
    y, sr = librosa.load(str(path), sr=config.CQT_PARAMS["sr"], mono=True)
    duration = len(y) / sr
    if duration > config.MAX_DURATION_S:
        raise ValueError("Duración excedida. El archivo no debe superar los seis minutos")
    if duration < 0.5:
        raise ValueError("Audio demasiado corto para transcribir")
    return y, sr, duration