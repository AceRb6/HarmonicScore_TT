"""Mide el horizonte fiable de v1 comparando contra MIDI de referencia.
Busca recursivamente MP3 y MIDI en storage/tests/."""
import sys
import numpy as np
import librosa
import pretty_midi
import torch
from pathlib import Path

ML = Path(__file__).resolve().parents[1]
SRC = ML / "models" / "amt" / "src"
for p in (str(ML), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)

import settings as config
from utils.audio import slice_padded_array
from pipeline.model_stage import RealModel

SEG = config.MODEL_AUDIO["window"]
SR = config.MODEL_AUDIO["sr"]
SEG_SEC = SEG / SR

def locate(stem, exts):
    """Busca recursivamente en storage/tests/"""
    for e in exts:
        hits = list((ML / "storage" / "tests").rglob(stem + e))
        if hits:
            return hits[0]
    return None

def load_midi_notes(midi_path):
    """Extrae notas del MIDI: [(onset_s, offset_s, pitch), ...]"""
    pm = pretty_midi.PrettyMIDI(str(midi_path))
    notes = []
    for inst in pm.instruments:
        if not inst.is_drum:
            for note in inst.notes:
                notes.append((note.start, note.end, note.pitch))
    return sorted(notes, key=lambda x: x[0])

def count_notes_in_range(notes, t0, t1, tol=0.05):
    """Cuenta notas de referencia en el rango [t0, t1]"""
    return sum(1 for onset, _, _ in notes if t0 - tol <= onset <= t1 + tol)

stem = sys.argv[1] if len(sys.argv) > 1 else "andersen-24-etudes-op15-no5"
audio = locate(stem, [".mp3", ".wav"])
midi = locate(stem, [".mid", ".midi"])

print(f"Audio: {audio}")
print(f"MIDI:  {midi}")
if audio is None or midi is None:
    print("ERROR: No se encontraron ambos archivos"); sys.exit(1)

print("\nCargando audio y MIDI...")
y, _ = librosa.load(str(audio), sr=SR, mono=True)
if getattr(config, "NORMALIZE_INPUT", True):
    y = np.clip(y / (np.max(np.abs(y)) + 1e-8), -1, 1) * config.NORMALIZE_TARGET

ref_notes = load_midi_notes(midi)
print(f"Notas de referencia en MIDI: {len(ref_notes)}")

x = y.astype(np.float32).reshape(1, -1)
segs = slice_padded_array(x, SEG, SEG, pad=True).astype(np.float32)
n_seg = segs.shape[0]

model = RealModel.get().model
tm = model.task_manager

print(f"\nEjecutando v1 sobre {n_seg} ventanas...")
segs_t = torch.from_numpy(segs).unsqueeze(1).to(config.DEVICE)
with torch.no_grad():
    preds_seq, _ = model.inference_file(bsz=1, audio_segments=segs_t)

def decode_fresh(idx):
    t = torch.from_numpy(segs[idx:idx+1]).unsqueeze(1).to(config.DEVICE)
    with torch.no_grad():
        preds = model.inference(t, None)
    arr = preds.detach().cpu().numpy()
    return sum(len(tm.detokenize([int(v) for v in arr[0, c]])[0])
               for c in range(arr.shape[1]))

print(f"\n{'win':>4} | {'t0':>5} | {'t1':>5} | {'ref':>3} | {'v1':>3} | {'fresh':>5} | {'prec':>5} | estado")
print("-" * 65)

horizon_v1 = 0
for i in range(n_seg):
    t0 = i * SEG_SEC
    t1 = (i + 1) * SEG_SEC
    n_ref = count_notes_in_range(ref_notes, t0, t1)

    p = np.asarray(preds_seq[i])
    if p.ndim == 2: p = p[None, ...]
    n_v1 = len(tm.detokenize([int(v) for v in p[0, 0]])[0])
    n_fresh = decode_fresh(i)
    prec = n_v1 / n_ref if n_ref > 0 else (0.0 if n_v1 == 0 else 1.0)

    if n_v1 > 0 and (n_ref == 0 or prec >= 0.3):
        estado = "OK"
        horizon_v1 = i + 1
    elif n_fresh > 0:
        estado = "DEGENERADA"
    else:
        estado = "SILENCIO"

    print(f"{i:4d} | {t0:5.1f} | {t1:5.1f} | {n_ref:3d} | {n_v1:3d} | {n_fresh:5d} | {prec:5.2f} | {estado}")

R = max(2, horizon_v1)
print(f"\nHorizonte fiable v1: {horizon_v1} ventanas ≈ {horizon_v1 * SEG_SEC:.2f} s")
print(f"-> usar segmentos de R={R} ventanas ({R * SEG_SEC:.2f} s) en adapter v4")