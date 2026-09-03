import io

import librosa
import numpy as np
import torch

SR = 44100
HOP_LENGTH = 512
FMIN = 32.7
N_BINS = 264
BINS_PER_OCTAVE = 12


def audio_to_cqt_tensor(audio_bytes: bytes) -> torch.Tensor:
    """
    Convierte un archivo de audio en un tensor CQT.

    Salida:
        Tensor con forma [1, 1, n_bins, frames]
    """
    audio, _ = librosa.load(
        io.BytesIO(audio_bytes),
        sr=SR,
        mono=True,
    )

    cqt = librosa.cqt(
        y=audio,
        sr=SR,
        hop_length=HOP_LENGTH,
        fmin=FMIN,
        n_bins=N_BINS,
        bins_per_octave=BINS_PER_OCTAVE,
        window="hann",
    )

    magnitude = np.abs(cqt)

    # Conversión a escala logarítmica, más adecuada para modelos de audio
    cqt_db = librosa.amplitude_to_db(
        magnitude,
        ref=np.max,
    )

    tensor = torch.from_numpy(cqt_db.astype(np.float32))

    # [frecuencia, tiempo] -> [batch, canales, frecuencia, tiempo]
    tensor = tensor.unsqueeze(0).unsqueeze(0)

    return tensor