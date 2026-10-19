import numpy as np
import soundfile as sf
from pathlib import Path

# Configuración idéntica a la que espera el modelo (16 kHz, mono)
sr = 16000
notes_hz = [261.63, 329.63, 392.00, 523.25]  # C4, E4, G4, C5
dur_note = 0.8  # 0.8 segundos de sonido
dur_silence = 0.2  # 0.2 segundos de silencio entre notas

t = np.linspace(0, dur_note, int(sr * dur_note), endpoint=False)
audio = []

for f in notes_hz:
    # Onda senoidal pura
    wave = 0.8 * np.sin(2 * np.pi * f * t)
    
    # Envolvente suave (fade in/out de 20ms) para evitar "clics" 
    # que el modelo podría interpretar como ruido o artefactos
    env = np.ones_like(t)
    fade = int(0.02 * sr)
    env[:fade] = np.linspace(0, 1, fade)
    env[-fade:] = np.linspace(1, 0, fade)
    
    audio.extend(wave * env)
    audio.extend(np.zeros(int(sr * dur_silence)))

y = np.array(audio, dtype=np.float32)

# Guardar en la carpeta de tests
out_path = Path("storage/tests/sintetico_mono.wav")
out_path.parent.mkdir(parents=True, exist_ok=True)
sf.write(out_path, y, sr)

print(f"✅ Audio sintético generado: {out_path}")
print(f"   Duración: {len(y)/sr:.1f} segundos")
print(f"   Notas esperadas (Ground Truth): 4 (C4, E4, G4, C5)")