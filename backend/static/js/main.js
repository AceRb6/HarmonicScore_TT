/* ============================================
   PUNTO DE ENTRADA PRINCIPAL
   Inicialización general de la aplicación
   Proyecto: Harmonic Score
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
    console.log('Harmonic Score - Mockup Inicializado');
    console.log('Versión: 1.1 (Prototipo Visual)');
    console.log('Equipo: Arroyo Parra, Cano Portugal, Garcés Valencia');
    console.log('ESCOM-IPN 2026-B115');
    
    // Inicializaciones globales adicionales
    inicializarAnimaciones();
});

/**
 * Inicializa animaciones globales
 */
function inicializarAnimaciones() {
    // Agregar clase de animación a elementos al hacer scroll
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animado');
            }
        });
    }, { threshold: 0.1 });

    // Observar elementos con clase 'animar'
    document.querySelectorAll('.animar').forEach(el => {
        observer.observe(el);
    });
}

/**
 * Función utilitaria para formatear bytes a MB
 */
function formatearTamañoBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Función utilitaria para formatear duración
 */
function formatearDuracion(segundos) {
    const mins = Math.floor(segundos / 60);
    const secs = Math.floor(segundos % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Exportar funciones utilitarias
window.formatearTamañoBytes = formatearTamañoBytes;
window.formatearDuracion = formatearDuracion;