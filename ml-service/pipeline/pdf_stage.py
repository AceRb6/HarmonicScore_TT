"""
Etapa 6b — Renderizado MusicXML 4.0 → PDF (RF-13).

Fuente única de verdad de la conversión final a PDF: la consumen
pipeline.score_stage (flujo productivo) y scripts/musicxml_to_pdf.py (CLI de pruebas).

Cadena de estrategias (deltas D1/D3 de la tabla de deltas TT-II):
  1) cairosvg        → preferida en Linux/CI (libcairo disponible).
  2) Edge headless   → Windows de desarrollo (sin libcairo, D3); perfil temporal,
                       sin ventanas ni alertas visibles.
  3) svglib+reportlab→ último recurso (calidad tipográfica reducida).
"""
from __future__ import annotations

import io
import logging
import subprocess
import tempfile
from pathlib import Path

log = logging.getLogger("harmonic.pdf_stage")

EDGE_CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
)


def musicxml_a_svg(xml_path: Path) -> list[str]:
    """Verovio: MusicXML → páginas SVG con tipografía Bravura (SMuFL)."""
    import verovio

    tk = verovio.toolkit()
    if not tk.loadFile(str(xml_path)):
        raise RuntimeError(f"Verovio no pudo cargar el MusicXML: {xml_path}")
    n_pages = tk.getPageCount()
    if not n_pages:
        raise RuntimeError("Verovio no generó páginas (MusicXML vacío o inválido)")
    return [tk.renderToSVG(i) for i in range(1, n_pages + 1)]


def _merge_pdfs(tmp_pdfs: list[Path], pdf_path: Path) -> None:
    from pypdf import PdfWriter

    writer = PdfWriter()
    for p in tmp_pdfs:
        writer.append(str(p))
    with open(pdf_path, "wb") as fh:
        writer.write(fh)


def _pdf_via_cairosvg(svgs: list[str], pdf_path: Path, workdir: Path) -> None:
    import cairosvg

    tmp = []
    for i, svg in enumerate(svgs, 1):
        p = workdir / f"page_{i:03d}.pdf"
        cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=str(p))
        tmp.append(p)
    _merge_pdfs(tmp, pdf_path)


def _pdf_via_edge(svgs: list[str], pdf_path: Path, workdir: Path) -> None:
    edge = next((Path(c) for c in EDGE_CANDIDATES if Path(c).exists()), None)
    if edge is None:
        raise RuntimeError("No se encontró msedge.exe")

    html = workdir / "score.html"
    pages = "\n".join(f'<section class="page">{s}</section>' for s in svgs)
    html.write_text(
        "<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
        "@page{size:A4 portrait;margin:12mm}"
        "html,body{margin:0;padding:0}"
        ".page{page-break-after:always;display:flex;align-items:center;justify-content:center}"
        ".page:last-child{page-break-after:auto}"
        ".page svg{max-width:100%;height:auto}"
        "</style></head><body>" + pages + "</body></html>",
        encoding="utf-8",
    )
    cmd = [
        str(edge), "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        f"--user-data-dir={workdir / 'edge-profile'}",
        "--no-first-run", "--no-default-browser-check",
        "--disable-extensions", "--disable-popup-blocking",
        "--hide-scrollbars", "--virtual-time-budget=10000",
        html.as_uri(),
    ]
    r = subprocess.run(cmd, capture_output=True, timeout=180)
    if not pdf_path.exists():
        raise RuntimeError(f"Edge no generó el PDF: {r.stderr.decode(errors='ignore')[:400]}")


def _pdf_via_svglib(svgs: list[str], pdf_path: Path, workdir: Path) -> None:
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPDF

    tmp = []
    for i, svg in enumerate(svgs, 1):
        drawing = svg2rlg(io.StringIO(svg))
        if drawing is None:
            raise RuntimeError("svglib no pudo interpretar el SVG")
        p = workdir / f"page_{i:03d}.pdf"
        renderPDF.drawToFile(drawing, str(p))
        tmp.append(p)
    _merge_pdfs(tmp, pdf_path)


def render_musicxml_to_pdf(xml_path: Path, pdf_path: Path) -> Path:
    """Convierte un MusicXML a PDF usando la primera estrategia que funcione."""
    xml_path, pdf_path = Path(xml_path), Path(pdf_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    svgs = musicxml_a_svg(xml_path)
    errores = []
    with tempfile.TemporaryDirectory(prefix="hs_pdf_") as td:
        workdir = Path(td)
        for nombre, fn in (("cairosvg", _pdf_via_cairosvg),
                           ("edge-headless", _pdf_via_edge),
                           ("svglib", _pdf_via_svglib)):
            try:
                fn(svgs, pdf_path, workdir)
                log.info("PDF generado vía %s: %s (%d página(s))", nombre, pdf_path, len(svgs))
                return pdf_path
            except Exception as e:                      # se intenta la siguiente ruta
                errores.append(f"{nombre}: {e}")
                log.warning("Ruta de render %s falló: %s", nombre, e)
    raise RuntimeError("No se pudo generar el PDF: " + " | ".join(errores))