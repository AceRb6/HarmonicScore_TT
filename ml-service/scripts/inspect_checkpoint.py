"""Inspección profunda del checkpoint — fuente de verdad para inferencia.
v3: (1) ruta real: ml-service/models/amt/logs/2024/<run>/checkpoints/last.ckpt
    (2) sys.path con models/amt/src para reconstruir clases locales (utils, model, config)
"""
import json
import sys
import torch
from pathlib import Path

ML = Path(__file__).resolve().parents[1]                     # ml-service/

# --- Código fuente de entrenamiento (para el unpickle) ---
SRC = ML / "models" / "amt" / "src"
if not SRC.exists():
    hits = list((ML / "models").rglob("train.py"))
    SRC = hits[0].parent if hits else SRC
sys.path.insert(0, str(SRC))

# --- Checkpoint MoE (8 expertos, top-k=2) ---
RUN = "mc13_256_g4_all_v7_mt3f_sqr_rms_moe_wf4_n8k2_silu_rope_rp_b36_nops"
CKPT = ML / "models" / "amt" / "logs" / "2024" / RUN / "checkpoints" / "last.ckpt"

print("SRC     :", SRC, "-> existe:", SRC.exists())
print("CKPT    :", CKPT, "-> existe:", CKPT.exists())

ckpt = torch.load(CKPT, map_location="cpu", weights_only=False)

print("== Keys top-level ==", list(ckpt.keys()))
print("== PL version ==", ckpt.get("pytorch-lightning_version"))

print("== hyper_parameters (completo) ==")
print(json.dumps(dict(ckpt.get("hyper_parameters", {})), indent=2, default=str))

sd = ckpt.get("state_dict", {})
n = sum(v.numel() for v in sd.values() if hasattr(v, "numel"))
print(f"== Parámetros totales: {n/1e6:.1f}M ==")

print("== Shapes representativos (primeros 30) ==")
for i, (k, v) in enumerate(sd.items()):
    if hasattr(v, "shape"):
        print(f"  {k}: {tuple(v.shape)}")
    if i >= 30:
        break