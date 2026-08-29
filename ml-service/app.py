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
    """Simula el renderizado final con Verovio, generando un PDF de prueba"""
    print(f"-> [PIPELINE] Generando PDF final con Verovio...")
    # 2026-08-29: Generar un PDF de prueba usando reportlab
    c = canvas.Canvas(pdf_path)
    c.drawString(100, 750, f"Archivo recibido: {original_filename} -- Harmonic Score")
    c.drawString(100, 730, f"Usuario: {username}")
    c.drawString(100, 710, "Este PDF fue generado por el Orquestador FastAPI.")
    c.drawString(100, 680, "Pipeline ejecutado: CQT -> Clasificacion -> YourMT3+ -> Verovio")
    c.save()


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