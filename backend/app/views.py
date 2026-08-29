import json
import os
import time
import requests as http_requests
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings

# 2026-08-21: Importación de reportlab para generación de PDFs de prueba
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

# 2026-08-21: Importación del modelo Transcripcion desde su app Django correcta
from transcripciones.models import Transcripcion

# ─────────────────────────────────────────────────────────────────────────────
# UTILIDAD: reCAPTCHA
# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
# UTILIDAD: Generador de PDF de prueba
# 2026-08-21: Genera un PDF en /media/pdfs/ con el mensaje de confirmación
# de recepción del archivo de audio.
# ─────────────────────────────────────────────────────────────────────────────
def generar_pdf_prueba(nombre_archivo, nombre_usuario):
    """
    Crea un PDF de prueba que confirma la recepción del archivo de audio.
    Retorna la ruta relativa del PDF dentro de MEDIA_ROOT.
    """
    # 2026-08-21: Crear carpeta /media/pdfs/ si no existe
    carpeta_pdfs = os.path.join(settings.MEDIA_ROOT, 'pdfs')
    os.makedirs(carpeta_pdfs, exist_ok=True)

    # 2026-08-21: Nombre único para el PDF basado en usuario y nombre de archivo
    nombre_pdf = f"{nombre_usuario}_{nombre_archivo.replace(' ', '_')}.pdf"
    ruta_completa = os.path.join(carpeta_pdfs, nombre_pdf)

    # 2026-08-21: Generar el PDF con reportlab
    c = canvas.Canvas(ruta_completa, pagesize=letter)
    ancho, alto = letter

    # Encabezado
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(ancho / 2, alto - 80, "Harmonic Score")

    # Línea separadora
    c.setLineWidth(1)
    c.line(60, alto - 100, ancho - 60, alto - 100)

    # Mensaje principal
    c.setFont("Helvetica", 14)
    c.drawCentredString(ancho / 2, alto - 140, "Archivo recibido:")
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(ancho / 2, alto - 170, nombre_archivo)

    # Detalles del usuario
    c.setFont("Helvetica", 12)
    c.drawCentredString(ancho / 2, alto - 220, f"Usuario: {nombre_usuario}")

    # Nota informativa
    c.setFont("Helvetica-Oblique", 11)
    c.setFillColorRGB(0.4, 0.4, 0.4)
    c.drawCentredString(ancho / 2, alto - 270,
        "Este PDF es una confirmación de prueba de conexión frontend–backend.")
    c.drawCentredString(ancho / 2, alto - 290,
        "La transcripción real será procesada por el modelo YourMT3.")

    # Pie de página
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(0.6, 0.6, 0.6)
    c.drawCentredString(ancho / 2, 40, "ESCOM-IPN — Proyecto Terminal 2026 — Harmonic Score")

    c.save()

    # 2026-08-21: Retornar la ruta relativa para almacenar en la BD y construir la URL
    return f"pdfs/{nombre_pdf}"


# ─────────────────────────────────────────────────────────────────────────────
# VISTA: registro_usuario
# ─────────────────────────────────────────────────────────────────────────────
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
        recaptcha_token = data.get('recaptcha_token', '')

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
        return JsonResponse({'error': 'Formato JSON inválido.'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# VISTA: recuperar_contrasena
# ─────────────────────────────────────────────────────────────────────────────
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


# ─────────────────────────────────────────────────────────────────────────────
# VISTA: subir_transcripcion
# 2026-08-21: Recibe el archivo de audio y el nombre de usuario desde el frontend,
# genera un PDF de prueba, guarda el registro en la BD y devuelve la URL del PDF.
# ─────────────────────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["POST"])
def subir_transcripcion(request):
    """
    CU-04 / CU-05: Subir archivo y transcribir.
    Recibe el archivo de audio junto con el username del frontend (sesión simulada).
    Genera un PDF de confirmación y guarda el registro en la BD.
    """
    try:
        # 2026-08-21: Validar que se recibió el archivo de audio
        if 'audio' not in request.FILES:
            return JsonResponse({'error': 'No se recibió ningún archivo de audio'}, status=400)

        archivo = request.FILES['audio']

        # 2026-08-21: Validar tamaño máximo (50 MB)
        tamanio_mb = archivo.size / (1024 * 1024)
        if tamanio_mb > 50:
            return JsonResponse({'error': 'Tamaño excedido. El archivo no debe superar los 50 MB'}, status=400)

        # TODO: Validar MIME type y cabecera binaria real (Pendiente)

        # 2026-08-21: Obtener el username del campo FormData enviado por el frontend
        # Se usa el username de localStorage porque el login todavía es simulado
        username = request.POST.get('username', '').strip()
        if not username:
            return JsonResponse({'error': 'Se requiere el nombre de usuario para registrar la transcripción'}, status=400)

        # 2026-08-21: Buscar usuario. El frontend a veces manda el prefijo del correo 
        # (ej. "prueba" en vez de "Emiliano") debido a la simulación del login.
        try:
            usuario = User.objects.get(username=username)
        except User.DoesNotExist:
            # Intentar buscar por el prefijo del email si el username falló
            usuario = User.objects.filter(email__startswith=f"{username}@").first()
            if not usuario:
                return JsonResponse({
                    'success': False, 
                    'error': f'Usuario "{username}" no encontrado en la base de datos'
                }, status=404)

        # 2026-08-21: Generar el PDF de prueba con el nombre del archivo y el usuario
        nombre_archivo = archivo.name
        ruta_relativa_pdf = generar_pdf_prueba(nombre_archivo, usuario.username)

        # 2026-08-21: Simular tiempo de procesamiento (se reemplazará con el modelo ML real)
        time.sleep(2)

        # 2026-08-21: Guardar el registro de transcripción en la base de datos
        transcripcion = Transcripcion.objects.create(
            usuario=usuario,
            titulo=nombre_archivo,
            estado='completado',
            ruta_pdf=ruta_relativa_pdf
        )

        # 2026-08-21: Construir la URL pública del PDF para que el frontend pueda descargarlo
        url_pdf = request.build_absolute_uri(f"{settings.MEDIA_URL}{ruta_relativa_pdf}")

        return JsonResponse({
            'success': True,
            'message': 'Transcripción completada',
            'transcripcion': {
                'id':      transcripcion.id,
                'titulo':  transcripcion.titulo,
                'fecha':   transcripcion.fecha.strftime('%d/%m/%Y'),
                'estado':  transcripcion.estado,
                'url_pdf': url_pdf,
            }
        }, status=200)

    except Exception as e:
        return JsonResponse({'error': f'Error en el procesamiento: {str(e)}'}, status=500)


# ─────────────────────────────────────────────────────────────────────────────
# VISTA: mis_transcripciones
# 2026-08-21: Devuelve el historial de transcripciones del usuario autenticado.
# El frontend pasa el username como query param porque el login es simulado.
# ─────────────────────────────────────────────────────────────────────────────
@csrf_exempt
@require_http_methods(["GET"])
def mis_transcripciones(request):
    """
    GET /api/transcripciones/mis/?username=Jair
    Retorna la lista de transcripciones del usuario indicado.
    """
    try:
        # 2026-08-21: Obtener el username desde los query params de la URL
        username = request.GET.get('username', '').strip()
        if not username:
            return JsonResponse({'error': 'Se requiere el parámetro username'}, status=400)

        # 2026-08-21: Buscar el usuario en la BD
        # 2026-08-21: Buscar el usuario por username o prefijo de correo
        try:
            usuario = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            usuario = User.objects.filter(email__startswith=f"{username}@").first()
            if not usuario:
                return JsonResponse({'error': f'Usuario "{username}" no encontrado'}, status=404)

        # 2026-08-21: Obtener sus transcripciones ordenadas de más reciente a más antigua
        transcripciones = Transcripcion.objects.filter(usuario=usuario)

        lista = []
        for t in transcripciones:
            # 2026-08-21: Construir URL absoluta del PDF si existe la ruta guardada
            url_pdf = None
            if t.ruta_pdf:
                url_pdf = request.build_absolute_uri(f"{settings.MEDIA_URL}{t.ruta_pdf}")

            lista.append({
                'id':      t.id,
                'titulo':  t.titulo,
                'fecha':   t.fecha.strftime('%d/%m/%Y'),
                'estado':  t.estado,
                'url_pdf': url_pdf,
            })

        return JsonResponse({'success': True, 'transcripciones': lista}, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# 2026-08-29: Nuevo endpoint para registrar la transcripción en Django desde FastAPI
@csrf_exempt
def registrar_historial(request):
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body)
            username = data.get('username')
            titulo = data.get('titulo')
            url_pdf = data.get('url_pdf')
            estado = data.get('estado', 'Finalizado')

            if not username or not titulo:
                return JsonResponse({'error': 'Faltan parámetros'}, status=400)

            # Buscar usuario
            try:
                usuario = User.objects.get(username__iexact=username)
            except User.DoesNotExist:
                usuario = User.objects.filter(email__startswith=f"{username}@").first()
                if not usuario:
                    return JsonResponse({'error': f'Usuario "{username}" no encontrado'}, status=404)
            
            # Quitar prefijo /media/ si viene en url_pdf porque FileField asume la base
            # Ej: "/media/pdfs/Jair_audio.pdf" -> "pdfs/Jair_audio.pdf"
            if url_pdf and url_pdf.startswith('/media/'):
                url_pdf = url_pdf.replace('/media/', '', 1)

            # Crear transcripción
            nueva_transcripcion = Transcripcion.objects.create(
                usuario=usuario,
                titulo=titulo,
                estado=estado,
                archivo_pdf=url_pdf
            )

            return JsonResponse({
                'success': True,
                'transcripcion': {
                    'id': nueva_transcripcion.id,
                    'titulo': nueva_transcripcion.titulo,
                    'fecha': nueva_transcripcion.fecha.strftime('%d/%m/%Y'),
                    'estado': nueva_transcripcion.estado,
                    'url_pdf': nueva_transcripcion.archivo_pdf.url if nueva_transcripcion.archivo_pdf else None,
                }
            }, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Método no permitido'}, status=405)
