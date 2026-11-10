"""
Etapa 4: Post-procesamiento musical (RF-11).
CICLO 2: Cuantización rítmica adaptativa (§3.7.1, Ec. 21/22),
fusión de notas adyacentes (§3.7.2, Ec. 23) y estimación dinámica de tempo.
"""
import numpy as np
import librosa
import logging

log = logging.getLogger("harmonic.post_stage")

from collections import Counter

# =====================================================================
# DETECCIÓN AUTOMÁTICA DE INSTRUMENTO (Opción B: Heurística por Programa MIDI)
# =====================================================================

# Mapeo de programas MIDI más comunes a nuestras categorías
# Basado en el estándar General MIDI Level 1
PROGRAMAS_MIDI_A_INSTRUMENTO = {
    # Piano (0-7)
    0: 'piano', 1: 'piano', 2: 'piano', 3: 'piano',
    4: 'piano', 5: 'piano', 6: 'piano', 7: 'piano',
    # Guitarra (24-31)
    24: 'guitar', 25: 'guitar', 26: 'guitar', 27: 'guitar',
    28: 'guitar', 29: 'guitar', 30: 'guitar', 31: 'guitar',
    # Bajo (32-39)
    32: 'guitar', 33: 'guitar', 34: 'guitar', 35: 'guitar',  # Bajo se mapea a guitar para rango amplio
    # Violín/Cuerdas frotadas (40-47)
    40: 'violin', 41: 'violin', 42: 'violin', 43: 'violin',
    44: 'violin', 45: 'violin', 46: 'violin', 47: 'violin',
    # Vientos madera (73-80)
    73: 'flute', 74: 'flute', 75: 'flute', 76: 'flute',
    77: 'flute', 78: 'flute', 79: 'flute', 80: 'flute',
    # Vientos metal (56-63)
    56: 'trumpet', 57: 'trumpet', 58: 'trumpet', 59: 'trumpet',
    60: 'trumpet', 61: 'trumpet', 62: 'trumpet', 63: 'trumpet',
    # Voz (52-53 en algunos modelos)
    52: 'voice', 53: 'voice',
}

# =====================================================================
# RANGOS MIDI POR INSTRUMENTO (Para corrección de octavas)
# =====================================================================
RANGOS_INSTRUMENTO = {
    'violin': (55, 100),        # Sol3 (G3) - Mi7 (E7)
    'flute': (58, 97),          # Si3 (B3) - Re7 (D7)
    'piano': (21, 108),         # La0 (A0) - Do8 (C8)
    'guitar': (40, 87),         # Mi2 (E2) - Fa6 (F6)
    'voice': (48, 84),          # Do3 (C3) - Do6 (C6)
    'trumpet': (54, 87),        # Fa#3 (F#3) - Fa6 (F6)
    'clarinet': (50, 94),       # Re3 (D3) - Do7 (C7)
    'cello': (36, 76),          # Do2 (C2) - Do6 (C6)
    'viola': (48, 87),          # Do3 (C3) - Fa6 (F6)
    'default': (21, 108)        # Rango completo de piano
}


def filtrar_notas_fuera_de_rango(notes: list, instrumento: str = 'piano') -> list:
    """
    Corrige errores de octava transponiendo notas fuera de rango.
    Solo elimina si es imposible corregirla matemáticamente.
    
    Args:
        notes: Lista de notas con clave 'pitch' (MIDI)
        instrumento: Nombre del instrumento para validar rango
    
    Returns:
        Lista de notas corregidas dentro del rango válido
    """
    rango_min, rango_max = RANGOS_INSTRUMENTO.get(instrumento.lower(), RANGOS_INSTRUMENTO['default'])
    notas_filtradas = []
    notas_corregidas = 0
    notas_eliminadas = 0
    
    for note in notes:
        pitch = note.get('pitch', 60)
        
        # CASO 1: La nota está en el rango correcto
        if rango_min <= pitch <= rango_max:
            notas_filtradas.append(note)
            
        # CASO 2: Nota muy grave - Intentar subir octavas
        elif pitch < rango_min:
            pitch_original = pitch
            while pitch < rango_min:
                pitch += 12  # Subir una octava
            
            # Verificar si al subir entra en el rango válido
            if pitch <= rango_max:
                note['pitch'] = pitch
                notas_filtradas.append(note)
                notas_corregidas += 1
                log.debug(f"Corregida nota {pitch_original} -> {pitch} (subir octava)")
            else:
                notas_eliminadas += 1
                
        # CASO 3: Nota muy aguda - Intentar bajar octavas
        elif pitch > rango_max:
            pitch_original = pitch
            while pitch > rango_max:
                pitch -= 12  # Bajar una octava
            
            # Verificar si al bajar entra en el rango válido
            if pitch >= rango_min:
                note['pitch'] = pitch
                notas_filtradas.append(note)
                notas_corregidas += 1
                log.debug(f"Corregida nota {pitch_original} -> {pitch} (bajar octava)")
            else:
                notas_eliminadas += 1
    
    if notas_corregidas > 0:
        log.info(f"✅ Se corrigieron {notas_corregidas} errores de octava para {instrumento}")
    if notas_eliminadas > 0:
        log.warning(f"⚠️ Se eliminaron {notas_eliminadas} notas irreparables fuera de rango para {instrumento}")
        
    return notas_filtradas


def detectar_instrumento_por_modelo(notes: list) -> str:
    """
    Detecta el instrumento dominante basándose en los IDs de programa MIDI
    que el modelo YourMT3+ predice en cada nota.
    
    Args:
        notes: Lista de notas con claves 'program', 'instrument' o 'pitch'
    
    Returns:
        Nombre del instrumento detectado ('piano', 'violin', 'flute', etc.)
    """
    # Extraer programas MIDI de las notas (el modelo puede usar 'program' o 'instrument')
    programas = []
    for n in notes:
        prog = n.get('program') or n.get('instrument')
        if prog is not None and isinstance(prog, (int, float)):
            programas.append(int(prog))
    
    if not programas:
        log.info("No se encontraron programas MIDI. Usando rango piano (conservador).")
        return 'piano'
    
    # Encontrar el programa más frecuente
    programa_mas_comun = Counter(programas).most_common(1)[0][0]
    
    # Mapear a nuestra categoría
    instrumento = PROGRAMAS_MIDI_A_INSTRUMENTO.get(programa_mas_comun, 'piano')
    
    log.info(f"Instrumento detectado automáticamente: {instrumento} "
             f"(programa MIDI dominante: {programa_mas_comun}, "
             f"de {len(programas)} notas analizadas)")
    
    return instrumento

def estimate_tempo_from_events(notes: list, min_bpm: float = 40.0, max_bpm: float = 200.0) -> float:
    """Calcula el tempo usando el histograma de Intervalos Inter-Onset (IOI)."""
    valid_notes = [n for n in notes if n.get("confidence", 0) > 0.5]
    if len(valid_notes) < 4:
        return 100.0
        
    onsets = sorted([n["onset"] for n in valid_notes])
    iois = np.diff(onsets)
    iois = iois[iois > 0.1] # Descartar micro-intervalos (< 100ms)
    
    if len(iois) == 0:
        return 100.0
        
    bpms = 60.0 / iois
    valid_bpms = bpms[(bpms >= min_bpm) & (bpms <= max_bpm)]
    
    if len(valid_bpms) == 0:
        return 100.0
        
    estimated_bpm = float(np.median(valid_bpms))

    # Ajuste de octava del tempo (pulso principal entre 60 y 160 BPM)
    PULSE_MIN, PULSE_MAX = 60.0, 160.0
    while estimated_bpm < PULSE_MIN:
        estimated_bpm *= 2.0
        log.info(f"Ajuste de octava: duplicando tempo a {estimated_bpm:.1f} BPM")
    while estimated_bpm > PULSE_MAX:
        estimated_bpm /= 2.0
        log.info(f"Ajuste de octava: dividiendo tempo a {estimated_bpm:.1f} BPM")

    log.info(f"Tempo final estimado: {estimated_bpm:.1f} BPM")
    return estimated_bpm


def quantize_onset_adaptive(t_raw: float, bpm: float, time_signature: str = "4/4") -> float:
    """Aplica la Ecuación 21 y 22: Ajusta el tiempo crudo a la rejilla rítmica."""
    beat_duration = 60.0 / bpm
    D = [2.0, 1.5, 1.0, 0.75, 0.5, 0.375, 0.25, 0.125] 
    
    t_beats = t_raw / beat_duration
    best_beats = t_beats
    min_diff = float('inf')
    
    for d in D:
        units = round(t_beats / d)
        candidate_beats = units * d
        diff = abs(t_beats - candidate_beats)
        if diff < min_diff:
            min_diff = diff
            best_beats = candidate_beats
            
    best_t_grid = best_beats * beat_duration
    epsilon_agogia = 0.15 * beat_duration # 15% de tolerancia
    
    if abs(t_raw - best_t_grid) < epsilon_agogia:
        return t_raw # Preservar expresividad
        
    return best_t_grid


def _get_accent_strength(energies: list, group_size: int) -> float:
    """Calcula la fuerza del acento usando diferencias porcentuales."""
    n_groups = len(energies) // group_size
    if n_groups < 2:
        return 0.0
    
    first_beats = [energies[i*group_size] for i in range(n_groups)]
    other_beats = [energies[i*group_size + j] for i in range(n_groups) for j in range(1, group_size)]
    
    if not other_beats:
        return 0.0
        
    avg_first, avg_other = np.mean(first_beats), np.mean(other_beats)
    if avg_other == 0:
        return 0.0

    return float((avg_first - avg_other) / avg_other)


def estimate_time_signature(notes: list, bpm: float, mag_cqt: np.ndarray, sr: int, hop_length: int) -> str:
    """Estima el compás usando validación cruzada (Energía CQT vs Velocity)."""
    if not notes or bpm <= 0:
        return "4/4"
    
    beat_duration = 60.0 / bpm
    cqt_str_3, cqt_str_4, cqt_confidence = 0.0, 0.0, 0.0
    
    try:
        tempo, beats = librosa.beat.beat_track(sr=sr, onset_envelope=np.sum(mag_cqt, axis=0), 
                                               hop_length=hop_length, start_bpm=bpm, tightness=20, units='frames')
        if len(beats) >= 8:
            cqt_energies = [float(np.sum(mag_cqt[:, int(b)])) for b in beats if int(b) < mag_cqt.shape[1]]
            if len(cqt_energies) >= 8:
                cqt_str_3 = _get_accent_strength(cqt_energies, 3)
                cqt_str_4 = _get_accent_strength(cqt_energies, 4)
                cqt_confidence = abs(cqt_str_3 - cqt_str_4)
    except Exception as e:
        log.warning(f"Error al analizar CQT para compás: {e}")

    beat_energies_vel = {}
    for n in notes:
        beat_idx = round(n['onset'] / beat_duration)
        beat_energies_vel[beat_idx] = beat_energies_vel.get(beat_idx, 0) + n.get('velocity', 80)

    vel_str_3, vel_str_4, vel_confidence = 0.0, 0.0, 0.0
    if len(beat_energies_vel) >= 8:
        sorted_beats = sorted(beat_energies_vel.keys())
        vel_energies = [beat_energies_vel[b] for b in sorted_beats]
        vel_str_3 = _get_accent_strength(vel_energies, 3)
        vel_str_4 = _get_accent_strength(vel_energies, 4)
        vel_confidence = abs(vel_str_3 - vel_str_4)

    MIN_CONFIDENCE = 0.05 
    log.info(f"DEBUG COMPÁS -> CQT(str3={cqt_str_3:.2f}, str4={cqt_str_4:.2f}, conf={cqt_confidence:.2f}) | VEL(str3={vel_str_3:.2f}, str4={vel_str_4:.2f}, conf={vel_confidence:.2f})")
    
    if cqt_confidence > MIN_CONFIDENCE and cqt_confidence >= vel_confidence:
        return "3/4" if cqt_str_3 > cqt_str_4 else "4/4"
    elif vel_confidence > MIN_CONFIDENCE:
        return "3/4" if vel_str_3 > vel_str_4 else "4/4"
    
    return "4/4"


def merge_adjacent_notes(notes: list, threshold_s: float = 0.08) -> list:
    """
    Ecuación 23: Fusión de notas adyacentes.
    REGLA DE ORO: NUNCA fusionar si el pitch cambia, aunque el gap sea de 0.001s.
    """
    if not notes:
        return notes
        
    merged = []
    current = notes[0].copy()
    
    for n in notes[1:]:
        gap = n['onset'] - current['offset']
        
        # Solo fusionamos si es EXACTAMENTE el mismo pitch Y el hueco es menor al umbral
        if n['pitch'] == current['pitch'] and 0 < gap < threshold_s:
            current['offset'] = max(current['offset'], n['offset'])
            # Opcional: Promediar la velocidad si se fusionan
            current['velocity'] = max(current.get('velocity', 80), n.get('velocity', 80))
        else:
            # Si el pitch cambió, o el gap es negativo (solapamiento), cerramos la nota actual
            merged.append(current)
            current = n.copy()
            
    merged.append(current)
    return merged


def suppress_overlap_duplicates(notes: list, overlap_threshold: float = 0.15) -> list:
    """Elimina notas duplicadas en zonas de solapamiento (NMS)."""
    if len(notes) < 2:
        return notes
    
    notes_sorted = sorted(notes, key=lambda x: x.get('onset', 0.0))
    filtered = []
    used = [False] * len(notes_sorted)
    
    for i, note_i in enumerate(notes_sorted):
        if used[i]:
            continue
        
        best_note = note_i
        for j in range(i + 1, len(notes_sorted)):
            if used[j]:
                continue
            
            note_j = notes_sorted[j]
            if note_j.get('onset', 0.0) - note_i.get('onset', 0.0) > overlap_threshold:
                break
            
            same_pitch = abs(note_i.get('pitch', 0) - note_j.get('pitch', 0)) <= 1
            if same_pitch:
                used[j] = True # Descartar la segunda, quedarse con la primera
        
        filtered.append(best_note)
        used[i] = True
    
    return filtered


def correct_octave_errors(notes: list, mag_cqt: np.ndarray, sr: int, hop_length: int) -> list:
    """Fallback global: Corrige errores de octava completa si la energía lo indica."""
    if mag_cqt is None or len(notes) == 0:
        return notes
    
    for note in notes:
        onset_frame = int(note.get('onset', 0.0) * sr / hop_length)
        pitch_midi = note.get('pitch', 60)
        
        f_min = 32.7
        f_fundamental = 440.0 * (2 ** ((pitch_midi - 69) / 12))
        f_octave_up = f_fundamental * 2
        
        bin_fundamental = int(12 * np.log2(f_fundamental / f_min))
        bin_octave_up = int(12 * np.log2(f_octave_up / f_min))
        
        if 0 <= bin_fundamental < mag_cqt.shape[0] and 0 <= bin_octave_up < mag_cqt.shape[0]:
            frame_range = slice(max(0, onset_frame-2), min(mag_cqt.shape[1], onset_frame+3))
            energy_fundamental = np.mean(mag_cqt[bin_fundamental, frame_range])
            energy_octave_up = np.mean(mag_cqt[bin_octave_up, frame_range])
            
            if energy_octave_up > energy_fundamental * 1.5:
                note['pitch'] = pitch_midi - 12
                if 'pitch_name' in note:
                    note['pitch_name'] = librosa.midi_to_note(note['pitch'])
    
    return notes

def suprimir_micro_pausas(notes: list, umbral_s: float = 0.12) -> list:
    """
    Elimina 'micro-pausas' o silencios artificiales menores al umbral (ej. 120ms).
    Extiende el offset de la nota anterior para que coincida con el onset de la siguiente,
    evitando que music21 genere silencios (rests) visualmente molestos en la partitura.
    
    Args:
        notes: Lista de notas ordenadas por onset.
        umbral_s: Umbral en segundos. Huecos menores a este valor se cierran (default: 0.12s = 120ms).
    """
    if len(notes) < 2:
        return notes

    notas_limpias = []
    current = notes[0].copy()

    for i in range(1, len(notes)):
        next_note = notes[i]
        gap = next_note['onset'] - current['offset']

        # Si hay un hueco, pero es menor al umbral (micro-pausa/artefacto)
        if gap > 0 and gap < umbral_s:
            # Forzamos legato: extendemos la nota actual hasta el inicio de la siguiente
            current['offset'] = next_note['onset']
            
            # Nota: No fusionamos las notas si son de pitch diferente, 
            # solo eliminamos el silencio entre ellas.
            
        # Si el gap es real (>= umbral) o negativo (solapamiento), cerramos la nota actual
        notas_limpias.append(current)
        current = next_note.copy()

    # No olvidar agregar la última nota
    notas_limpias.append(current)
    
    return notas_limpias

def refine(notes: list, mag_cqt: np.ndarray = None, sr: int = 44100, 
           hop_length: int = 512, es_percusion: bool = False,
           es_polifonico: bool = False, instrumento: str = 'auto') -> dict:
    """
    Orquesta el post-procesamiento completo. 
    ORDEN CRÍTICO: Filtro drums -> NMS -> Octava CQT -> FILTRO RANGO SEGURO -> Tempo -> Cuantización -> Fusión
    """
    if not notes:
        return {"notes": [], "bpm": 120.0, "time_signature": "4/4"}
    
    # PASO 0: Filtrar baterías/percusión espurias
    if not es_percusion:
        notas_filtradas = [n for n in notes if not n.get('is_drum', False)]
        if len(notas_filtradas) < len(notes):
            log.info(f"Se filtraron {len(notes) - len(notas_filtradas)} notas de batería/percusión erróneas.")
        notes = notas_filtradas

    if not notes:
        return {"notes": [], "bpm": 120.0, "time_signature": "4/4"}

    # PASO 0.5: Detección de instrumento
    if instrumento == 'auto':
        instrumento_detectado = detectar_instrumento_por_modelo(notes)
    else:
        instrumento_detectado = instrumento
    
    # PASO 1: NMS (Eliminar duplicados por solapamiento de ventanas)
    notes = suppress_overlap_duplicates(notes, overlap_threshold=0.15)
    
    # PASO 2: Corrección de octava global basada en energía CQT (Fallback físico)
    if mag_cqt is not None:
        notes = correct_octave_errors(notes, mag_cqt, sr, hop_length)
    
    # PASO 2.5: FILTRO DE RANGO SEGURO (CRÍTICO para monofonía no-piano)
    # Si es monofónico y NO es piano, forzamos un rango de viento/cuerda aguda para eliminar notas graves "fantasma"
    if not es_polifonico and instrumento_detectado != 'piano':
        log.info(f"Modo Monofónico no-piano detectado ({instrumento_detectado}). Aplicando rango seguro de viento (48-96).")
        # Usamos 'flute' como base segura porque cubre la mayoría de vientos y cuerdas agudas (Do3 a Do7)
        notes = filtrar_notas_fuera_de_rango(notes, instrumento='flute')
    else:
        # Si es piano o polifónico, usamos el rango detectado o el default (piano)
        notes = filtrar_notas_fuera_de_rango(notes, instrumento=instrumento_detectado)
    
    # PASO 3: Estimar Tempo y Compás
    bpm = estimate_tempo_from_events(notes)
    time_sig = estimate_time_signature(notes, bpm, mag_cqt, sr, hop_length)
    
    # PASO 4: Cuantizar Onsets y Offsets a la rejilla rítmica (con tolerancia agógica)
    quantized_notes = []
    for n in notes:
        new_note = n.copy()
        new_note['onset'] = quantize_onset_adaptive(n['onset'], bpm, time_sig)
        new_note['offset'] = quantize_onset_adaptive(n['offset'], bpm, time_sig)
        
        # Seguridad: garantizar que el offset sea posterior al onset
        if new_note['offset'] <= new_note['onset']:
            new_note['offset'] = new_note['onset'] + (60.0 / bpm) * 0.5 
            
        quantized_notes.append(new_note)
    
    # PASO 5: Suprimir micro-pausas (Limpia silencios artificiales < 120ms entre notas cuantizadas)
    # Esto evita que music21 dibuje silencios diminutos entre notas que deberían sonar continuas (legato)
    clean_notes = suprimir_micro_pausas(quantized_notes, umbral_s=0.12)
    
    # PASO 6: Fusionar notas adyacentes del MISMO pitch (Ec. 23)
    # REGLA DE ORO: La función merge_adjacent_notes NUNCA fusionará si el pitch cambia.
    final_notes = merge_adjacent_notes(clean_notes, threshold_s=0.08) 
    
    log.info(f"Post-procesamiento completado: {len(final_notes)} notas finales, {bpm:.1f} BPM, {time_sig}")
    
    return {
        "notes": final_notes,
        "bpm": bpm,
        "time_signature": time_sig
    }