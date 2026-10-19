"""Diagnóstico de ventaneo (H-27): verifica qué audio recibe cada ventana.
Hipótesis A: slicing roto  -> ventanas 1+ con RMS ≈ 0.
Hipótesis B: slicing correcto -> el colapso viene del modelo (dominio/condicionamiento).
Uso: py eval\standalone.py [ruta_al_audio]
"""
import sys
from pathlib import Path

import numpy as np
import librosa

ML = Path(__file__).resolve().parents[1]        # ml-service/
SRC = ML / "models" / "amt" / "src"             # repo vendado (utils, model)
for p in (str(ML), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

import settings as config
from utils.audio import slice_padded_array

SEG = config.MODEL_AUDIO["window"]              # 32767 muestras
SR = config.MODEL_AUDIO["sr"]                   # 16000 Hz



def main():
    default = ML / "storage" / "tests" / "v1" / "andersen-24-etudes-op15-no5.mp3"
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else default
    if not path.exists():
        raise FileNotFoundError(f"No existe {path}")

    y, sr = librosa.load(str(path), sr=SR, mono=True)

    # Misma normalización que producción (parche B)
    peak = float(np.max(np.abs(y))) + 1e-8
    target = getattr(config, "NORMALIZE_TARGET", 0.95)
    x = (np.clip(y / peak, -1.0, 1.0) * target).astype(np.float32)

    # Mismo ventaneo que model_stage
    segs = np.asarray(
        slice_padded_array(x.reshape(1, -1), slice_length=SEG, slice_hop=SEG, pad=True),
        dtype=np.float32)

    axes = tuple(range(1, segs.ndim))           # promedio sobre canales+muestras
    rms = np.sqrt(np.mean(segs ** 2, axis=axes))
    con_audio = int(np.sum(rms > 1e-4))

    print(f"archivo: {path.name}")
    print(f"shape segs={segs.shape} | ventanas con audio real: {con_audio}/{len(rms)}")
    for i in range(min(8, len(rms))):
        print(f"  seg {i:02d} RMS={rms[i]:.4f}")

    if con_audio >= len(rms) - 1:
        print("VEREDICTO: slicing CORRECTO -> el colapso es del modelo (Hipótesis B).")
    else:
        print("VEREDICTO: slicing ROTO -> ventanas vacías alimentan al modelo (Hipótesis A).")


if __name__ == "__main__":
    main()