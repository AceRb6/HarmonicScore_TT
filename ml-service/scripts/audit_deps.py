"""Auditoría de dependencias: stack fijo del reporte + imports reales de notebooks."""
import ast
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]          # harmonic-score-app/
EXCLUDE = {".venv", "venv", "venv_harmonic", "node_modules", "__pycache__", ".git", "storage"}

# Stack fijo (import -> paquete pip con pin del reporte)
STACK = {
    "numpy": "numpy==1.26.4", "scipy": "scipy==1.11.4", "pandas": "pandas==2.1.4",
    "librosa": "librosa==0.11.0", "soundfile": "soundfile==0.12.1",
    "torch": "torch==2.1.2+cu118", "torchaudio": "torchaudio==2.1.2+cu118",
    "transformers": "transformers==4.45.1", "einops": "einops==0.7.0",
    "basic_pitch": "basic-pitch==0.4.0", "ray": "ray==2.9.3",
    "fastapi": "fastapi==0.115.0", "uvicorn": "uvicorn==0.30.6",
    "multipart": "python-multipart==0.0.9", "pydantic": "pydantic==2.9.0",
    "pydantic_settings": "pydantic-settings==2.5.0",
    "music21": "music21==9.1.0", "verovio": "verovio==4.3.1", "cairosvg": "cairosvg==2.7.1",
    "apscheduler": "APScheduler==3.10.4", "jose": "python-jose==3.3.0",
    "passlib": "passlib==1.7.4", "tqdm": "tqdm==4.66.4", "dotenv": "python-dotenv==1.0.1",
    "psutil": "psutil==6.0.0", "matplotlib": "matplotlib==3.8.4",
    "mir_eval": "mir_eval==0.7", "pytest": "pytest==7.4.4",
    "IPython": "ipython==8.19.0", "ipykernel": "jupyter==1.0.0",
}
PIP_NAME = {"cv2": "opencv-python", "sklearn": "scikit-learn", "PIL": "Pillow",
            "yaml": "PyYAML", "mpl_toolkits": "matplotlib", "bs4": "beautifulsoup4"}
LOCAL = {"config", "pipeline", "jobs", "app", "orchestrator", "cqt", "utils",
         "models", "scripts", "main", "api", "google", "get_ipython"}


def notebook_imports():
    """Extrae imports reales de todos los .ipynb del repo."""
    found = set()
    for nb in ROOT.rglob("*.ipynb"):
        if EXCLUDE & set(nb.parts):
            continue
        try:
            cells = json.loads(nb.read_text(encoding="utf-8"))["cells"]
        except Exception:
            continue
        for cell in cells:
            if cell.get("cell_type") != "code":
                continue
            src = "".join(cell.get("source", []))
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    found |= {a.name.split(".")[0] for a in node.names}
                elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                    found.add(node.module.split(".")[0])
    return found


def main():
    required = (set(STACK) | notebook_imports()) - set(sys.stdlib_module_names) - LOCAL
    missing = []
    for mod in sorted(required):
        try:
            if importlib.util.find_spec(mod) is None:
                missing.append(mod)
        except (ImportError, ValueError):
            missing.append(mod)

    print("=" * 62)
    if not missing:
        print("✅ Sin dependencias faltantes en el entorno activo")
    else:
        print(f"❌ FALTAN {len(missing)} PAQUETES:")
        for mod in missing:
            print(f"   {mod:18s} → {STACK.get(mod, PIP_NAME.get(mod, mod))}")
    print("=" * 62)
    return missing


if __name__ == "__main__":
    main()