"""
Splitter heurístico por registro (octavas) para polifonía homogénea.
Separa audio de un solo instrumento (piano/guitarra) en stems graves y agudos
usando filtrado en el dominio CQT.
"""
import numpy as np
import librosa
import logging

log = logging.getLogger(__name__)


class OctaveSplitter:
    """
    Separa señales polifónicas de un mismo instrumento en stems por rango MIDI.
    Ideal para piano (mano izquierda vs derecha) o guitarra (bajo vs melodía).
    """
    
    def __init__(self, sr=44100, split_midi=60):
        """
        Args:
            sr: Sample rate (44100 Hz estándar)
            split_midi: Punto de división MIDI (60 = Do4, punto medio piano)
        """
        self.sr = sr
        self.split_freq = librosa.midi_to_hz(split_midi)  # 261.63 Hz para MIDI 60
        self.split_midi = split_midi
        log.info(f"OctaveSplitter inicializado: split en MIDI {split_midi} ({self.split_freq:.2f} Hz)")
    
    def split_by_register(self, audio: np.ndarray) -> dict:
        """
        Divide el audio en stems graves y agudos usando máscaras espectrales suaves.
        
        Args:
            audio: Array numpy del audio (mono, float32)
        
        Returns:
            dict con keys 'bass_register', 'treble_register', 'split_freq_hz'
        """
        # 1. Calcular CQT con resolución de 12 bins/octava
        C = np.abs(librosa.cqt(
            audio, sr=self.sr,
            fmin=librosa.note_to_hz('C1'),  # Do1 = 32.7 Hz
            n_bins=84,  # 7 octavas (C1 a C8)
            bins_per_octave=12
        ))
        
        # 2. Identificar bin de corte
        freqs = librosa.cqt_frequencies(
            n_bins=84,
            fmin=librosa.note_to_hz('C1')
        )
        cut_bin = np.argmin(np.abs(freqs - self.split_freq))
        log.info(f"Bin de corte: {cut_bin} (freq={freqs[cut_bin]:.2f} Hz)")
        
        # 3. Crear máscaras espectrales suaves (evitar artefactos de corte duro)
        mask_bass = np.zeros_like(C)
        mask_treble = np.zeros_like(C)
        
        # Transición suave de 1 octava (12 bins) alrededor del punto de corte
        transition = 12
        for i in range(C.shape[0]):
            if i < cut_bin - transition:
                mask_bass[i] = 1.0
                mask_treble[i] = 0.0
            elif i > cut_bin + transition:
                mask_bass[i] = 0.0
                mask_treble[i] = 1.0
            else:
                # Función sigmoide para transición suave
                weight = 1 / (1 + np.exp((i - cut_bin) / 3))
                mask_bass[i] = weight
                mask_treble[i] = 1 - weight
        
        # 4. Aplicar máscaras y reconstruir con iCQT
        C_bass = C * mask_bass
        C_treble = C * mask_treble
        
        stem_bass = librosa.icqt(
            C_bass, sr=self.sr,
            fmin=librosa.note_to_hz('C1'),
            bins_per_octave=12
        )
        stem_treble = librosa.icqt(
            C_treble, sr=self.sr,
            fmin=librosa.note_to_hz('C1'),
            bins_per_octave=12
        )
        
        # 5. Normalizar stems para evitar pérdida de energía
        stem_bass = librosa.util.normalize(stem_bass) if np.max(np.abs(stem_bass)) > 0 else stem_bass
        stem_treble = librosa.util.normalize(stem_treble) if np.max(np.abs(stem_treble)) > 0 else stem_treble
        
        return {
            "bass_register": stem_bass,      # Mano izquierda / bajo
            "treble_register": stem_treble,  # Mano derecha / melodía
            "split_freq_hz": self.split_freq,
            "split_midi": self.split_midi
        }
    
    def estimate_homogeneity(self, audio: np.ndarray) -> float:
        """
        Estima la homogeneidad tímbrica del audio.
        Valores bajos (< 500) sugieren un solo instrumento (piano/guitarra sola).
        Valores altos sugieren mezcla heterogénea.
        """
        spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=self.sr)[0]
        return float(np.std(spectral_centroid))