"""Convierte un MusicXML de storage/outputs a SVG (Verovio) y PDF (Edge headless).

Deltas documentados vs TT-I (tabla de deltas TT-II):
  D1: los bindings Python de Verovio no exponen renderToPDF -> SVG + impresion headless.
  D2: el C++ de Verovio no resuelve rutas no-ASCII en Windows (venv bajo
      '...\\TITULACION\\...') -> staging ASCII para recursos SMuFL y XML de entrada.
  D3: cairosvg requiere libcairo (ausente en Windows) -> se descarta esa ruta.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import verovio

ML = Path(__file__).resolve().parents[1]
OUTPUTS = ML / "storage" / "outputs"
STAGE = Path(tempfile.gettempdir()) / "hs_verovio_ascii"   # ruta 100% ASCII

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def _ascii_resources() -> Path:
    """Copia los recursos SMuFL del paquete a una ruta ASCII (mitiga D2)."""
    src = Path(verovio.__file__).resolve().parent / "data"
    dst = STAGE / "data"
    if not dst.exists():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    return dst


def _edge() -> Path:
    for c in EDGE_CANDIDATES:
        if Path(c).exists():
            return Path(c)
    raise RuntimeError("No se encontro msedge.exe para la impresion PDF")


def render(xml_path: Path) -> Path:
    xml_path = Path(xml_path)
    work = STAGE / xml_path.stem
    work.mkdir(parents=True, exist_ok=True)

    # 1) Staging ASCII del XML de entrada
    xml_ascii = work / "score.musicxml"
    shutil.copyfile(xml_path, xml_ascii)

    # 2) Toolkit con recursos en ruta ASCII
    tk = verovio.toolkit()
    if hasattr(tk, "setResourcePath"):
        tk.setResourcePath(str(_ascii_resources()))
    if not tk.loadFile(str(xml_ascii)):
        raise RuntimeError("Verovio no pudo cargar el MusicXML incluso en staging ASCII")

    # 3) SVG por pagina (el SVG de Verovio es autocontenido: lleva los glifos Bravura
    #    como trazas vectoriales, por eso Edge lo renderiza fielmente sin fuentes externas)
    svgs = []
    for i in range(1, tk.getPageCount() + 1):
        p = work / f"page_{i:03d}.svg"
        p.write_text(tk.renderToSVG(i), encoding="utf-8")
        svgs.append(p)

    # 4) HTML paginado A4 y impresion headless
    pages = "\n".join(
        f'<section class="page"><img src="{p.name}"></section>' for p in svgs
    )
    html = work / "score.html"
    html.write_text(
        "<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
        "@page{size:A4 portrait;margin:10mm}"
        "html,body{margin:0;padding:0}"
        ".page{width:190mm;height:277mm;page-break-after:always;"
        "display:flex;align-items:center;justify-content:center;overflow:hidden}"
        ".page:last-child{page-break-after:auto}"
        ".page img{max-width:100%;max-height:100%}"
        f"</style></head><body>{pages}</body></html>",
        encoding="utf-8",
    )

    pdf_tmp = work / "score.pdf"
    edge = _edge()
    for flag in ("--headless=new", "--headless"):
        r = subprocess.run(
            [str(edge), flag, "--disable-gpu", "--no-pdf-header-footer",
             f"--print-to-pdf={pdf_tmp}", str(html)],
            capture_output=True, timeout=180,
        )
        if pdf_tmp.exists():
            break
    if not pdf_tmp.exists():
        raise RuntimeError(f"Edge no genero el PDF: {r.stderr.decode(errors='ignore')[:500]}")

    # 5) El PDF final vive en storage/outputs con nombre RF-06
    final = OUTPUTS / (xml_path.stem + ".pdf")
    shutil.copyfile(pdf_tmp, final)
    return final


if __name__ == "__main__":
    if len(sys.argv) > 1:
        target = Path(sys.argv[1])
    else:
        target = max(OUTPUTS.glob("*.musicxml"), key=lambda p: p.stat().st_mtime)
    out = render(target)
    print("PDF generado:", out)