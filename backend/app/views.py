import json
import os
import requests as http_requests
from django.http import JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render
from transcripciones.models import Transcripcion

RECAPTCHA_SECRET_KEY = '6LedhbksAAAAAHAegKlmuLZgwT-G2VohfM4YV25F'

# ─── Vistas HTML ─────────────────────────────────────────────────────────────

def home(request):
    return render(request, 'index.html')

def carga(request):
    return render(request, 'carga.html')

def consultas(request):
    return render(request, 'consultas.html')

def login_view(request):
    return render(request, 'login.html')

def registro(request):
    return render(request, 'registro.html')

def recuperar_page(request):
    return render(request, 'recuperar-contrasena.html')

# ─── Helpers ─────────────────────────────────────────────────────────────────

def verificar_recaptcha(token):
    """Verifica el token de reCAPTCHA contra la API de Google."""
    try:
        respuesta = http_requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={'secret': RECAPTCHA_SECRET_KEY, 'response': token}
        )
        return respuesta.json().get('success', False)
    except Exception:
        return False

# ─── API: Autenticacion ───────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def registro_usuario(request):
    """CU-01: Registro de nuevo usuario. Guarda en auth_user de PostgreSQL."""
    try:
        data = json.loads(request.body)
        first_name       = data.get('first_name', '')
        last_name        = data.get('last_name', '')
        email            = data.get('email', '')
        username         = data.get('username', '')
        password         = data.get('password', '')
        recaptcha_token  = data.get('recaptcha_token', '')

        if not all([email, username, password]):
            return JsonResponse({'error': 'Faltan campos obligatorios'}, status=400)

        if not recaptcha_token or not verificar_recaptcha(recaptcha_token):
            return JsonResponse({'error': 'captcha_invalido'}, status=400)

        if User.objects.filter(email__iexact=email).exists():
            return JsonResponse({'error': 'correo_existente'}, status=400)

        if User.objects.filter(username__iexact=username).exists():
            return JsonResponse({'error': 'usuario_existente'}, status=400)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        return JsonResponse({
            'success': True,
            'message': 'Cuenta registrada exitosamente',
            'user_id': user.id
        }, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Formato JSON invalido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def login_usuario(request):
    """CU-02: Autentica al usuario y crea sesion Django."""
    try:
        data     = json.loads(request.body)
        username = data.get('username', '').strip()
        email    = data.get('email', '').strip()
        password = data.get('password', '').strip()

        if not password or (not email and not username):
            return JsonResponse({'error': 'Campos obligatorios vacios', 'message': 'Ingresa tu correo y contraseña.'}, status=400)

        # 1. Búsqueda explícita de existencia en la base de datos
        usuario_db = None
        if email:
            usuario_db = User.objects.filter(email__iexact=email).first()
            if not usuario_db:
                # Intentar también por username si el usuario ingresó su nombre de usuario en el campo
                usuario_db = User.objects.filter(username__iexact=email).first()
        elif username:
            usuario_db = User.objects.filter(username__iexact=username).first()

        # Si NO existe en PostgreSQL, rechazar forzosamente
        if not usuario_db:
            return JsonResponse({
                'error': 'usuario_no_encontrado',
                'message': 'Usuario no existente, registrate porfavor'
            }, status=404)

        # 2. Validar contraseña con Django auth
        user = authenticate(request, username=usuario_db.username, password=password)

        if user is not None:
            if not user.is_active:
                return JsonResponse({
                    'error': 'usuario_inactivo',
                    'message': 'Esta cuenta ha sido desactivada.'
                }, status=403)

            login(request, user)
            return JsonResponse({
                'success': True,
                'user_id': user.id,
                'username': user.username,
                'email': user.email,
                'message': f'Bienvenido, {user.username}'
            })
        else:
            return JsonResponse({
                'error': 'credenciales_invalidas',
                'message': 'Contraseña incorrecta. Verifica tus datos.'
            }, status=401)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON invalido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def logout_usuario(request):
    """Cierra la sesion del usuario actual."""
    logout(request)
    return JsonResponse({'success': True, 'message': 'Sesion cerrada'})


@csrf_exempt
@require_http_methods(["POST"])
def recuperar_contrasena(request):
    """CU-03: Verifica si el correo existe en la base de datos."""
    try:
        data  = json.loads(request.body)
        email = data.get('email', '').strip()

        if not email:
            return JsonResponse({'error': 'correo_requerido'}, status=400)

        existe = User.objects.filter(email__iexact=email).exists()

        if existe:
            return JsonResponse({
                'success': True,
                'message': 'Se ha enviado la recuperacion a tu correo'
            }, status=200)
        else:
            return JsonResponse({'error': 'correo_no_encontrado'}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Formato JSON invalido'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# ─── API: Transcripciones ─────────────────────────────────────────────────────

@csrf_exempt
@require_http_methods(["POST"])
def subir_transcripcion(request):
    """
    CU-04 / CU-05: Recibe el audio, lo guarda en PostgreSQL con estado
    PENDIENTE y lo encola en Celery para procesamiento asincrono.
    Responde inmediatamente con el job_id para polling desde el frontend.
    """
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'no_autenticado'}, status=401)

        if 'audio' not in request.FILES:
            return JsonResponse({'error': 'No se recibio ningun archivo de audio'}, status=400)

        archivo = request.FILES['audio']

        # Validar tamano
        tamanio_mb = archivo.size / (1024 * 1024)
        if tamanio_mb > 50:
            return JsonResponse({'error': 'Tamano excedido. Maximo 50 MB'}, status=400)

        # Validar formato
        formatos_permitidos = ['.mp3', '.wav', '.ogg', '.flac', '.m4a']
        _, extension = os.path.splitext(archivo.name.lower())
        if extension not in formatos_permitidos:
            return JsonResponse({'error': f'Formato no permitido: {extension}'}, status=400)

        # Guardar registro en PostgreSQL
        transcripcion = Transcripcion.objects.create(
            usuario=request.user,
            titulo_audio=archivo.name,
            ruta_audio_original=archivo,
            estado='PENDIENTE',
        )

        # Encolar en Celery: el worker envia el audio al ml-service (otra maquina)
        from transcripciones.tasks import procesar_audio
        try:
            procesar_audio.delay(str(transcripcion.id))
        except Exception as e:
            transcripcion.estado = 'ERROR'
            transcripcion.detalles_error = f'No se pudo encolar la tarea: {e}'
            transcripcion.save(update_fields=['estado', 'detalles_error'])

        return JsonResponse({
            'success': True,
            'message': 'Audio recibido y en cola de procesamiento.',
            'job_id': str(transcripcion.id),
            'estado': transcripcion.estado,
            'titulo': transcripcion.titulo_audio,
        }, status=202)

    except Exception as e:
        return JsonResponse({'error': f'Error al procesar: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def estado_transcripcion(request, job_id):
    """Consulta el estado de un job especifico por su UUID."""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'no_autenticado'}, status=401)

        t = Transcripcion.objects.get(id=job_id, usuario=request.user)

        return JsonResponse({
            'job_id': str(t.id),
            'titulo': t.titulo_audio,
            'estado': t.estado,
            'harmonic_score': t.harmonic_score,
            'pdf_url': t.ruta_archivo_pdf.url if t.ruta_archivo_pdf else None,
            'mxl_url': t.ruta_archivo_mxl.url if t.ruta_archivo_mxl else None,
            'error': t.detalles_error,
            'fecha_subida': t.fecha_subida.isoformat(),
        })

    except Transcripcion.DoesNotExist:
        return JsonResponse({'error': 'job_no_encontrado'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def historial_transcripciones(request):
    """Devuelve todas las transcripciones del usuario autenticado."""
    try:
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'no_autenticado'}, status=401)

        jobs = Transcripcion.objects.filter(
            usuario=request.user
        ).order_by('-fecha_subida')

        data = [{
            'job_id': str(t.id),
            'titulo': t.titulo_audio,
            'estado': t.estado,
            'harmonic_score': t.harmonic_score,
            'pdf_url': t.ruta_archivo_pdf.url if t.ruta_archivo_pdf else None,
            'mxl_url': t.ruta_archivo_mxl.url if t.ruta_archivo_mxl else None,
            'fecha_subida': t.fecha_subida.isoformat(),
            'fecha_completado': t.fecha_completado.isoformat(),
        } for t in jobs]

        return JsonResponse({'transcripciones': data, 'total': len(data)})

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def mis_transcripciones(request):
    """
    Formato que espera transcripciones.js: lista de
    { titulo, fecha, estado: completado|error|proceso, url_descarga }.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'no_autenticado'}, status=401)

    mapa_estado = {
        'PENDIENTE': 'proceso',
        'PROCESANDO': 'proceso',
        'EXITO': 'completado',
        'ERROR': 'error',
    }
    jobs = Transcripcion.objects.filter(usuario=request.user).order_by('-fecha_subida')
    data = [{
        'job_id': str(t.id),
        'titulo': t.titulo_audio,
        'fecha': t.fecha_subida.isoformat(),
        'estado': mapa_estado.get(t.estado, 'proceso'),
        'harmonic_score': t.harmonic_score,
        'url_descarga': t.ruta_archivo_pdf.url if t.ruta_archivo_pdf else None,
    } for t in jobs]
    return JsonResponse(data, safe=False)