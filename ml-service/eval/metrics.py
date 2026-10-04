"""Métricas estándar AMT (MIREX) para el benchmark de Harmonic Score."""
import numpy as np
import librosa
import mir_eval


def _to_arrays(notes):
    intervals = np.array([[float(n["onset"]), float(n["offset"])] for n in notes])
    hz = np.array([librosa.midi_to_hz(int(n["pitch"])) for n in notes])
    return intervals, hz


def evaluate_transcription(ref_notes, est_notes, onset_tolerance=0.05):
    """P/R/F1 (onset+pitch), F1 (onset+offset, MIREX) y pitch accuracy."""
    if not ref_notes or not est_notes:
        return dict(precision=0.0, recall=0.0, f1_onset=0.0, f1_onset_offset=0.0,
                    pitch_accuracy=0.0,
                    n_ref=len(ref_notes or []), n_est=len(est_notes or []))
    ref_int, ref_hz = _to_arrays(ref_notes)
    est_int, est_hz = _to_arrays(est_notes)

    p, r, f1, _ = mir_eval.transcription.precision_recall_f1_overlap(
        ref_int, ref_hz, est_int, est_hz,
        onset_tolerance=onset_tolerance, offset_ratio=None)
    _, _, f1_off, _ = mir_eval.transcription.precision_recall_f1_overlap(
        ref_int, ref_hz, est_int, est_hz,
        onset_tolerance=onset_tolerance, offset_ratio=0.20)

    # Empareja solo por onset (ignora pitch) para aislar precisión de altura
    match = mir_eval.transcription.match_notes(
        ref_int, ref_hz, est_int, est_hz, onset_tolerance=onset_tolerance,
        pitch_compare=lambda a, b: np.ones_like(a, dtype=bool))
    pitch_ok = sum(1 for i, j in match if ref_hz[i] == est_hz[j])

    return dict(precision=float(p), recall=float(r), f1_onset=float(f1),
                f1_onset_offset=float(f1_off),
                pitch_accuracy=pitch_ok / len(ref_hz),
                n_ref=int(len(ref_notes)), n_est=int(len(est_notes)))