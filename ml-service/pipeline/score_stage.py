"""
Etapa 6 — Generación de partitura MusicXML 4.0 (RF-12) y delegación de RF-13.

Convierte la secuencia refinada de eventos (pitch, onset, offset, velocity)
en MusicXML 4.0 mediante music21, con figuras rítmicas cuantizadas y silencios
de relleno basados en el tempo y compás estimados dinámicamente.

Optimizaciones Ciclo 3:
- Limpieza estricta del título (solo nombre de la pieza)
- Validación de integridad de notas
- Filtrado de silencios microscópicos (< 1/64 de negra)
- Manejo robusto de errores en escritura XML
"""

from __future__ import annotations

import logging
import re
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

# Umbral mínimo para generar un silencio (evita artefactos visuales)
MIN_REST_QUARTER = 0.125  # 1/8 de negra (corchea)


def limpiar_titulo(titulo_raw: str) -> str:
    """
    Limpia el título para que SOLO contenga el nombre de la pieza.
    Elimina:
    - Timestamps (20261107_090529)
    - IDs de job (UUIDs hexadecimales)
    - Sufijos como '_harmonic_score', '_output', etc.
    - Caracteres especiales problemáticos para XML
    """
    if not titulo_raw:
        return "Pieza sin título"
    
    titulo = titulo_raw
    
    # Eliminar timestamps comunes (YYYYMMDD_HHMMSS o YYYY-MM-DD_HH-MM-SS)
    titulo = re.sub(r'\d{8}[_-]\d{6}', '', titulo)
    titulo = re.sub(r'\d{4}[_-]\d{2}[_-]\d{2}[_-]\d{2}[_-]\d{2}[_-]\d{2}', '', titulo)
    
    # Eliminar UUIDs hexadecimales (32 caracteres hex)
    titulo = re.sub(r'[0-9a-f]{32}', '', titulo, flags=re.IGNORECASE)
    
    # Eliminar sufijos conocidos del sistema
    sufijos_sistema = [
        r'_harmonic_score', r'_HarmonicScore', r'_output', r'_processed',
        r'_transcription', r'_score', r'-harmonic', r'_final'
    ]
    for sufijo in sufijos_sistema:
        titulo = re.sub(sufijo, '', titulo, flags=re.IGNORECASE)
    
    # Eliminar guiones bajos y guiones al inicio/final
    titulo = titulo.strip('_- ')
    
    # Reemplazar guiones bajos internos por espacios
    titulo = titulo.replace('_', ' ').replace('-', ' ')
    
    # Capitalizar correctamente (Title Case)
    titulo = titulo.title()
    
    # Eliminar espacios múltiples
    titulo = re.sub(r'\s+', ' ', titulo).strip()
    
    # Validar que no quede vacío
    if not titulo:
        return "Pieza sin título"
    
    return titulo


def cuantizar_duracion(duracion_s: float, tempo_bpm: float = 120.0) -> float:
    """
    Convierte segundos a la figura musical (quarterLength) más cercana según el tempo.
    
    Args:
        duracion_s: Duración en segundos
        tempo_bpm: Tempo en BPM
        
    Returns:
        Duración en quarterLength (fracciones de negra) entre 0.0625 (64th) y 4.0 (whole)
    """
    if duracion_s <= 0:
        return 0.0
    
    duracion_negras = duracion_s * (tempo_bpm / 60.0)
    figuras = sorted(FIGURAS_MUSICALES.keys())
    figura = min(figuras, key=lambda x: abs(x - duracion_negras))
    return max(0.0625, min(4.0, figura))


def validar_notas(notes: list) -> list:
    """
    Valida y filtra notas malformadas antes de generar la partitura.
    Incluye logs de depuración para identificar por qué se descartan.
    """
    notas_validas = []
    descartadas = 0
    
    # DEBUG: Inspeccionar la primera nota para ver su estructura real
    if len(notes) > 0:
        log.info(f"🔍 DEBUG validar_notas: Tipo del primer elemento: {type(notes[0])}")
        log.info(f"🔍 DEBUG validar_notas: Contenido del primer elemento: {notes[0]}")

    for i, n in enumerate(notes):
        # 1. Si es un objeto (dataclass), convertirlo a diccionario
        if not isinstance(n, dict):
            if hasattr(n, '__dict__'):
                n = n.__dict__
            else:
                if descartadas < 3:
                    log.warning(f"Nota {i} descartada: No es diccionario ni objeto válido. Tipo: {type(n)}")
                descartadas += 1
                continue
        
        # 2. Validar campos requeridos
        if 'onset' not in n or 'offset' not in n or 'pitch' not in n:
            if descartadas < 3:
                log.warning(f"Nota {i} descartada: Faltan campos obligatorios. Claves presentes: {list(n.keys())}")
            descartadas += 1
            continue
        
        # 3. Validar que offset > onset (duración positiva)
        if n['offset'] <= n['onset']:
            if descartadas < 3:
                log.warning(f"Nota {i} descartada: Duración <= 0. offset ({n['offset']}) <= onset ({n['onset']})")
            descartadas += 1
            continue
        
        # 4. Validar rango MIDI válido (0-127)
        if not (0 <= n['pitch'] <= 127):
            if descartadas < 3:
                log.warning(f"Nota {i} descartada: pitch fuera de rango (0-127). Valor: {n['pitch']}")
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
    title: str = "Pieza sin título"
) -> Path:
    """
    Genera el MusicXML usando el tempo y compás estimados dinámicamente,
    y delega el PDF al módulo pdf_stage.
    
    Args:
        notes: Lista de diccionarios con {pitch, onset, offset, velocity}
        pdf_path: Ruta de salida del PDF
        bpm: Tempo en BPM (estimado dinámicamente)
        time_signature: Compás (ej. "4/4", "3/4")
        title: Título de la pieza (se limpiará automáticamente)
        
    Returns:
        Ruta del PDF generado
        
    Raises:
        ValueError: Si no hay notas válidas para transcribir
        RuntimeError: Si falla la escritura del MusicXML
    """
    # 1. Validar y limpiar notas
    notas_validas = validar_notas(notes)
    if not notas_validas:
        raise ValueError("No hay notas válidas para generar la partitura")
    
    log.info(f"Generando partitura: {len(notas_validas)} notas | {bpm:.1f} BPM | {time_signature}")
    
    # 2. Limpiar el título (SOLO el nombre de la pieza)
    titulo_limpio = limpiar_titulo(title)
    log.info(f"Título final de la pieza: '{titulo_limpio}'")
    
    # 3. Crear estructura del score
    score = stream.Score()
    
    # Metadatos mínimos (solo información relevante)
    md = metadata.Metadata()
    md.title = titulo_limpio
    md.composer = ""  # Dejamos vacío, se infiere del contexto
    score.metadata = md
    
    # 4. Crear parte (asumimos piano por defecto, pero podría ser parametrizable)
    part = stream.Part()
    part.append(instrument.Piano())
    part.append(tempo.MetronomeMark(number=int(round(bpm))))
    part.append(meter.TimeSignature(time_signature))
    
    # 5. Construir la secuencia musical
    current_time = 0.0
    notas_ordenadas = sorted(notas_validas, key=lambda x: x['onset'])
    
    for n in notas_ordenadas:
        # Insertar silencio de relleno si hay gap
        if n['onset'] > current_time:
            gap_s = n['onset'] - current_time
            gap_beats = cuantizar_duracion(gap_s, tempo_bpm=bpm)
            
            # Solo generar silencio si es significativo (>= 1 corchea)
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
        nota.volume.velocity = max(1, min(127, velocity))
        
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