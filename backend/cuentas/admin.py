from django.contrib import admin

from .models import TokenRecuperacion


@admin.register(TokenRecuperacion)
class TokenRecuperacionAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'fecha_creacion', 'fecha_expiracion', 'usado', 'fecha_uso', 'ip_solicitud')
    list_filter = ('usado',)
    search_fields = ('usuario__email', 'usuario__username')
    readonly_fields = ('usuario', 'token', 'fecha_creacion', 'fecha_expiracion',
                       'usado', 'fecha_uso', 'ip_solicitud')
