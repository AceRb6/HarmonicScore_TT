import uuid
from django.db import models
from django.contrib.auth.models import User

class Transcripcion(models.Model):
    ESTADOS = [
        ('PENDIENTE', 'Pendiente'),
        ('PROCESANDO', 'Procesando'),
        ('EXITO', 'Exito'),
        ('ERROR', 'Error'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    titulo_audio = models.CharField(max_length=200)
    ruta_audio_original = models.FileField(upload_to='audios/in/')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    harmonic_score = models.FloatField(null=True, blank=True)
    ruta_archivo_pdf = models.FileField(upload_to='audios/pdf/', null=True, blank=True)
    ruta_archivo_mxl = models.FileField(upload_to='audios/mxl/', null=True, blank=True)
    detalles_error = models.TextField(blank=True, null=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)
    fecha_completado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.titulo_audio} - {self.estado}"
