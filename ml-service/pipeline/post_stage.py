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
    """
    Implementación de la 'matriz de eventos': Calcula el tempo usando el histograma de IOI.
    """
    # 1. Filtrar notas con confianza razonable para evitar ruido del modelo
    valid_notes = [n for n in notes if n.get("confidence", 0) > 0.5]
    if len(valid_notes) < 4:
        return 100.0  # Fallback por defecto si hay muy pocas notas
        
    # 2. Extraer onsets y ordenarlos
    onsets = sorted([n["onset"] for n in valid_notes])
    
    # 3. Calcular la matriz de intervalos (Inter-Onset Intervals, IOI)
    iois = np.diff(onsets)
    
    # 4. Limpiar frecuencia: descartar intervalos irreales (< 100ms, suelen ser errores o ornamentos)
    iois = iois[iois > 0.1]
    if len(iois) == 0:
        return 100.0
        
    # 5. Convertir intervalos a BPM
    bpms = 60.0 / iois
    valid_bpms = bpms[(bpms >= min_bpm) & (bpms <= max_bpm)]
    
    if len(valid_bpms) == 0:
        return 100.0
        
    # 6. El tempo estimado es la mediana (robusto ante outliers)
    estimated_bpm = float(np.median(valid_bpms))

    # Corrección de octava:El "pulso principal" (negra) suele estar entre 60 y 160 BPM. 
    PULSE_MIN, PULSE_MAX = 60.0, 160.0
    # Si el tiempo detectado es muy lento, probablemente detecta una blanca.
    while estimated_bpm < PULSE_MIN:
        estimated_bpm *= 2.0
        log.info(f"Ajuste de octava: duplicando tempo a {estimated_bpm:.1f} BPM")

    # Si el tiempo detectado es muy rápido, probablemente detecta una corchea.
    while estimated_bpm > PULSE_MAX:
        estimated_bpm /= 2.0
        log.info(f"Ajuste de octava: dividiendo tempo a {estimated_bpm:.1f} BPM")

    log.info(f"Tempo final estimado: {estimated_bpm:.1f} BPM")
    return estimated_bpm

def quantize_onset_adaptive(t_raw: float, bpm: float, time_signature: str = "4/4") -> float:
    """
    Aplica la Ecuación 21 y 22 del reporte. Ajusta el tiempo crudo a la rejilla rítmica.
    """
    beat_duration = 60.0 / bpm  # Duración de una negra en segundos
    
    # Divisiones rítmicas válidas (D) relativas a la negra (Ec. 21)
    D = [2.0, 1.5, 1.0, 0.75, 0.5, 0.375, 0.25, 0.125] 
    
    # Convertir tiempo absoluto a "pulsos" (beats) desde el inicio
    t_beats = t_raw / beat_duration
    
    best_beats = t_beats
    min_diff = float('inf')
    
    # Buscar la división rítmica más cercana
    for d in D:
        units = round(t_beats / d)
        candidate_beats = units * d
        diff = abs(t_beats - candidate_beats)
        if diff < min_diff:
            min_diff = diff
            best_beats = candidate_beats
            
    best_t_grid = best_beats * beat_duration
    
    # Ecuación 22: Umbral de agogía (15% del valor de negra)
    epsilon_agogia = 0.15 * beat_duration
    
    # Si la desviación es menor al 15%, preservamos el tiempo original (expresividad)
    if abs(t_raw - best_t_grid) < epsilon_agogia:
        return t_raw
        
    return best_t_grid

def _get_accent_strength(energies: list, group_size: int) -> float:
    """Función auxiliar para calcular la fuerza del acento usando diferencias procentuales.
    Retorna un valor entre -1.0 y 1.0. Positivo = acento en el primer pulso."""
    n_groups = len(energies) // group_size
    if n_groups < 2:
        return 0.0
    
    first_beats = []
    other_beats = []
    for i in range(n_groups):
        group = energies[i*group_size : (i+1)*group_size]
        first_beats.append(group[0])
        other_beats.extend(group[1:])
    
    if not other_beats:
        return 0.0
        
    avg_first = np.mean(first_beats)
    avg_other = np.mean(other_beats)

    if avg_other == 0:
        return 0.0 # Evitar división por cero

    # Diferencia porcentual normalizad: (Primero - Resto) / Rest
    return float((avg_first - avg_other) / avg_other)

def estimate_time_signature(notes: list, bpm: float, mag_cqt: np.ndarray, sr: int, hop_length: int) -> str:
    """
    Estima el compás usando validación cruzada con normalización porcentual:
    1. Analiza la energía espectral (CQT) - Robusto, fuente primaria.
    2. Analiza la energía (velocity) de las notas en cada pulso - Secundario, fuente de respaldo.
    3. Reliega la que tenga mayor confianza.
    """
    
    if not notes or bpm <= 0:
        return "4/4"
    
    beat_duration = 60.0 / bpm

    # ANÁLISIS 1: Energía Espectral (CQT)
    cqt_str_3, cqt_str_4, cqt_confidence = 0.0, 0.0, 0.0
    try:
        tempo, beats = librosa.beat.beat_track(sr=sr, onset_envelope=np.sum(mag_cqt, axis=0), hop_length=hop_length, start_bpm=bpm, tightness=20, units='frames')
        if len(beats) >= 8:

            # Extraer energía de cada frame detectado
            cqt_energies = []
            for b in beats:
                idx = int(b)
                if idx < mag_cqt.shape[1]:
                    cqt_energies.append(float(np.sum(mag_cqt[:, idx])))

            if len(cqt_energies) >= 8:
                cqt_str_3 = _get_accent_strength(cqt_energies, 3)
                cqt_str_4 = _get_accent_strength(cqt_energies, 4)
                cqt_confidence = abs(cqt_str_3 - cqt_str_4)

    except Exception as e:
        log.warning(f"Error al analizar CQT: {e}")

    # ANÁLISIS 2: Velocity de las notas
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

    # LÓGICA DE DECISIÓN (VALIDACIÓN CRUZADA)
    # Umbral mínimo para considerar que hay un acento real (evita ruido) del 5%
    MIN_CONFIDENCE = 0.05 

    log.info(f"DEBUG COMPÁS -> CQT(str3={cqt_str_3:.2f}, str4={cqt_str_4:.2f}, conf={cqt_confidence:.2f}) | VEL(str3={vel_str_3:.2f}, str4={vel_str_4:.2f}, conf={vel_confidence:.2f})")
    
    # 1. Si la CQT es clara, confiamos en ella
    if cqt_confidence > MIN_CONFIDENCE and cqt_confidence >= vel_confidence:
        log.info(f"Compás por CQT: {'3/4' if cqt_str_3 > cqt_str_4 else '4/4'}")
        return "3/4" if cqt_str_3 > cqt_str_4 else "4/4"
    
    # 2. Si la CQT es ambigua, usamos velocity
    if vel_confidence > MIN_CONFIDENCE:
        log.info(f"Compás por Velocity: {'3/4' if vel_str_3 > vel_str_4 else '4/4'}")
        return "3/4" if vel_str_3 > vel_str_4 else "4/4"
    
    # 3. Fallback seguro
    log.info("Compás ambiguo. Usando fallback 4/4.")
    return "4/4"

def merge_adjacent_notes(notes: list, threshold_s: float = 0.08) -> list:
    """
    Ecuación 23: Fusión de notas adyacentes del mismo pitch separadas por < umbral.
    """
    if not notes:
        return notes
        
    merged = []
    current = notes[0].copy()
    
    for n in notes[1:]:
        # Si es el mismo pitch y el gap es menor al umbral, fusionar
        if n['pitch'] == current['pitch'] and (n['onset'] - current['offset']) < threshold_s:
            current['offset'] = max(current['offset'], n['offset'])
        else:
            merged.append(current)
            current = n.copy()
            
    merged.append(current)
    return merged

def refine(notes: list, mag_cqt: np.ndarray = None, sr: int = 44100, hop_length: int = 512) -> dict:
    """
    Orquesta el post-procesamiento. 
    Retorna un diccionario con las notas refinadas y los metadatos estimados.
    """
    if not notes:
        return {"notes": [], "bpm": 120.0, "time_signature": "4/4"}
        
    # 1. Estimar Tempo dinámicamente
    bpm = estimate_tempo_from_events(notes)
    
    # 2. Estimar Compás usando validación cruzada (CQT + Velocity)
    # Si mag_cqt es None, la función híbrida caerá en 4/4 por defecto
    time_sig = estimate_time_signature(notes, bpm, mag_cqt, sr, hop_length)
    
    # 3. Cuantizar Onsets y Offsets
    refined_notes = []
    for n in notes:
        new_note = n.copy()
        new_note['onset'] = quantize_onset_adaptive(n['onset'], bpm, time_sig)
        new_note['offset'] = quantize_onset_adaptive(n['offset'], bpm, time_sig)
        
        # Seguridad: garantizar que el offset sea posterior al onset
        if new_note['offset'] <= new_note['onset']:
            new_note['offset'] = new_note['onset'] + (60.0 / bpm) * 0.5 
            
        refined_notes.append(new_note)
        
    # 4. Fusionar notas adyacentes del mismo pitch (Ec. 23)
    final_notes = merge_adjacent_notes(refined_notes, threshold_s=0.08) # 80ms umbral genérico
    
    log.info(f"Post-procesamiento completado: {len(final_notes)} notas finales, {bpm:.1f} BPM, {time_sig}")
    
    return {
        "notes": final_notes,
        "bpm": bpm,
        "time_signature": time_sig
    }