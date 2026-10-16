"""
Etapa 6 — Generación de partitura MusicXML 4.0 (RF-12) y delegación de RF-13.

Convierte la secuencia refinada de eventos (pitch, onset, offset, velocity)
en MusicXML 4.0 mediante music21, con figuras rítmicas cuantizadas y silencios
de relleno basados en el tempo y compás estimados dinámicamente.
"""
from __future__ import annotations

import logging
from pathlib import Path

from music21 import stream, note, tempo, meter, instrument, metadata

from pipeline.pdf_stage import render_musicxml_to_pdf

log = logging.getLogger("harmonic.score_stage")

# Figuras musicales válidas en MusicXML (en fracciones de negra / quarterLength)
FIGURAS_MUSICALES = {
    4.0: 'whole', 3.0: 'dotted half', 2.0: 'half', 1.5: 'dotted quarter',
    1.0: 'quarter', 0.75: 'dotted eighth', 0.5: 'eighth', 0.375: 'dotted 16th',
    0.25: '16th', 0.125: '32nd', 0.0625: '64th',
}

def cuantizar_duracion(duracion_s: float, tempo_bpm: float = 120.0) -> float:
    """Convierte segundos a la figura musical (quarterLength) más cercana según el tempo."""
    duracion_negras = duracion_s * (tempo_bpm / 60.0)
    figuras = sorted(FIGURAS_MUSICALES.keys())
    figura = min(figuras, key=lambda x: abs(x - duracion_negras))
    return max(0.0625, min(4.0, figura))

def build_score(notes: list, pdf_path: Path, bpm: float = 120.0, time_signature: str = "4/4", title: str = "Pieza sin título") -> Path:
    """
    Genera el MusicXML usando el tempo y compás estimados dinámicamente, 
    y delega el PDF. Devuelve la ruta del PDF final.
    """
    if not notes:
        raise ValueError("No hay notas para generar la partitura")

    score = stream.Score()

    # Inyección de metadatos
    md = metadata.Metadata()
    md.title = title
    md.composer = "Harmonic Score v.1.0"
    md.publisher = "Harmonic Score"
    md.rights = "Transcrito con Harmonic Score"
    transcriber = metadata.Contributor(name="Harmonic Score", role="transcriber")
    md.addContributor(transcriber)
    score.metadata = md

    part = stream.Part()
    part.append(instrument.Piano())
    
    # Usamos los valores dinámicos estimados para el tempo y compás
    part.append(tempo.MetronomeMark(number=int(round(bpm))))
    part.append(meter.TimeSignature(time_signature))

    current_time = 0.0
    for n in sorted(notes, key=lambda x: x['onset']):
        if n['onset'] > current_time:                      # silencio de relleno
            # Pasamos el bpm dinámico a la función de cuantización
            gap_beats = cuantizar_duracion(n['onset'] - current_time, tempo_bpm=bpm)
            if gap_beats >= 0.0625:
                rest = note.Rest()
                rest.quarterLength = gap_beats
                part.append(rest)

        nota = note.Note()
        nota.pitch.midi = n['pitch']
        # Pasamos el bpm dinámico a la función de cuantización
        nota.quarterLength = cuantizar_duracion(n['offset'] - n['onset'], tempo_bpm=bpm)
        
        velocity = n.get('velocity', 80)
        nota.volume.velocity = max(1, min(127, velocity))
        part.append(nota)
        current_time = n['offset']

    score.append(part)

    xml_path = Path(pdf_path).with_suffix('.musicxml')
    score.write("musicxml", fp=str(xml_path))
    log.info("MusicXML generado: %s (Tempo: %d, Compás: %s)", xml_path, int(round(bpm)), time_signature)

    return render_musicxml_to_pdf(xml_path, pdf_path)