"""
Script de evaluación de métricas AMT (Automatic Music Transcription)
Compara la salida del pipeline (Ciclo 3) contra el Ground Truth (MIDI/JSON).
"""
import numpy as np

def evaluate_transcription(ground_truth_notes, predicted_notes, onset_tolerance_ms=50):
    """
    Calcula F1-Score de Onsets y Precisión de Pitch.
    ground_truth_notes: Lista de dicts [{'onset': 1.2, 'pitch': 60, 'offset': 1.5}, ...]
    predicted_notes: Lista de dicts con la salida de post_stage.refine()
    """
    tolerance_sec = onset_tolerance_ms / 1000.0
    tp, fp, fn = 0, 0, 0
    pitch_correct = 0
    
    # Marcamos las notas de ground truth que ya fueron "matcheadas"
    matched_gt = [False] * len(ground_truth_notes)
    
    for pred in predicted_notes:
        match_found = False
        for i, gt in enumerate(ground_truth_notes):
            if matched_gt[i]:
                continue
            
            # 1. Evaluar Onset (Ecuación 21/22: la cuantización ayuda a estar dentro del tolerance)
            if abs(pred['onset'] - gt['onset']) <= tolerance_sec:
                match_found = True
                matched_gt[i] = True
                
                # 2. Evaluar Pitch
                if pred['pitch'] == gt['pitch']:
                    pitch_correct += 1
                break
                
        if match_found:
            tp += 1
        else:
            fp += 1 # Nota predicha que no existe en la realidad
            
    fn = sum(not m for m in matched_gt) # Notas reales que el modelo no encontró
    
    # Cálculo de métricas
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1_onset = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    pitch_accuracy = pitch_correct / tp if tp > 0 else 0.0
    
    return {
        "f1_onset": round(f1_onset, 3),
        "pitch_accuracy": round(pitch_accuracy, 3),
        "total_predicted": len(predicted_notes),
        "total_ground_truth": len(ground_truth_notes),
        "notes_fused_by_postprocessing": len(ground_truth_notes) - len(predicted_notes) # Aproximación
    }