import json
import requests as http_requests
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# #--nuevo--
RECAPTCHA_SECRET_KEY = '6LedhbksAAAAAHAegKlmuLZgwT-G2VohfM4YV25F'

def verificar_recaptcha(token):
    """
    Verifica el token de reCAPTCHA contra la API de Google.
    Retorna True si el captcha es válido, False si no.
    """
    respuesta = http_requests.post(
        'https://www.google.com/recaptcha/api/siteverify',
        data={
            'secret': RECAPTCHA_SECRET_KEY,
            'response': token
        }
    )
    resultado = respuesta.json()
    return resultado.get('success', False)
# #-----------

@csrf_exempt
@require_http_methods(["POST"])
def registro_usuario(request):
    try:
        data = json.loads(request.body)
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')
        email = data.get('email', '')
        username = data.get('username', '')
        password = data.get('password', '')
        recaptcha_token = data.get('recaptcha_token', '')  # #--nuevo--

        # Validar campos obligatorios
        if not all([email, username, password]):
            return JsonResponse({'error': 'Faltan campos obligatorios'}, status=400)

        # #--nuevo-- Verificar captcha con Google antes de procesar el registro
        if not recaptcha_token or not verificar_recaptcha(recaptcha_token):
            return JsonResponse({'error': 'captcha_invalido'}, status=400)
        # #-----------

        # Validar duplicados
        if User.objects.filter(email__iexact=email).exists():
            return JsonResponse({'error': 'correo_existente'}, status=400)

        if User.objects.filter(username__iexact=username).exists():
            return JsonResponse({'error': 'usuario_existente'}, status=400)

        # Crear Usuario con contraseña cifrada automáticamente
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
        return JsonResponse({'error': 'Formato JSON inválido.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def recuperar_contrasena(request):
    """
    CU-03: Verifica si el correo existe en la base de datos.
    Si existe  -> responde éxito (msn1).
    Si no existe -> responde error (msn2).
    El envío real del correo se implementará cuando el backend lo programe.
    """
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()

        if not email:
            return JsonResponse({'error': 'correo_requerido'}, status=400)

        # Buscar el correo en la base de datos (insensible a mayúsculas)
        existe = User.objects.filter(email__iexact=email).exists()

        if existe:
            # TODO: aquí el backend deberá generar el token de 24h y enviar el correo
            return JsonResponse({
                'success': True,
                'message': 'Se ha enviado la recuperación a tu correo'
            }, status=200)
        else:
            return JsonResponse({'error': 'correo_no_encontrado'}, status=404)

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Formato JSON inválido.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

import time

@csrf_exempt
@require_http_methods(["POST"])
def subir_transcripcion(request):
    """
    CU-04 / CU-05: Subir archivo y transcribir.
    Esta vista valida el archivo subido y simula el tiempo de procesamiento
    mientras se integra la solución real de ML.
    """
    try:
        # 1. Validaciones básicas de recepción
        if 'audio' not in request.FILES:
            return JsonResponse({'error': 'No se recibió ningún archivo de audio'}, status=400)
            
        archivo = request.FILES['audio']
        # Validar tamaño y formato (redundante por seguridad)
        tamanio_mb = archivo.size / (1024 * 1024)
        if tamanio_mb > 50:
            return JsonResponse({'error': 'Tamaño excedido. El archivo no debe superar los 50 MB'}, status=400)
            
        # TODO: Validar MIME type y cabecera binaria real (Pendiente)
        # TODO: Guardar temporalmente con permisos restringidos (Pendiente)
        
        # 2. Scaffolding para Lógica de Transcripción (CU-05)
        # ----------------------------------------------------
        # TODO: Clasificar audio (Monofónico/Polifónico) por entropía espectral.
        # TODO: Generar representación CQT (Librosa).
        # TODO: Ejecutar modelo YourMT3-YPTF-MoE-M (PyTorch).
        # TODO: Aplicar post-procesamiento (Cuantización, Fusión, Armónicos).
        # TODO: Latencia objetivo: <15 ms por segundo de audio (Medir).
        # ----------------------------------------------------
        
        # Simular delay de procesamiento ML temporalmente
        time.sleep(2)
        
        return JsonResponse({
            'success': True,
            'message': 'Transcripción completada'
        }, status=200)

    except Exception as e:
        return JsonResponse({'error': f'Error en el procesamiento: {str(e)}'}, status=500)
