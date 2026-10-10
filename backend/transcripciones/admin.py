from django.contrib import admin
from .models import Transcripcion


@admin.register(Transcripcion)
class TranscripcionAdmin(admin.ModelAdmin):
    list_display = ('titulo_audio', 'usuario', 'estado', 'harmonic_score', 'fecha_subida')
    list_filter = ('estado', 'fecha_subida')
    search_fields = ('titulo_audio', 'usuario__username', 'usuario__email')
    readonly_fields = ('id', 'fecha_subida', 'fecha_completado')
