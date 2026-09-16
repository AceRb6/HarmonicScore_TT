"""
Etapa 2: Representación CQT (RF-09) y clasificación de polifonía (RF-08).

Nota de ingeniería (para el TT-II): el TT-I (§3.5.2, Tabla 2) reporta
n_bins=264 ("22 octavas"), pero con fmin=32.7 Hz y bins_per_octave=12 eso
produce fmax = 32.7 * 2^(264/12) ≈ 137 MHz, violando el teorema de Nyquist
para sr=44.1 kHz (22.05 kHz). Se corrige a n_bins=96 (8 octavas), que es
consistente con el fmax=8372 Hz que el mismo reporte declara en su Tabla 3
y cubre el rango completo del piano (A0=27.5 Hz a C8=4186 Hz).
"""
import logging

import numpy as np
import librosa

import settings as config

log = logging.getLogger("harmonic.cqt_stage")

P = config.CQT_PARAMS


# ---------------------------------------------------------------------
# RF-09: Representación espectral CQT
# ---------------------------------------------------------------------
def compute_cqt(y: np.ndarray) -> np.ndarray:
    """Magnitud CQT alineada con percepción musical (relación Δf/f constante)."""
    cqt = librosa.cqt(
        y=y,
        sr=P["sr"],
        hop_length=P["hop_length"],
        fmin=P["fmin"],
        n_bins=P["n_bins"],
        bins_per_octave=P["bins_per_octave"],
        filter_scale=P["filter_scale"],
        norm=P["norm"],
        sparsity=P["sparsity"],
        window=P["window"],
    )
    mag = np.abs(cqt)
    log.info("CQT computada: shape %s (n_bins=%d, sr=%d Hz)",
             mag.shape, P["n_bins"], P["sr"])
    return mag


# ---------------------------------------------------------------------
# RF-08: Clasificación monofónico/polifónico por entropía espectral
# ---------------------------------------------------------------------
def classify_polyphony(mag: np.ndarray):
    """
    Entropía espectral normalizada por frame (0 = tono puro, 1 = ruido blanco),
    promediada sobre los frames con energía audible.

    Umbrales RF-08 / Ilustración 23 del TT-I:
        entropía < 0.35  → señal monofónica (flauta, voz solista)
        entropía ≥ 0.35  → señal polifónica (piano, guitarra)

    Returns:
        (entropy_mean, level) con level en {'monofonico', 'polifonico'}
    """
    n_bins = mag.shape[0]
    energy = mag ** 2                                    # potencia por bin
    prob = energy / (energy.sum(axis=0, keepdims=True) + 1e-10)   # distribución por frame
    entropy = -np.sum(prob * np.log2(prob + 1e-10), axis=0)       # (T,)
    entropy_norm = entropy / np.log2(n_bins)                     # normalizada a [0, 1]

    # Excluir frames casi silenciosos para no sesgar con silencio digital
    frame_energy = energy.sum(axis=0)
    voiced = frame_energy > (frame_energy.max() * 1e-3)
    if not voiced.any():
        voiced = np.ones_like(voiced)

    e = float(entropy_norm[voiced].mean())
    level = "monofonico" if e < 0.35 else "polifonico"
    log.info("Polifonía: entropía=%.3f (%s) -> %s", e, entropy_detail(e), level)
    return e, level


def entropy_detail(e: float) -> str:
    """Granularidad de 5 niveles (Ilustración 23 TT-I).
    Reservada para el ruteo dinámico de expertos MoE en Ciclo 3."""
    if e < 0.35:
        return "mono"
    if e < 0.65:
        return "low"
    if e < 0.85:
        return "medium"
    if e < 0.95:
        return "high"
    return "extreme"