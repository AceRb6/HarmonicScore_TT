"""Validacion de fortaleza de contrasena (backend) para la recuperacion (CU-03)."""
import re

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError

SIMBOLOS = r"""[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>/?`~]"""

REGLAS = [
    (lambda p: len(p) >= 8,              'La contraseña debe tener mínimo 8 caracteres.'),
    (lambda p: re.search(r'[A-Z]', p),   'La contraseña debe contener al menos una letra mayúscula.'),
    (lambda p: re.search(r'[a-z]', p),   'La contraseña debe contener al menos una letra minúscula.'),
    (lambda p: re.search(r'\d', p),      'La contraseña debe contener al menos un número.'),
    (lambda p: re.search(SIMBOLOS, p),   'La contraseña debe contener al menos un símbolo especial.'),
]

# Traduccion de los mensajes de los validadores nativos de Django (settings en ingles)
TRADUCCION_DJANGO = {
    'password_too_common': 'La contraseña es demasiado común. Elige una más segura.',
    'password_entirely_numeric': 'La contraseña no puede contener solo números.',
    'password_too_similar': 'La contraseña es demasiado parecida a tus datos personales.',
    'password_too_short': 'La contraseña debe tener mínimo 8 caracteres.',
}


def validar_nueva_contrasena(password: str, confirmacion: str, usuario) -> list:
    """Devuelve la lista de errores (vacia si la contrasena es valida)."""
    errores = [msg for regla, msg in REGLAS if not regla(password or '')]

    if password != confirmacion:
        errores.append('La contraseña y su confirmación no coinciden.')

    # Validadores configurados en AUTH_PASSWORD_VALIDATORS:
    # contrasena comun, solo numerica, similar al usuario y longitud minima.
    try:
        password_validation.validate_password(password or '', user=usuario)
    except ValidationError as e:
        for err in e.error_list:
            msg = TRADUCCION_DJANGO.get(err.code, ' '.join(err.messages))
            if msg not in errores:
                errores.append(msg)

    return errores
