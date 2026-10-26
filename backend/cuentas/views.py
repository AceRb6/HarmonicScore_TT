"""
CU-03: Recuperacion de contrasena.

Flujo:
  1. POST /api/auth/recuperar-contrasena/  {email}
     -> si el correo existe: genera token (24 h, un solo uso) y envia correo.
  2. GET  /recuperacion/<token>/  -> formulario para la nueva contrasena.
  3. POST /recuperacion/<token>/  -> valida token y contrasena, guarda con
     set_password(), marca el token como usado y redirige a /login/.
"""
import json
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_http_methods

from .models import TokenRecuperacion, hash_token
from .validators import validar_nueva_contrasena

log = logging.getLogger(__name__)

# Limite anti-abuso: maximo de solicitudes por IP dentro de la ventana
LIMITE_SOLICITUDES = int(getattr(settings, 'RECUPERACION_LIMITE_POR_IP', 5))
VENTANA_SEGUNDOS = int(getattr(settings, 'RECUPERACION_VENTANA_SEGUNDOS', 15 * 60))

MSG_NO_REGISTRADO = 'Correo no registrado en HarmonicScore'


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _ip_cliente(request):
    return request.META.get('REMOTE_ADDR')


def _excede_limite(ip):
    """Cuenta solicitudes por IP en cache (Redis). Si la cache falla, no bloquea."""
    if not ip:
        return False
    limite = int(getattr(settings, 'RECUPERACION_LIMITE_POR_IP', 15))
    ventana = int(getattr(settings, 'RECUPERACION_VENTANA_SEGUNDOS', 15 * 60))
    clave = f'recuperacion:ip:{ip}'
    try:
        if cache.add(clave, 1, timeout=ventana):
            return False
        return cache.incr(clave) > limite
    except Exception as e:  # Redis caido: se registra y se permite la solicitud
        log.warning('Rate limit no disponible (%s)', e)
        return False


def _nombre_usuario(usuario):
    return usuario.first_name.strip() or usuario.username


def _enlace_recuperacion(request, token_plano):
    ruta = f'/recuperacion/{token_plano}/'
    base = getattr(settings, 'SITE_URL', '').rstrip('/')
    return f'{base}{ruta}' if base else request.build_absolute_uri(ruta)


def _enviar_correo(usuario, enlace):
    cuerpo = render_to_string('emails/recuperacion.txt', {
        'nombre_usuario': _nombre_usuario(usuario),
        'enlace_recuperacion': enlace,
    })
    send_mail(
        subject='Recuperación de contraseña en Harmonic Score',
        message=cuerpo,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[usuario.email],
        fail_silently=False,
    )


# ─── API: solicitud de recuperacion ───────────────────────────────────────────

@csrf_exempt
@require_http_methods(['POST'])
def solicitar_recuperacion(request):
    try:
        data = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'json_invalido', 'message': 'Formato JSON inválido.'}, status=400)

    email = (data.get('email') or '').strip()

    if not email:
        return JsonResponse({'error': 'correo_requerido',
                             'message': 'Ingresa tu correo electrónico.'}, status=400)
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({'error': 'correo_invalido',
                             'message': 'El formato del correo electrónico no es válido.'}, status=400)

    ip = _ip_cliente(request)
    if _excede_limite(ip):
        return JsonResponse({'error': 'demasiadas_solicitudes',
                             'message': 'Demasiadas solicitudes. Intenta de nuevo en unos minutos.'},
                            status=429)

    # NOTA: en un despliegue publico conviene responder con un mensaje generico
    # para no revelar si el correo existe (enumeracion de usuarios).
    usuario = User.objects.filter(email__iexact=email, is_active=True).first()
    if not usuario:
        return JsonResponse({'error': 'correo_no_encontrado', 'message': MSG_NO_REGISTRADO}, status=404)

    with transaction.atomic():
        token_obj, token_plano = TokenRecuperacion.objects.crear_para(usuario, ip=ip)
        try:
            _enviar_correo(usuario, _enlace_recuperacion(request, token_plano))
        except Exception as e:
            log.exception('Fallo el envio del correo de recuperacion a %s', usuario.email)
            # Revierte el token: no debe quedar un token activo que nunca llego al usuario
            transaction.set_rollback(True)
            return JsonResponse({'error': 'envio_fallido',
                                 'message': 'No se pudo enviar el correo. Intenta más tarde.',
                                 'detalle': str(e) if settings.DEBUG else None}, status=502)

    return JsonResponse({'success': True, 'email': email,
                         'message': f'Revisa tu bandeja de entrada del correo ({email})'})


# ─── Vista HTML: establecer nueva contrasena ─────────────────────────────────

@never_cache
@csrf_protect
@require_http_methods(['GET', 'POST'])
def recuperacion(request, token=''):
    def responder(contexto, status=200):
        resp = render(request, 'recuperacion.html', contexto, status=status)
        resp['Referrer-Policy'] = 'same-origin'  # evita filtrar el token a sitios externos sin bloquear Origin en CSRF
        return resp

    token_obj = TokenRecuperacion.objects.buscar_valido(token)
    if not token_obj:
        return responder({'token_invalido': True}, status=400 if token else 200)

    usuario = token_obj.usuario
    contexto = {'nombre_usuario': _nombre_usuario(usuario), 'token': token}

    if request.method == 'GET':
        return responder(contexto)

    password = request.POST.get('password', '')
    confirmacion = request.POST.get('password_confirmacion', '')
    errores = validar_nueva_contrasena(password, confirmacion, usuario)
    if errores:
        contexto['errores'] = errores
        return responder(contexto, status=400)

    with transaction.atomic():
        # Bloqueo de fila: evita que dos envios simultaneos usen el mismo token
        token_obj = (TokenRecuperacion.objects.select_for_update()
                     .select_related('usuario').filter(token=hash_token(token)).first())
        if not token_obj or not token_obj.es_valido():
            return responder({'token_invalido': True}, status=400)

        usuario = token_obj.usuario
        usuario.set_password(password)  # se guarda cifrada con el hasher de Django
        usuario.save(update_fields=['password'])
        token_obj.marcar_usado()
        # Invalida cualquier otro token pendiente del mismo usuario
        TokenRecuperacion.objects.filter(usuario=usuario, usado=False).update(
            usado=True, fecha_uso=token_obj.fecha_uso)

    return redirect('/login.html?recuperado=1')
