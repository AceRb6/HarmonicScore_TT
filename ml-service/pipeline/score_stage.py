"""
Etapa 6 — Generación de partitura MusicXML 4.0 (RF-12) y delegación de RF-13.

Convierte la secuencia refinada de eventos (pitch, onset, offset, velocity)
en MusicXML 4.0 mediante music21, con figuras rítmicas cuantizadas y silencios
de relleno para cerrar cada compás 4/4.

La conversión MusicXML → PDF (RF-13) NO vive aquí: se delega a
pipeline.pdf_stage.render_musicxml_to_pdf (fuente única de verdad del render).
"""
from __future__ import annotations

import logging
from pathlib import Path

from music21 import stream, note, tempo, meter, instrument

from pipeline.pdf_stage import render_musicxml_to_pdf

log = logging.getLogger("harmonic.score_stage")

# Figuras musicales válidas en MusicXML (en fracciones de negra / quarterLength)
FIGURAS_MUSICALES = {
    4.0: 'whole', 3.0: 'dotted half', 2.0: 'half', 1.5: 'dotted quarter',
    1.0: 'quarter', 0.75: 'dotted eighth', 0.5: 'eighth', 0.375: 'dotted 16th',
    0.25: '16th', 0.125: '32nd', 0.0625: '64th',
}


def cuantizar_duracion(duracion_s: float, tempo_bpm: float = 120.0) -> float:
    """Convierte segundos a la figura musical (quarterLength) más cercana."""
    duracion_negras = duracion_s * (tempo_bpm / 60.0)
    figuras = sorted(FIGURAS_MUSICALES.keys())
    figura = min(figuras, key=lambda x: abs(x - duracion_negras))
    return max(0.0625, min(4.0, figura))


def build_score(notes: list, pdf_path: Path) -> Path:
    """Genera el MusicXML y delega el PDF. Devuelve la ruta del PDF final."""
    if not notes:
        raise ValueError("No hay notas para generar la partitura")

    score = stream.Score()
    part = stream.Part()
    part.append(instrument.Piano())
    part.append(tempo.MetronomeMark(number=120))
    part.append(meter.TimeSignature('4/4'))

    current_time = 0.0
    for n in sorted(notes, key=lambda x: x['onset']):
        if n['onset'] > current_time:                      # silencio de relleno
            gap_beats = cuantizar_duracion(n['onset'] - current_time)
            if gap_beats >= 0.0625:
                rest = note.Rest()
                rest.quarterLength = gap_beats
                part.append(rest)

        nota = note.Note()
        nota.pitch.midi = n['pitch']
        nota.quarterLength = cuantizar_duracion(n['offset'] - n['onset'])
        velocity = n.get('velocity', 80)
        nota.volume.velocity = max(1, min(127, velocity))
        part.append(nota)
        current_time = n['offset']

    score.append(part)

    xml_path = Path(pdf_path).with_suffix('.musicxml')
    score.write("musicxml", fp=str(xml_path))
    log.info("MusicXML generado: %s", xml_path)

    return render_musicxml_to_pdf(xml_path, pdf_path)      # RF-13 delegado