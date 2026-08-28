from django.db import models
from django.contrib.auth.models import User

# 2026-08-21: Modelo que representa un registro de transcripción de audio.
# Almacena el usuario propietario, el nombre del archivo original enviado,
# la fecha de creación, el estado del proceso y la ruta del PDF generado.
class Transcripcion(models.Model):
    usuario  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transcripciones')
    titulo   = models.CharField(max_length=255)                       # nombre del archivo de audio original
    fecha    = models.DateTimeField(auto_now_add=True)                # fecha de creación automática
    estado   = models.CharField(max_length=20, default='completado')  # 'completado', 'error', 'proceso'
    ruta_pdf = models.CharField(max_length=500, blank=True, null=True)  # ruta relativa dentro de /media/

    class Meta:
        ordering = ['-fecha']   # 2026-08-21: Mostrar las más recientes primero

    def __str__(self):
        return f"{self.usuario.username} — {self.titulo}"
