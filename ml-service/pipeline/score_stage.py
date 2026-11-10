"""
Etapa 6 — Generación de partitura MusicXML 4.0 (RF-12) y delegación de RF-13.

Convierte la secuencia refinada de eventos (pitch, onset, offset, velocity)
en MusicXML 4.0 mediante music21, con figuras rítmicas cuantizadas y silencios
de relleno basados en el tempo y compás estimados dinámicamente.

Optimizaciones Ciclo 3:
- Limpieza estricta del título (solo nombre de la pieza)
- Validación de integridad de notas
- Filtrado de silencios microscópicos (< 1/64 de negra)
- Etiquetado semántico de instrumentación (Nombre, Abreviatura, MIDI, Clave)
- Manejo robusto de errores en escritura XML
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from music21 import stream, note, tempo, meter, instrument, metadata, clef

from pipeline.pdf_stage import render_musicxml_to_pdf

log = logging.getLogger("harmonic.score_stage")

# =====================================================================
# MAPEO DE INSTRUMENTOS PARA MUSICXML Y GENERAL MIDI
# =====================================================================
INSTRUMENTO_MAP = {
    'violin': {
        'class': instrument.Violin,
        'midi_program': 40,
        'clef': clef.TrebleClef,
        'name': 'Violín'
    },
    'flute': {
        'class': instrument.Flute,
        'midi_program': 73,
        'clef': clef.TrebleClef,
        'name': 'Flauta'
    },
    'piano': {
        'class': instrument.Piano,
        'midi_program': 0,
        'clef': clef.TrebleClef, # Para monofonía. (Para polifonía avanzada se usaría GrandStaff)
        'name': 'Piano'
    },
    'guitar': {
        'class': instrument.AcousticGuitar,
        'midi_program': 24,
        'clef': clef.TrebleClef, # Clave de Sol octavada (estándar para guitarra)
        'name': 'Guitarra Acústica'
    },
    'voice': {
        'class': instrument.Vocalist,
        'midi_program': 52,
        'clef': clef.TrebleClef,
        'name': 'Voz'
    }
}

# Figuras musicales válidas en MusicXML (en fracciones de negra / quarterLength)
FIGURAS_MUSICALES = {
    4.0: 'whole', 3.0: 'dotted half', 2.0: 'half', 1.5: 'dotted quarter',
    1.0: 'quarter', 0.75: 'dotted eighth', 0.5: 'eighth', 0.375: 'dotted 16th',
    0.25: '16th', 0.125: '32nd', 0.0625: '64th',
}

# Umbral mínimo para generar un silencio (evita artefactos visuales)
MIN_REST_QUARTER = 0.125  # 1/8 de negra (corchea)


def limpiar_titulo(titulo_raw: str) -> str:
    """
    Limpia el título para que SOLO contenga el nombre de la pieza.
    """
    if not titulo_raw:
        return "Pieza sin título"
    
    titulo = titulo_raw
    titulo = re.sub(r'\d{8}[_-]\d{6}', '', titulo)
    titulo = re.sub(r'\d{4}[_-]\d{2}[_-]\d{2}[_-]\d{2}[_-]\d{2}[_-]\d{2}', '', titulo)
    titulo = re.sub(r'[0-9a-f]{32}', '', titulo, flags=re.IGNORECASE)
    
    sufijos_sistema = [
        r'_harmonic_score', r'_HarmonicScore', r'_output', r'_processed',
        r'_transcription', r'_score', r'-harmonic', r'_final'
    ]
    for sufijo in sufijos_sistema:
        titulo = re.sub(sufijo, '', titulo, flags=re.IGNORECASE)
    
    titulo = titulo.strip('_- ')
    titulo = titulo.replace('_', ' ').replace('-', ' ')
    titulo = titulo.title()
    titulo = re.sub(r'\s+', ' ', titulo).strip()
    
    return titulo if titulo else "Pieza sin título"


def cuantizar_duracion(duracion_s: float, tempo_bpm: float = 120.0) -> float:
    """Convierte segundos a la figura musical (quarterLength) más cercana."""
    if duracion_s <= 0:
        return 0.0
    
    duracion_negras = duracion_s * (tempo_bpm / 60.0)
    figuras = sorted(FIGURAS_MUSICALES.keys())
    figura = min(figuras, key=lambda x: abs(x - duracion_negras))
    return max(0.0625, min(4.0, figura))


def validar_notas(notes: list) -> list:
    """Valida y filtra notas malformadas antes de generar la partitura."""
    notas_validas = []
    descartadas = 0
    
    if len(notes) > 0:
        log.debug(f"DEBUG validar_notas: Tipo del primer elemento: {type(notes[0])}")

    for i, n in enumerate(notes):
        if not isinstance(n, dict):
            if hasattr(n, '__dict__'):
                n = n.__dict__
            else:
                if descartadas < 3:
                    log.warning(f"Nota {i} descartada: No es diccionario ni objeto válido.")
                descartadas += 1
                continue
        
        if 'onset' not in n or 'offset' not in n or 'pitch' not in n:
            if descartadas < 3:
                log.warning(f"Nota {i} descartada: Faltan campos obligatorios.")
            descartadas += 1
            continue
        
        if n['offset'] <= n['onset']:
            if descartadas < 3:
                log.warning(f"Nota {i} descartada: Duración <= 0.")
            descartadas += 1
            continue
        
        if not (0 <= n['pitch'] <= 127):
            if descartadas < 3:
                log.warning(f"Nota {i} descartada: pitch fuera de rango (0-127).")
            descartadas += 1
            continue
        
        notas_validas.append(n)
    
    if descartadas > 0:
        log.warning(f"Total notas descartadas por validación: {descartadas} de {len(notes)}")
    
    return notas_validas


def build_score(
    notes: list,
    pdf_path: Path,
    bpm: float = 120.0,
    time_signature: str = "4/4",
    title: str = "Pieza sin título",
    instrumento: str = 'piano'  # <-- NUEVO PARÁMETRO
) -> Path:
    """
    Genera el MusicXML usando el tempo y compás estimados dinámicamente,
    asignando el instrumento y la clave correcta, y delega el PDF.
    """
    # 1. Validar y limpiar notas
    notas_validas = validar_notas(notes)
    if not notas_validas:
        raise ValueError("No hay notas válidas para generar la partitura")
    
    log.info(f"Generando partitura: {len(notas_validas)} notas | {bpm:.1f} BPM | {time_signature}")
    
    # 2. Limpiar el título
    titulo_limpio = limpiar_titulo(title)
    log.info(f"Título final de la pieza: '{titulo_limpio}'")
    
    # 3. Crear estructura del score
    score = stream.Score()
    md = metadata.Metadata()
    md.title = titulo_limpio
    score.metadata = md
    
    # 4. Crear parte con el instrumento y clave correctos
    part = stream.Part()
    
    # Obtener configuración del instrumento (fallback a piano si no se reconoce)
    inst_key = instrumento.lower() if instrumento.lower() in INSTRUMENTO_MAP else 'piano'
    inst_config = INSTRUMENTO_MAP[inst_key]
    
    # Aplicar instrumento y configurar programa MIDI
    inst_obj = inst_config['class']()
    inst_obj.midiProgram = inst_config['midi_program']
    part.append(inst_obj)
    
    # Aplicar la clave musical correcta (ej. GuitarClef para guitarra)
    part.append(inst_config['clef']())
    
    # Aplicar tempo y compás
    part.append(tempo.MetronomeMark(number=int(round(bpm))))
    part.append(meter.TimeSignature(time_signature))
    
    log.info(f"Instrumento asignado a la partitura: {inst_config['name']} (MIDI: {inst_config['midi_program']})")
    
    # 5. Construir la secuencia musical
    current_time = 0.0
    notas_ordenadas = sorted(notas_validas, key=lambda x: x['onset'])
    
    for n in notas_ordenadas:
        # Insertar silencio de relleno si hay gap
        if n['onset'] > current_time:
            gap_s = n['onset'] - current_time
            gap_beats = cuantizar_duracion(gap_s, tempo_bpm=bpm)
            
            if gap_beats >= MIN_REST_QUARTER:
                rest = note.Rest()
                rest.quarterLength = gap_beats
                part.append(rest)
        
        # Crear nota
        nota = note.Note()
        nota.pitch.midi = n['pitch']
        nota.quarterLength = cuantizar_duracion(n['offset'] - n['onset'], tempo_bpm=bpm)
        
        # Asignar velocity (dinámica)
        velocity = n.get('velocity', 80)
        nota.volume.velocity = max(1, min(127, int(velocity)))
        
        part.append(nota)
        current_time = n['offset']
    
    score.append(part)
    
    # 6. Escribir MusicXML
    xml_path = Path(pdf_path).with_suffix('.musicxml')
    try:
        score.write("musicxml", fp=str(xml_path))
        log.info(f"MusicXML generado: {xml_path.name}")
    except Exception as e:
        log.error(f"Error al escribir MusicXML: {e}")
        raise RuntimeError(f"No se pudo generar el archivo MusicXML: {e}") from e
    
    # 7. Delegar renderizado a PDF
    return render_musicxml_to_pdf(xml_path, pdf_path, title=titulo_limpio)