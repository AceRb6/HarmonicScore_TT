"""Etapa 5: eventos → MusicXML 4.0 → PDF (RF-12, RF-13)."""
import music21
import verovio

BPM = 120  # tempo fijo Ciclo 1; Ciclo 2: estimación de tempo real


def build_score(notes, pdf_path):
    if not notes:
        raise ValueError("No se detectaron notas en el audio")

    part = music21.stream.Part()
    part.append(music21.tempo.MetronomeMark(number=BPM))
    part.append(music21.meter.TimeSignature("4/4"))

    for n in notes:
        no = music21.note.Note()
        no.pitch.midi = n["pitch"]
        beats = (n["offset"] - n["onset"]) * (BPM / 60.0)
        no.duration.quarterLength = max(0.25, min(4.0, round(beats * 4) / 4))
        part.insert(n["onset"] * (BPM / 60.0), no)        # offset en beats

    score = music21.stream.Score()
    score.insert(0, part)

    xml_path = pdf_path.with_suffix(".musicxml")
    score.write("musicxml", fp=str(xml_path))

    tk = verovio.toolkit()
    tk.loadFile(str(xml_path))
    try:
        tk.renderToPDF(str(pdf_path))
    except TypeError:                     # compatibilidad entre versiones de verovio
        data = tk.renderToPDF()
        pdf_path.write_bytes(data if isinstance(data, bytes) else data.encode())
    return pdf_path