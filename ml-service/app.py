# 2026-08-29: FastAPI como Orquestador Principal del Pipeline
import os
import time
import requests
from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from reportlab.pdfgen import canvas

app = FastAPI(title="Harmonic Score ML Orchestrator")

# 2026-08-29: Habilitar CORS para que el frontend pueda hacer peticiones a este puerto
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En produccion restringir a los dominios del frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2026-08-29: Configuracion de rutas
DJANGO_URL = "http://127.0.0.1:8000/api/transcripciones/registrar-historial/"
MEDIA_ROOT = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backend', 'media', 'pdfs')

# Asegurar que el directorio de PDFs exista
os.makedirs(MEDIA_ROOT, exist_ok=True)


# --- FUNCIONES SIMULADAS DEL PIPELINE ---
# 2026-08-29: Cada funcion representa un paso del pipeline real de transcripcion musical
def pipeline_cqt(audio_path: str):
    """Simula el calculo de la Transformada Q Constante (CQT)"""
    print(f"-> [PIPELINE] Calculando CQT para {audio_path}")
    time.sleep(0.5)

def pipeline_clasificacion(audio_path: str):
    """Simula la clasificacion monofonico/polifonico"""
    print(f"-> [PIPELINE] Clasificando audio...")
    time.sleep(0.5)
    return "Polifonico"

def pipeline_yourmt3(audio_path: str):
    """Simula la inferencia con el modelo YourMT3+"""
    print(f"-> [PIPELINE] Ejecutando modelo YourMT3+...")
    time.sleep(1.0)
    return "notas_transcritas"

def pipeline_verovio(notas, pdf_path: str, username: str, original_filename: str):
    """
    2026-09-01: Genera un PDF de confirmacion que acredita que la comunicacion
    Frontend -> FastAPI -> Django fue exitosa. Mientras el modelo YourMT3+ no este
    integrado, este PDF sirve como prueba de que el sistema funciona correctamente.
    """
    from datetime import datetime
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.units import cm

    doc = SimpleDocTemplate(pdf_path, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()

    titulo_style = ParagraphStyle('titulo', parent=styles['Heading1'],
        fontSize=20, textColor=colors.HexColor('#1A237E'), spaceAfter=6)
    ok_style = ParagraphStyle('ok', parent=styles['Normal'],
        fontSize=14, textColor=colors.HexColor('#2E7D32'), spaceAfter=4)
    campo_style = ParagraphStyle('campo', parent=styles['Normal'],
        fontSize=12, textColor=colors.HexColor('#37474F'), spaceAfter=6)
    nota_style = ParagraphStyle('nota', parent=styles['Normal'],
        fontSize=10, textColor=colors.HexColor('#795548'), spaceAfter=4)

    story.append(Paragraph("Harmonic Score — Comprobante de Recepción", titulo_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1A237E')))
    story.append(Spacer(1, 0.4*cm))

    story.append(Paragraph("✔  SISTEMA OPERATIVO — API Funcionando Correctamente", ok_style))
    story.append(Spacer(1, 0.3*cm))

    now = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
    story.append(Paragraph(f"<b>Archivo recibido:</b> {original_filename}", campo_style))
    story.append(Paragraph(f"<b>Usuario:</b> {username}", campo_style))
    story.append(Paragraph(f"<b>Fecha y hora:</b> {now}", campo_style))
    story.append(Paragraph("<b>Estado:</b> LISTO PARA TRANSCRIPCIÓN", campo_style))
    story.append(Spacer(1, 0.5*cm))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CFD8DC')))
    story.append(Spacer(1, 0.3*cm))

    story.append(Paragraph("<b>Pipeline ejecutado (simulado):</b>", campo_style))
    story.append(Paragraph("  1. Carga de audio", campo_style))
    story.append(Paragraph("  2. Preprocesamiento CQT", campo_style))
    story.append(Paragraph("  3. Clasificación mono/polifónico", campo_style))
    story.append(Paragraph("  4. Inferencia YourMT3+  ← pendiente de integración", campo_style))
    story.append(Paragraph("  5. Post-procesamiento → MusicXML", campo_style))
    story.append(Paragraph("  6. Renderizado PDF con Verovio", campo_style))
    story.append(Spacer(1, 0.5*cm))

    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#CFD8DC')))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "<i>Nota: El modelo de transcripción (YourMT3+) aún no está conectado. "
        "Este PDF confirma que la comunicación Frontend → FastAPI (puerto 8001) → "
        "Django (puerto 8000) es exitosa y el archivo llegó listo para procesarse.</i>",
        nota_style))

    doc.build(story)


@app.get("/")
def root():
    return {"message": "Harmonic Score ML Orchestrator corriendo en el puerto 8001"}


# 2026-08-29: Endpoint principal que recibe el audio del frontend y orquesta todo el flujo
@app.post("/api/transcribir")
async def transcribir(audio: UploadFile = File(...), username: str = Form(...)):
    print(f"\n--- NUEVA TRANSCRIPCION RECIBIDA ---")
    print(f"Usuario: {username}")
    print(f"Archivo: {audio.filename}")

    # Validar que el usuario este presente
    if not username:
        raise HTTPException(status_code=401, detail="Usuario no autorizado o no proporcionado")

    # 2026-08-29: Validacion de Formato (MP3 o WAV unicamente)
    ext = os.path.splitext(audio.filename)[1].lower()
    if ext not in ['.mp3', '.wav']:
        raise HTTPException(status_code=400, detail="Formato no soportado. Solo se aceptan archivos MP3 o WAV.")

    # 2026-08-29: Validacion de Tamano (maximo 50MB)
    content = await audio.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > 50:
        raise HTTPException(status_code=400, detail="Tamaño excedido. El archivo no debe superar los cincuenta megabytes.")

    print("[OK] Validaciones de formato y peso aprobadas.")

    # --- SIMULACION DEL FLUJO INTERNO ---
    temp_audio_path = audio.filename
    
    try:
        pipeline_cqt(temp_audio_path)
        tipo = pipeline_clasificacion(temp_audio_path)
        notas = pipeline_yourmt3(temp_audio_path)

        # 2026-08-29: Generar el PDF en la carpeta compartida con Django
        safe_username = username.replace(' ', '_').replace('/', '')
        pdf_filename = f"{safe_username}_{audio.filename}.pdf"
        pdf_path = os.path.join(MEDIA_ROOT, pdf_filename)
        
        pipeline_verovio(notas, pdf_path, username, audio.filename)
        
        print(f"[OK] PDF Generado en: {pdf_path}")
        
    except Exception as e:
        print(f"[ERROR] Error en el pipeline: {e}")
        raise HTTPException(status_code=500, detail="Error en el procesamiento")

    # --- COMUNICACION CON DJANGO ---
    # 2026-08-29: Avisamos a Django que el archivo esta listo para que lo guarde en BD
    print(f"-> [DJANGO] Registrando en el historial...")
    payload = {
        "username": username,
        "titulo": audio.filename,
        "url_pdf": f"/media/pdfs/{pdf_filename}",
        "estado": "Finalizado"
    }

    try:
        resp = requests.post(DJANGO_URL, json=payload, timeout=5)
        resp_data = resp.json()
        if not resp.ok:
            raise Exception(resp_data.get('error', 'Error desconocido en Django'))
    except Exception as e:
        print(f"[ERROR] Error comunicando con Django: {e}")
        raise HTTPException(status_code=500, detail="Error en el procesamiento al guardar historial")

    print(f"[OK] Registro exitoso en Django.")
    
    # 2026-08-29: Devolver la informacion de la transcripcion para que el frontend la muestre
    return {
        "success": True,
        "transcripcion": resp_data.get('transcripcion')
    }