"""
Router inteligente que decide qué estrategia de separación usar
según el análisis del audio de entrada.
"""
import numpy as np
import librosa
import logging

log = logging.getLogger(__name__)


class SeparationRouter:
    """
    Decide si el audio requiere separación y qué tipo.
    """
    
    def __init__(self, entropy_threshold=0.35, homogeneity_threshold=500):
        """
        Args:
            entropy_threshold: Umbral para clasificación mono/poli (ε = 0.35)
            homogeneity_threshold: Umbral de std de centroide espectral
        """
        self.entropy_threshold = entropy_threshold
        self.homogeneity_threshold = homogeneity_threshold
    
    def analyze(self, audio: np.ndarray, sr=44100) -> dict:
        """
        Analiza el audio y retorna la estrategia recomendada.
        
        Returns:
            dict con 'strategy', 'entropy', 'homogeneity'
        """
        # 1. Calcular entropía espectral
        S = np.abs(librosa.stft(audio))
        energy = np.sum(S, axis=0)
        prob = energy / (np.sum(energy) + 1e-10)
        entropy = -np.sum(prob * np.log2(prob + 1e-10))
        
        # 2. Calcular homogeneidad tímbrica
        spectral_centroid = librosa.feature.spectral_centroid(y=audio, sr=sr)[0]
        homogeneity = float(np.std(spectral_centroid))
        
        # 3. Decidir estrategia
        if entropy < self.entropy_threshold:
            strategy = "none"  # Monofónico, no requiere separación
        elif homogeneity < self.homogeneity_threshold:
            strategy = "octave"  # Polifonía homogénea (piano/guitarra sola)
        else:
            strategy = "htdemucs"  # Mezcla heterogénea (Fase 2)
        
        log.info(f"Análisis: entropy={entropy:.3f}, homogeneity={homogeneity:.1f}, strategy={strategy}")
        
        return {
            "strategy": strategy,
            "entropy": float(entropy),
            "homogeneity": homogeneity
        }