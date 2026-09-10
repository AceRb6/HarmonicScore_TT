"""Etapa 2: representación espectral CQT + clasificación de polifonía (RF-08, RF-09)."""
import numpy as np
import torch
import librosa
import settings as config


def compute_cqt(y):
    """Magnitud CQT (T, 264) con parámetros exactos del reporte."""
    cqt = librosa.cqt(
        y=y, sr=config.CQT_PARAMS["sr"],
        hop_length=config.CQT_PARAMS["hop_length"],
        fmin=config.CQT_PARAMS["fmin"], n_bins=config.CQT_PARAMS["n_bins"],
        bins_per_octave=config.CQT_PARAMS["bins_per_octave"],
        filter_scale=config.CQT_PARAMS["filter_scale"],
        norm=config.CQT_PARAMS["norm"], sparsity=config.CQT_PARAMS["sparsity"],
        window=config.CQT_PARAMS["window"],
    )
    return np.abs(cqt).T                      # (T, 264)


def classify_polyphony(mag):
    """
    Entropía espectral (Ilustración 23).
    DECISIÓN DOCUMENTADA: normalizamos la entropía entre [0,1] dividiendo por
    log2(n_bins) para que los umbrales 0.35/0.65/0.85/0.95 del reporte sean
    matemáticamente consistentes (la entropía cruda de 264 bins llega a ~8).
    """
    ents = []
    for frame in mag:
        total = frame.sum()
        if total < 1e-10:
            continue
        p = frame / total
        ents.append(-np.sum(p * np.log2(p + 1e-10)))
    entropy = float(np.mean(ents)) if ents else 0.0
    norm_ent = entropy / np.log2(config.CQT_PARAMS["n_bins"])

    if norm_ent < 0.35:   level = "mono"
    elif norm_ent < 0.65: level = "low"
    elif norm_ent < 0.85: level = "medium"
    elif norm_ent < 0.95: level = "high"
    else:                 level = "extreme"
    return norm_ent, level


def to_tensor(mag):
    """Tensor de entrada (1, 1, T, 264) normalizado, §3.5.1."""
    db = librosa.amplitude_to_db(mag, ref=np.max)
    norm = ((db - db.mean()) / (db.std() + 1e-8)).astype(np.float32)
    return torch.from_numpy(norm).unsqueeze(0).unsqueeze(0)