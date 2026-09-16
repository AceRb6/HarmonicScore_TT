"""Harmonic Score — configuración central del ml-service.
Fuentes: Reporte Técnico 2026-B115 (§3.5.2, Ilustración 15) y
ground truth del checkpoint (inspección de hyper_parameters).
"""
from pathlib import Path
import torch

# --- Directorios ---
BASE_DIR = Path(__file__).resolve().parent
STORAGE = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE / "uploads"
OUTPUT_DIR = STORAGE / "outputs"
LOG_DIR = STORAGE / "logs"
VEROVIO_RESOURCE_PATH = r"C:\verovio_data"
for _d in (UPLOAD_DIR, OUTPUT_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# --- CQT: SOLO análisis de polifonía (RF-08), §3.5.2 / Ilustración 15 ---
CQT_PARAMS = {
    "sr": 44100,
    "hop_length": 512,
    "fmin": 32.7,          # Do0
    "n_bins": 96,          # ← 8 octavas (C0–C8); NO 264 (viola Nyquist, ver docstring)
    "bins_per_octave": 12,
    "filter_scale": 1.0,
    "norm": 1,
    "sparsity": 0.01,
    "window": "hann",
}
FRAME_RATE = CQT_PARAMS["sr"] / CQT_PARAMS["hop_length"]    # 86.13 fps

# --- Entrada del modelo (ground truth del checkpoint, NO del reporte) ---
MODEL_AUDIO = {"sr": 16000, "window": 32767}    # ventana ≈ 2.048 s
EVENT_GRID_MS = 10.0                            # resolución del tokenizer

# --- Checkpoint YourMT3+ MoE local (8 expertos, top-k=2) ---
CHECKPOINT_PATH = BASE_DIR / "models" / "amt" / "logs" / "2024" / \
    "mc13_256_g4_all_v7_mt3f_sqr_rms_moe_wf4_n8k2_silu_rope_rp_b36_nops" / \
    "checkpoints" / "last.ckpt"

# --- Backend de inferencia: "real" | "baseline" (seguro del Entregable 1) ---
MODEL_BACKEND = "real"

# --- Hardware real: RTX 4050 6 GB VRAM / 16 GB RAM ---
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
USE_FP16 = DEVICE.type == "cuda"

# --- RF-02 / RF-03 / CU-04 ---
ALLOWED_EXT = {".mp3", ".wav"}
MAX_BYTES = 50 * 1024 * 1024
MAX_DURATION_S = 360.0