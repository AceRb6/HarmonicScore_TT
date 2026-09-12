import json
import requests as http_requests
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

# #--nuevo--
RECAPTCHA_SECRET_KEY = '6LedhbksAAAAAHAegKlmuLZgwT-G2VohfM4YV25F'
from django.shortcuts import render

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
    Django actúa como orquestador: recibe el audio del frontend,
    lo reenvía al ml-service (FastAPI), espera el resultado y lo devuelve al frontend.
    """
    try:
        # 1. Validaciones básicas de recepción
        if 'audio' not in request.FILES:
            return JsonResponse({'error': 'No se recibió ningún archivo de audio'}, status=400)
            
        archivo = request.FILES['audio']
        
        # Validar tamaño y formato
        tamanio_mb = archivo.size / (1024 * 1024)
        if tamanio_mb > 50:
            return JsonResponse({'error': 'Tamaño excedido. El archivo no debe superar los 50 MB'}, status=400)
        
        # 2. Reenviar al ml-service (FastAPI en puerto 8000)
        ml_service_url = 'http://127.0.0.1:8000/api/transcribe'
        
        # Preparar el archivo para enviar al ml-service
        files = {'audio': (archivo.name, archivo.read(), archivo.content_type)}
        
        # Llamar al ml-service
        respuesta_ml = http_requests.post(ml_service_url, files=files)
        
        if respuesta_ml.status_code != 202:
            return JsonResponse({
                'error': f'Error en el servicio de ML: {respuesta_ml.text}'
            }, status=500)
        
        # El ml-service devuelve un job_id
        resultado = respuesta_ml.json()
        job_id = resultado.get('job_id')
        
        # 3. Polling: esperar a que el job complete
        import time
        max_intentos = 120  # 2 minutos máximo
        intentos = 0
        
        while intentos < max_intentos:
            time.sleep(1)
            intentos += 1
            
            status_url = f'http://127.0.0.1:8000/api/transcribe/{job_id}'
            status_response = http_requests.get(status_url)
            
            if status_response.status_code != 200:
                continue
                
            status_data = status_response.json()
            
            if status_data.get('status') == 'completed':
                # Transcripción completada
                return JsonResponse({
                    'success': True,
                    'message': 'Transcripción completada',
                    'pdf_url': status_data.get('pdf_url'),
                    'metrics': status_data.get('metrics', {})
                }, status=200)
            
            elif status_data.get('status') == 'failed':
                return JsonResponse({
                    'error': f'Error en el procesamiento: {status_data.get("detail", "Error desconocido")}'
                }, status=500)
        
        # Timeout
        return JsonResponse({
            'error': 'Tiempo de procesamiento excedido'
        }, status=508)

    except Exception as e:
        return JsonResponse({'error': f'Error en el procesamiento: {str(e)}'}, status=500)