"""
Etapa 4: Post-procesamiento musical (RF-11).
CICLO 2: Cuantización rítmica adaptativa (§3.7.1, Ec. 21/22),
fusión de notas adyacentes (§3.7.2, Ec. 23) y estimación dinámica de tempo.
"""
import numpy as np
import librosa
import logging

log = logging.getLogger("harmonic.post_stage")

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
    """Ecuación 23: Fusión de notas adyacentes del mismo pitch separadas por < umbral."""
    if not notes:
        return notes
        
    merged = []
    current = notes[0].copy()
    
    for n in notes[1:]:
        if n['pitch'] == current['pitch'] and (n['onset'] - current['offset']) < threshold_s:
            current['offset'] = max(current['offset'], n['offset'])
        else:
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

def refine(notes: list, mag_cqt: np.ndarray = None, sr: int = 44100, hop_length: int = 512, es_percusion: bool = False) -> dict:
    """
    Orquesta el post-procesamiento completo. 
    ORDEN CRÍTICO: Filtro -> NMS -> Octava Fallback -> Tempo/Compás -> Cuantización -> Fusión
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

    # PASO 1: NMS (Eliminar duplicados por solapamiento de ventanas)
    notes = suppress_overlap_duplicates(notes, overlap_threshold=0.15)
    
    # PASO 2: Corrección de octava global (Fallback)
    if mag_cqt is not None:
        notes = correct_octave_errors(notes, mag_cqt, sr, hop_length)
    
    # PASO 3: Estimar Tempo y Compás
    bpm = estimate_tempo_from_events(notes)
    time_sig = estimate_time_signature(notes, bpm, mag_cqt, sr, hop_length)
    
    # PASO 4: Cuantizar Onsets y Offsets a la rejilla rítmica (con tolerancia agógica)
    refined_notes = []
    for n in notes:
        new_note = n.copy()
        new_note['onset'] = quantize_onset_adaptive(n['onset'], bpm, time_sig)
        new_note['offset'] = quantize_onset_adaptive(n['offset'], bpm, time_sig)
        
        if new_note['offset'] <= new_note['onset']:
            new_note['offset'] = new_note['onset'] + (60.0 / bpm) * 0.5 
            
        refined_notes.append(new_note)
        
    # 5. Suprimir micro-pausas (NUEVO: Limpia los silencios artificiales < 120ms)
    # Esto evita que music21 dibuje silencios diminutos entre notas que deberían sonar continuas
    notes = suprimir_micro_pausas(notes, umbral_s=0.12)
    
    # 6. Cuantizar Onsets y Offsets a la rejilla rítmica
    refined_notes = []
    for n in notes:
        new_note = n.copy()
        new_note['onset'] = quantize_onset_adaptive(n['onset'], bpm, time_sig)
        new_note['offset'] = quantize_onset_adaptive(n['offset'], bpm, time_sig)
        
        # Seguridad: garantizar que el offset sea posterior al onset
        if new_note['offset'] <= new_note['onset']:
            new_note['offset'] = new_note['onset'] + (60.0 / bpm) * 0.5 
            
        refined_notes.append(new_note)
        
    # 7. Fusionar notas adyacentes del mismo pitch (Ec. 23)
    # (Esto limpia cualquier solapamiento residual después de la cuantización)
    final_notes = merge_adjacent_notes(refined_notes, threshold_s=0.08) 
    
    log.info(f"Post-procesamiento completado: {len(final_notes)} notas finales, {bpm:.1f} BPM, {time_sig}")
    
    return {
        "notes": final_notes,
        "bpm": bpm,
        "time_signature": time_sig
    }