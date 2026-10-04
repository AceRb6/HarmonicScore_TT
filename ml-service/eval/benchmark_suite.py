"""
eval/benchmark_suite.py — Benchmark AMT (Ciclo 1)

Compara la transcripción estimada (MusicXML del pipeline) contra una
referencia (MusicXML/MIDI ground truth) con métricas estándar MIREX.

Métricas:
  * f1_onsets       : F1 de inicios de nota (tolerancia 50 ms)
  * f1_onset_pitch  : F1 onset+pitch (sin offset)
  * f1_full         : F1 onset+pitch+offset (offset_ratio=0.2)
  * pitch_acc       : precisión de altura sobre onsets emparejados

Uso:
  python eval/benchmark_suite.py --ref <gt> --est <estimada> --out <report.json>
"""
import argparse
import json
from pathlib import Path

import mir_eval
import music21
import numpy as np

ONSET_TOL = 0.05            # s, estándar MIREX
UMBRAL_F1_ONSETS = 0.75     # RNF-07
UMBRAL_PITCH = 0.80         # RNF-08


def _tempo_bpm(stream) -> float:
    mm = stream.getElementsByClass(music21.tempo.MetronomeMark)
    if mm:
        try:
            return float(mm[0].getQuarterBPM())
        except Exception:
            pass
    return 120.0


def extract_notes(path: Path):
    """(intervals [n,2] en segundos, pitches MIDI). Excluye notas de adorno
    (quarterLength==0): el vocabulario del modelo (shifts de 10 ms) no puede
    representarlas; se documenta como decisión de protocolo (H-23)."""
    s = music21.converter.parse(str(path))
    spq = 60.0 / _tempo_bpm(s)
    intervals, pitches = [], []
    for el in s.flatten():
        if isinstance(el, music21.note.Note) and el.pitch is not None:
            if el.quarterLength <= 0:      # gracia / adorno
                continue
            o = el.offset * spq
            intervals.append([o, o + el.quarterLength * spq])
            pitches.append(int(el.pitch.midi))
        elif isinstance(el, music21.chord.Chord):
            if el.quarterLength <= 0:
                continue
            o = el.offset * spq
            for p in el.pitches:
                intervals.append([o, o + el.quarterLength * spq])
                pitches.append(int(p.midi))
    return (np.array(intervals, dtype=float), np.array(pitches, dtype=int))


def evaluate(ref_int, ref_p, est_int, est_p) -> dict:
    res = {"n_ref": int(len(ref_int)), "n_est": int(len(est_int))}
    if len(ref_int) == 0 or len(est_int) == 0:
        res.update(f1_onsets=0.0, precision_onsets=0.0, recall_onsets=0.0,
                   f1_onset_pitch=0.0, f1_full=0.0, pitch_acc=0.0)
        return res

    # F1 de onsets (RNF-07)
    p, r, f = mir_eval.transcription.onset_precision_recall_f1(
        ref_int, est_int, onset_tolerance=ONSET_TOL)
    res.update(f1_onsets=float(f), precision_onsets=float(p), recall_onsets=float(r))

    # F1 onset+pitch (sin offset)
    _, _, f2, _ = mir_eval.transcription.precision_recall_f1_overlap(
        ref_int, ref_p, est_int, est_p,
        onset_tolerance=ONSET_TOL, offset_ratio=None)
    res["f1_onset_pitch"] = float(f2)

    # F1 completo (con offset, estándar MIREX)
    _, _, f3, _ = mir_eval.transcription.precision_recall_f1_overlap(
        ref_int, ref_p, est_int, est_p,
        onset_tolerance=ONSET_TOL, offset_ratio=0.2)
    res["f1_full"] = float(f3)

    # Precisión de pitch = (onsets emparejados con pitch correcto) /
    #                      (onsets emparejados sin condición de pitch)
    onset_matches = mir_eval.util.match_events(
        ref_int[:, 0], est_int[:, 0], ONSET_TOL)
    note_matches = mir_eval.transcription.match_notes(
        ref_int, ref_p, est_int, est_p,
        onset_tolerance=ONSET_TOL, offset_ratio=None)   # sin kwarg pitch_compare
    res["pitch_acc"] = (len(note_matches) / len(onset_matches)
                        if len(onset_matches) else 0.0)
    return res


def _cumple(v, umbral):
    return "CUMPLE" if v >= umbral else "NO CUMPLE"


def main():
    ap = argparse.ArgumentParser(description="Benchmark AMT ref vs estimada")
    ap.add_argument("--ref", required=True)
    ap.add_argument("--est", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    ref_int, ref_p = extract_notes(Path(args.ref))
    est_int, est_p = extract_notes(Path(args.est))

    print("=" * 62)
    print(f"Referencia: {Path(args.ref).name}  |  Estimada: {Path(args.est).name}")
    print(f"Notas ref: {len(ref_int)}   |   Notas est: {len(est_int)}")
    print("-" * 62)

    res = evaluate(ref_int, ref_p, est_int, est_p)

    print(f"F1 onsets             : {res['f1_onsets']:.3f}  -> "
          f"{_cumple(res['f1_onsets'], UMBRAL_F1_ONSETS)}")
    print(f"F1 onset+pitch        : {res['f1_onset_pitch']:.3f}")
    print(f"F1 onset+pitch+offset : {res['f1_full']:.3f}")
    print(f"Pitch accuracy        : {res['pitch_acc']:.3f}  -> "
          f"{_cumple(res['pitch_acc'], UMBRAL_PITCH)}")
    print("=" * 62)

    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Reporte guardado en: {out}")


if __name__ == "__main__":
    main()