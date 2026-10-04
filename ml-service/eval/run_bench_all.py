"""Benchmark por lote: una sola carga de modelo; maneja refs faltantes,
mismatch de nombres y piezas >6 min (recorte a 360 s para benchmark)."""
import json, sys
from pathlib import Path

import librosa
import soundfile as sf

ML = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ML))
sys.path.insert(0, str(ML / "eval"))

from pipeline.orchestrator import Orchestrator
from benchmark_suite import extract_notes, evaluate

TESTS, OUTS, REPORTS = ML/"storage"/"tests", ML/"storage"/"outputs", ML/"storage"/"reports"
MAX_S = 360.0


def find_ref(stem: str):
    base = stem.split(".custom_score")[0]                 # H-24
    for name in (stem, base):
        for ext in (".mxl", ".musicxml"):
            p = TESTS / (name + ext)
            if p.exists():
                return p
    return None


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)
    orch = Orchestrator()                                  # modelo UNA sola vez
    rows = []
    for mp3 in sorted(TESTS.glob("*.mp3")):
        stem = mp3.stem
        ref_path = find_ref(stem)
        if ref_path is None:
            print(f"[skip] {stem}: sin MXL de referencia"); rows.append({"pieza": stem, "estado": "skip_sin_ref"}); continue

        dur = librosa.get_duration(path=str(mp3))
        src, trim = mp3, False
        if dur > MAX_S:                                    # H-25: recorte para benchmark
            tmp = REPORTS.parent / f"_trim_{stem}.wav"
            y, sr = librosa.load(str(mp3), sr=None, mono=True, duration=MAX_S - 0.5)
            sf.write(tmp, y, sr)
            src, trim, dur = tmp, True, float(len(y)) / sr

        try:
            orch.run(src, f"{stem}_bench.pdf")
        except Exception as e:
            print(f"[error] {stem}: {e}"); rows.append({"pieza": stem, "estado": "error_pipeline"}); continue

        ref_int, ref_p = extract_notes(ref_path)
        if trim:
            m = ref_int[:, 0] < MAX_S - 0.5
            ref_int, ref_p = ref_int[m], ref_p[m]
        est_int, est_p = extract_notes(OUTS / f"{stem}_bench.musicxml")

        res = evaluate(ref_int, ref_p, est_int, est_p)
        res.update(pieza=stem, estado="ok", trim=trim, dur_s=round(dur, 1),
                   n_ref=int(len(ref_int)), n_est=int(len(est_int)))
        (REPORTS / f"{stem}.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8")
        rows.append(res)
        print(f"{stem}: F1on={res['f1_onsets']:.3f} P={res['precision_onsets']:.3f} "
              f"R={res['recall_onsets']:.3f} pitchAcc={res['pitch_acc']:.3f} "
              f"(ref={len(ref_int)}, est={len(est_int)})")

    print("\n=== RESUMEN HS-Piano (protocolo B) ===")
    for r in rows:
        print(f"{r['pieza']:<55} {r['estado']:<14} "
              f"F1={r.get('f1_onsets', '-')} pitchAcc={r.get('pitch_acc', '-')}")
    (REPORTS / "resumen_batch.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Guardado:", REPORTS / "resumen_batch.json")


if __name__ == "__main__":
    main()