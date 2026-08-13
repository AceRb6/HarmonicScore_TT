#!/usr/bin/env python
"""Validación técnica del checkpoint YourMT3-YPTF-MoE-M"""
import sys
from pathlib import Path
import torch

# 1. Agregar el directorio fuente de YourMT3 al PYTHONPATH
SRC_DIR = Path("models/amt/src")
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

CKPT_PATH = Path("models/amt/logs/2024/mc13_256_g4_all_v7_mt3f_sqr_rms_moe_wf4_n8k2_silu_rope_rp_b36_nops/checkpoints/last.ckpt")

def validate():
    if not CKPT_PATH.exists():
        print(f"❌ Checkpoint no encontrado: {CKPT_PATH}")
        return False
    
    print("📦 Cargando metadata del checkpoint...")
    try:
        # Cargar en CPU. weights_only=False es necesario porque el checkpoint 
        # contiene configs/objetos pickled, no solo tensores.
        ckpt = torch.load(CKPT_PATH, map_location="cpu", weights_only=False)
        
        hp = ckpt.get("hyper_parameters", {})
        model_cfg = hp.get("model_cfg", {})
        enc = model_cfg.get("encoder", {}).get("perceiver-tf", {})
        
        print(f"✅ Checkpoint válido: {CKPT_PATH.name}")
        print(f"   • Arquitectura: {enc.get('encoder_type')}")
        print(f"   • FF Layer: {enc.get('ff_layer_type')}")  # Debe ser 'moe'
        print(f"   • Experts: {enc.get('moe_num_experts')}")  # Debe ser 8
        print(f"   • Top-k: {enc.get('moe_topk')}")          # Debe ser 2
        print(f"   • D model: {enc.get('d_model')}")
        
        if enc.get("ff_layer_type") == "moe" and enc.get("moe_num_experts") == 8:
            print("\n🎉 Configuración MoE confirmada. Listo para inferencia.")
            return True
        print("\n⚠️ Configuración no coincide con MoE-YPTF esperado.")
        return False
        
    except Exception as e:
        print(f"\n❌ Error de carga: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    sys.exit(0 if validate() else 1)