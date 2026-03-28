/* ============================================
   NAVEGACIÓN
   Manejo del menú activo y redirecciones
   Proyecto: Harmonic Score
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
    actualizarMenuActivo();
});

/**
 * Marca el enlace del menú correspondiente a la página actual como activo
 */
function actualizarMenuActivo() {
    const rutaActual = window.location.pathname.split('/').pop() || 'index.html';
    const enlaces = document.querySelectorAll('.header-nav a');
    
    enlaces.forEach(enlace => {
        const href = enlace.getAttribute('href');
        if (href === rutaActual) {
            enlace.classList.add('activo');
        } else {
            enlace.classList.remove('activo');
        }
    });
}