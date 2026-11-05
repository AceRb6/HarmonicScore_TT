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
    restaurarAvisoModeloPendiente();
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

/* ============================================
   AVISO DE PRECISIÓN DEL MODELO (CU-05)
   Persiste entre carga.html -> consultas.html hasta
   que el usuario presione "X" o se cumplan 15 segundos.
   ============================================ */
const AVISO_MODELO_DURACION_MS = 15000;
const AVISO_MODELO_STORAGE_KEY = 'hs_aviso_modelo_expira';

function mostrarAvisoModelo(duracionRestanteMs) {
    const esNuevo = typeof duracionRestanteMs !== 'number';
    const duracion = esNuevo ? AVISO_MODELO_DURACION_MS : Math.max(0, duracionRestanteMs);
    if (duracion <= 0) {
        sessionStorage.removeItem(AVISO_MODELO_STORAGE_KEY);
        return;
    }

    if (esNuevo) {
        sessionStorage.setItem(AVISO_MODELO_STORAGE_KEY, String(Date.now() + AVISO_MODELO_DURACION_MS));
    }

    const anterior = document.getElementById('aviso-modelo');
    if (anterior) anterior.remove();

    const aviso = document.createElement('div');
    aviso.id = 'aviso-modelo';
    aviso.className = 'aviso-modelo';
    aviso.setAttribute('role', 'dialog');
    aviso.setAttribute('aria-live', 'polite');
    aviso.innerHTML = `
        <button type="button" class="aviso-modelo-cerrar" aria-label="Cerrar aviso">&times;</button>
        <h4 class="aviso-modelo-titulo">Gracias por usar Harmonic Score</h4>
        <p class="aviso-modelo-texto">Recuerda que nuestro modelo de transcripción automática puede presentar
        imprecisiones dependiendo de la dificultad de la pieza, la cantidad de instrumentos o el ruido de fondo
        en la grabación.</p>
        <div class="aviso-modelo-barra"></div>`;
    document.body.appendChild(aviso);

    const fraccionInicial = Math.min(1, Math.max(0, duracion / AVISO_MODELO_DURACION_MS));
    const barra = aviso.querySelector('.aviso-modelo-barra');
    if (barra && typeof barra.animate === 'function') {
        barra.animate(
            [{ transform: `scaleX(${fraccionInicial})` }, { transform: 'scaleX(0)' }],
            { duration: duracion, easing: 'linear', fill: 'forwards' }
        );
    }

    if (esNuevo) {
        requestAnimationFrame(() => requestAnimationFrame(() => aviso.classList.add('visible')));
    } else {
        aviso.classList.add('visible');
    }

    let cerrado = false;
    const cerrar = () => {
        if (cerrado) return;
        cerrado = true;
        clearTimeout(temporizador);
        sessionStorage.removeItem(AVISO_MODELO_STORAGE_KEY);
        aviso.classList.remove('visible');
        setTimeout(() => aviso.remove(), 400);
    };
    const temporizador = setTimeout(cerrar, duracion);
    aviso.querySelector('.aviso-modelo-cerrar').addEventListener('click', cerrar);
}

function restaurarAvisoModeloPendiente() {
    const expira = Number(sessionStorage.getItem(AVISO_MODELO_STORAGE_KEY) || 0);
    if (!expira) return;
    const restante = expira - Date.now();
    if (restante > 250) {
        mostrarAvisoModelo(restante);
    } else {
        sessionStorage.removeItem(AVISO_MODELO_STORAGE_KEY);
    }
}

window.mostrarAvisoModelo = mostrarAvisoModelo;