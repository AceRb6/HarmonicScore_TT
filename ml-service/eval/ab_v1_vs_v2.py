"""Comparación A/B entre versión 1 (bug) y versión 2 (adaptador corregido).

Ejecuta la misma pieza con ambos backends y compara cobertura/notas.
"""
import sys
from pathlib import Path
ML = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML))

import settings as config
from pipeline.model_stage import RealModel, _baseline_notes
from pipeline.ymt3_adapter import YMT3Adapter

TESTS = ML / "storage" / "tests"

def locate(name):
    for base in (TESTS, TESTS / "v1"):
        p = base / name
        if p.exists():
            return p
    return None

def run_v1(audio_path):
    """Backend original (bug de subtask_key)."""
    notes = RealModel.get().transcribe(audio_path)
    dur = librosa.get_duration(path=str(audio_path))
    last = max((n.onset for n in notes), default=0.0)
    return len(notes), (last / dur if dur else 0.0)

def run_v2(audio_path):
    """Backend v2 con condicionamiento corregido."""
    notes = YMT3Adapter.get().transcribe(audio_path)
    dur = librosa.get_duration(path=str(audio_path))
    last = max((n.onset for n in notes), default=0.0)
    return len(notes), (last / dur if dur else 0.0)

if __name__ == "__main__":
    import librosa
    print("pieza | v1(notas,cov) | v2(notas,cov) | Δ notas | Δ cobertura")
    for piece in ["andersen-24-etudes-op15-no5.mp3"]:
        p = locate(piece)
        if p is None:
            print(f"{piece}: NO ENCONTRADA"); continue
        
        n1, c1 = run_v1(p)
        n2, c2 = run_v2(p)
        dn = n2 - n1
        dc = c2 - c1
        print(f"{piece}: v1=({n1},{c1:.2f}) | v2=({n2},{c2:.2f}) | Δ={dn:+d} notas, {dc:+.2f} cov")