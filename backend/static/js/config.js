/* ============================================
   CONFIGURACIÓN GLOBAL — Harmonic Score
   ============================================ */
const CONFIG = {
    // Servicios
    // La base de la API Django vive en api.js (mismo origen). NO usar para ml-service.
    API_ML: 'http://127.0.0.1:8000',   // ml-service (FastAPI): descarga de artefactos

    // Límites (RF-02, RF-03, CU-04)
    TAMANO_MAXIMO_ARCHIVO_MB: 50,
    DURACION_MAXIMA_S: 360,
    FORMATOS_PERMITIDOS: ['audio/mpeg', 'audio/wav', 'audio/mp3'],

    // Tiempos
    INTERVALO_ACTUALIZACION_PROGRESO: 100,
    // Legacy del mockup; el flujo real no lo usa (se conserva por compatibilidad)
    DURACION_SIMULACION_TRANSCRIPCION: 60000,

    // Selectores DOM comunes
    SELECTORES: {
        FOOTER_BARRA_PROGRESO: '#footer-barra-progreso',
        FOOTER_BARRA_RELLENO: '#footer-barra-relleno',
        MODAL_PROGRESO: '#modal-progreso',
        MODAL_BARRA_RELLENO: '#modal-barra-relleno'
    },

    // Mensajes (definición ÚNICA: RF-02/03 + CU-04 msn2/msn3/msn4)
    MENSAJES: {
        ERROR_FORMATO:  'Formato no soportado. Solo se aceptan archivos MP3 o WAV.',
        ERROR_TAMANO:   'Tamaño excedido. El archivo no debe superar los 50 MB.',
        ERROR_DURACION: 'Duración excedida. El archivo no debe superar los seis minutos.',
        EXITO_CARGA:    'Archivo cargado correctamente'
    }
};