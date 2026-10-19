"""A/B de normalización de amplitud (validación de H-27 / shift de escala)."""
import sys
from pathlib import Path
ML = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML))

import numpy as np, librosa, soundfile as sf
from pipeline import model_stage

TESTS = ML / "storage" / "tests"

def locate(name):
    for base in (TESTS, TESTS / "v1"):
        p = base / name
        if p.exists():
            return p
    return None

def run(y, sr, tag):
    tmp = TESTS / f"_ab_{tag}.wav"
    sf.write(tmp, y.astype(np.float32), sr)
    notes = model_stage.infer_notes(tmp)
    dur = len(y) / sr
    last = max((n["onset"] for n in notes), default=0.0)
    return len(notes), (last / dur if dur else 0.0)

print("pieza | crudo(notas,cov) | normalizado(notas,cov)")
for piece in ["andersen-24-etudes-op15-no2.mp3",
              "andersen-24-etudes-op15-no5.mp3"]:
    p = locate(piece)
    if p is None:
        print(f"{piece}: NO ENCONTRADA"); continue
    y, sr = librosa.load(str(p), sr=16000, mono=True)
    peak = float(np.max(np.abs(y))) + 1e-8
    y_norm = np.clip(y / peak, -1.0, 1.0) * 0.95
    n_r, c_r = run(y, sr, "raw")
    n_n, c_n = run(y_norm, sr, "norm")
    print(f"{piece}: RAW=({n_r},{c_r:.2f}) | NORM=({n_n},{c_n:.2f})")