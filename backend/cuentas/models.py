"""
Modelo de tokens de recuperacion de contrasena (CU-03).

Seguridad:
- El token en claro SOLO viaja en el enlace del correo; en la base de datos
  se guarda su hash SHA-256 (campo `token`). Si alguien lee la tabla, no
  puede reconstruir enlaces validos.
- Cada token caduca a las 24 horas y solo puede usarse una vez.
"""
import hashlib
import secrets
from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

VIGENCIA_TOKEN = timedelta(hours=24)


def hash_token(token_plano: str) -> str:
    """Devuelve el hash SHA-256 (hex) de un token en claro."""
    return hashlib.sha256(token_plano.encode('utf-8')).hexdigest()


class TokenRecuperacionManager(models.Manager):
    def crear_para(self, usuario, ip=None):
        """
        Invalida los tokens pendientes del usuario y genera uno nuevo.
        Devuelve (instancia, token_en_claro). El token en claro no se guarda.
        """
        ahora = timezone.now()
        self.filter(usuario=usuario, usado=False).update(usado=True, fecha_uso=ahora)

        token_plano = secrets.token_urlsafe(32)  # 256 bits de entropia
        instancia = self.create(
            usuario=usuario,
            token=hash_token(token_plano),
            fecha_expiracion=ahora + VIGENCIA_TOKEN,
            ip_solicitud=ip,
        )
        return instancia, token_plano

    def buscar_valido(self, token_plano: str):
        """Devuelve el token si existe, no esta usado ni expirado; si no, None."""
        if not token_plano:
            return None
        t = (self.select_related('usuario')
                 .filter(token=hash_token(token_plano)).first())
        return t if t and t.es_valido() else None


class TokenRecuperacion(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE,
                                related_name='tokens_recuperacion')
    token = models.CharField(max_length=64, unique=True,
                             help_text='Hash SHA-256 del token enviado por correo')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField()
    usado = models.BooleanField(default=False)
    ip_solicitud = models.GenericIPAddressField(null=True, blank=True)
    fecha_uso = models.DateTimeField(null=True, blank=True)

    objects = TokenRecuperacionManager()

    class Meta:
        verbose_name = 'Token de recuperación'
        verbose_name_plural = 'Tokens de recuperación'
        ordering = ['-fecha_creacion']

    def es_valido(self) -> bool:
        return (not self.usado
                and self.fecha_expiracion > timezone.now()
                and self.usuario.is_active)

    def marcar_usado(self):
        self.usado = True
        self.fecha_uso = timezone.now()
        self.save(update_fields=['usado', 'fecha_uso'])

    def __str__(self):
        estado = 'usado' if self.usado else 'pendiente'
        return f'{self.usuario.email} - {estado} - expira {self.fecha_expiracion:%Y-%m-%d %H:%M}'
