/* ============================================
   CONFIGURACIÓN GLOBAL
   Constantes y ajustes generales del proyecto
   Proyecto: Harmonic Score
   ============================================ */

const CONFIG = {
    // Tiempos
    DURACION_SIMULACION_TRANSCRIPCION: 60000, // 1 minuto en milisegundos
    INTERVALO_ACTUALIZACION_PROGRESO: 100,    // Actualizar cada 100ms
    
    // Límites
    TAMANO_MAXIMO_ARCHIVO_MB: 50,
    FORMATOS_PERMITIDOS: ['audio/mpeg', 'audio/wav', 'audio/mp3'],
    
    // Selectores DOM Comunes
    SELECTORES: {
        FOOTER_BARRA_PROGRESO: '#footer-barra-progreso',
        FOOTER_BARRA_RELLENO: '#footer-barra-relleno',
        MODAL_PROGRESO: '#modal-progreso',
        MODAL_BARRA_RELLENO: '#modal-barra-relleno'
    },
    
    // Mensajes
    MENSAJES: {
        ERROR_FORMATO: 'Formato no soportado. Solo se aceptan archivos MP3 o WAV',
        ERROR_TAMANO: 'El archivo excede el límite de 50 MB',
        EXITO_CARGA: 'Archivo cargado correctamente'
    }
};

// Exportar para uso en otros módulos
// export default CONFIG;