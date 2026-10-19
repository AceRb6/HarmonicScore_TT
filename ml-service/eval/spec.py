import librosa
import matplotlib.pyplot as plt

y, sr = librosa.load("ml-service/storage/tests/v1/andersen-24-etudes-op15-no5.mp3", sr=16000, mono=True)
D = librosa.amplitude_to_db(np.abs(librosa.stft(y)), ref=np.max)

plt.figure(figsize=(15, 5))
librosa.display.specshow(D, sr=sr, x_axis='time', y_axis='log')
plt.colorbar(format='%+2.0f dB')
plt.title('Espectrograma - Andersen Op.15 No.5')
plt.tight_layout()
plt.savefig("storage/reports/andersen_spectrogram.png", dpi=120)
print("Espectrograma guardado en storage/reports/andersen_spectrogram.png")