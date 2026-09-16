"""
Etapa 6: Generación de partitura MusicXML y PDF (RF-12/RF-13).
Convierte notas a MusicXML mediante music21, luego renderiza a PDF con Verovio.
Incluye cuantización de duraciones a figuras musicales expresables.
"""
import logging
from pathlib import Path

from music21 import stream, note, tempo, meter, instrument

import settings as config

log = logging.getLogger("harmonic.score_stage")

# Figuras musicales válidas en MusicXML (en fracciones de negra)
FIGURAS_MUSICALES = {
    4.0: 'whole',        # redonda
    3.0: 'dotted half',  # blanca con puntillo
    2.0: 'half',         # blanca
    1.5: 'dotted quarter',  # negra con puntillo
    1.0: 'quarter',      # negra
    0.75: 'dotted eighth', # corchea con puntillo
    0.5: 'eighth',       # corchea
    0.375: 'dotted 16th', # semicorchea con puntillo
    0.25: '16th',        # semicorchea
    0.125: '32nd',       # fusa
    0.0625: '64th',      # semifusa
}


def cuantizar_duracion(duracion_s: float, tempo_bpm: float = 120.0) -> float:
    """
    Convierte duración en segundos a la figura musical más cercana.
    
    Args:
        duracion_s: Duración en segundos
        tempo_bpm: Tempo estimado en beats por minuto
    
    Returns:
        Duración cuantizada en "negras" (beats), expresable en MusicXML
    """
    # Convertir segundos a negras (beats)
    duracion_negras = duracion_s * (tempo_bpm / 60.0)
    
    # Encontrar la figura musical más cercana
    figuras = sorted(FIGURAS_MUSICALES.keys())
    figura_cercana = min(figuras, key=lambda x: abs(x - duracion_negras))
    
    # Limitar a rango válido (entre semifusa y redonda)
    figura_cercana = max(0.0625, min(4.0, figura_cercana))
    
    return figura_cercana


def build_score(notes: list, pdf_path: Path):
    """
    Genera partitura MusicXML y la convierte a PDF.
    """
    if not notes:
        log.warning("No hay notas para generar partitura")
        return None
    
    # Crear stream de music21
    score = stream.Score()
    part = stream.Part()
    
    # Agregar instrumento (piano por defecto)
    inst = instrument.Piano()
    part.append(inst)
    
    # Agregar tempo (120 BPM por defecto)
    tempo_mark = tempo.MetronomeMark(number=120)
    part.append(tempo_mark)
    
    # Agregar compás 4/4
    time_sig = meter.TimeSignature('4/4')
    part.append(time_sig)
    
    # Ordenar notas por onset
    notes_sorted = sorted(notes, key=lambda n: n['onset'])
    
    # Convertir cada nota a objeto music21 con duración cuantizada
    current_time = 0.0
    for n in notes_sorted:
        # Insertar silencio si hay gap entre notas
        if n['onset'] > current_time:
            gap = n['onset'] - current_time
            gap_beats = cuantizar_duracion(gap, 120.0)
            if gap_beats >= 0.0625:  # Mínimo: semifusa
                rest = note.Rest()
                rest.quarterLength = gap_beats
                part.append(rest)
        
        # Crear nota con duración cuantizada
        duracion = n['offset'] - n['onset']
        duracion_beats = cuantizar_duracion(duracion, 120.0)
        
        # Crear nota musical
        nota = note.Note()
        nota.pitch.midi = n['pitch']
        nota.quarterLength = duracion_beats
        
        # Agregar velocity (dinámica)
        velocity = n.get('velocity', 80)
        if velocity < 40:
            nota.volume.velocity = 40  # pp
        elif velocity < 60:
            nota.volume.velocity = 60  # p
        elif velocity < 80:
            nota.volume.velocity = 80  # mp
        elif velocity < 100:
            nota.volume.velocity = 100  # mf
        else:
            nota.volume.velocity = 120  # f
        
        part.append(nota)
        current_time = n['offset']
    
    score.append(part)
    
    # Exportar a MusicXML
    xml_path = pdf_path.with_suffix('.musicxml')
    try:
        score.write("musicxml", fp=str(xml_path))
        log.info("MusicXML generado: %s", xml_path)
    except Exception as e:
        log.error("Error al generar MusicXML: %s", e)
        raise
    
    # Convertir MusicXML a PDF usando Verovio (SVG) + Edge headless
    try:
        import verovio
        import subprocess
        
        tk = verovio.toolkit()
        
        # Intentar configurar recursos SMuFL si existe en config
        if hasattr(config, 'VEROVIO_RESOURCE_PATH'):
            tk.setResourcePath(config.VEROVIO_RESOURCE_PATH)
        
        if not tk.loadFile(str(xml_path)):
            raise RuntimeError("Verovio no pudo cargar el MusicXML")
        
        page_count = tk.getPageCount()
        log.info("Verovio: %d páginas detectadas", page_count)
        
        # Intentar renderToPDF directo (por si la versión lo soporta)
        if hasattr(tk, 'renderToPDF'):
            try:
                pdf_bytes = tk.renderToPDF()
                pdf_path.write_bytes(pdf_bytes)
                log.info("PDF generado con renderToPDF: %s", pdf_path)
                return pdf_path
            except Exception as e:
                log.warning("renderToPDF falló, usando cadena SVG→HTML→PDF con Edge: %s", e)
        
        # Cadena SVG → HTML → PDF usando Edge headless (evita dependencia de Cairo)
        # Generar todas las páginas SVG
        svg_pages = []
        for page_num in range(1, page_count + 1):
            svg_content = tk.renderToSVG(page_num)
            svg_pages.append(svg_content)
        
        # Crear HTML que envuelve todas las páginas SVG con saltos de página
        html_content = "<!DOCTYPE html><html><head><meta charset='utf-8'><style>"
        html_content += "@page { size: A4; margin: 1cm; }"
        html_content += "body { margin: 0; padding: 0; }"
        html_content += ".page { page-break-after: always; width: 100%; height: 100vh; display: flex; align-items: center; justify-content: center; }"
        html_content += ".page:last-child { page-break-after: auto; }"
        html_content += "svg { max-width: 100%; max-height: 100%; }"
        html_content += "</style></head><body>"
        
        for svg in svg_pages:
            html_content += f'<div class="page">{svg}</div>'
        
        html_content += "</body></html>"
        
        # Guardar HTML temporal
        temp_html = pdf_path.with_suffix('.html')
        temp_html.write_text(html_content, encoding='utf-8')
        
        # Buscar Edge en rutas comunes de Windows
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        ]
        
        edge_exe = None
        for path in edge_paths:
            if Path(path).exists():
                edge_exe = path
                break
        
        if edge_exe is None:
            raise RuntimeError("No se encontró Microsoft Edge en el sistema")
        
        # Usar Edge headless para imprimir HTML a PDF
        subprocess.run([
            edge_exe,
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            str(temp_html)
        ], check=True, capture_output=True, timeout=60)
        
        # Limpiar HTML temporal
        temp_html.unlink(missing_ok=True)
        
        log.info("PDF generado con Edge headless: %s", pdf_path)
        return pdf_path
        
    except Exception as e:
        log.error("Error al generar PDF con Verovio: %s", e)
        # Fallback: devolver solo el MusicXML si Verovio falla
        log.warning("Devolviendo MusicXML sin PDF (puedes abrirlo con MuseScore/Dorico)")
        return xml_path