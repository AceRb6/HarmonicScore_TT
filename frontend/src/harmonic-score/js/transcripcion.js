/* ============================================
   LÓGICA DE TRANSCRIPCIÓN
   Simulación de progreso y barras de estado
   Proyecto: Harmonic Score
   ============================================ */

let intervaloProgreso = null;
let progresoActual = 0;
let transcripcionActiva = false;

document.addEventListener('DOMContentLoaded', function() {
    inicializarTranscripcion();
});

/**
 * Configura los eventos para el botón de transcribir y modales
 */
function inicializarTranscripcion() {
    const btnTranscribir = document.getElementById('btn-transcribir');
    const modalProgreso = document.getElementById('modal-progreso');
    const cerrarModal = document.getElementById('cerrar-modal-progreso');
    const btnMinimizar = document.getElementById('btn-minimizar-progreso');

    if (!btnTranscribir) {
        console.log('Botón transcribir no encontrado');
        return;
    }

    console.log('Inicializando botón de transcripción');

    btnTranscribir.addEventListener('click', function() {
        console.log('Click en transcribir');
        iniciarSimulacionTranscripcion();
    });

    // Cerrar modal
    if (cerrarModal && modalProgreso) {
        cerrarModal.addEventListener('click', function() {
            modalProgreso.classList.remove('activo');
            mostrarBarraProgresoMini();
        });
    }

    // Minimizar
    if (btnMinimizar && modalProgreso) {
        btnMinimizar.addEventListener('click', function() {
            modalProgreso.classList.remove('activo');
            mostrarBarraProgresoMini();
        });
    }

    // Clic fuera del modal
    if (modalProgreso) {
        modalProgreso.addEventListener('click', function(e) {
            if (e.target === modalProgreso) {
                modalProgreso.classList.remove('activo');
                mostrarBarraProgresoMini();
            }
        });
    }
}

/**
 * Muestra la barra de progreso mini en el panel izquierdo
 */
function mostrarBarraProgresoMini() {
    const miniBaraProgreso = document.getElementById('mini-barra-progreso');
    if (miniBaraProgreso) {
        miniBaraProgreso.style.display = 'block';
        console.log('Barra mini mostrada');
    }
}

/**
 * Inicia la simulación de progreso (1 minuto)
 */
function iniciarSimulacionTranscripcion() {
    const modalProgreso = document.getElementById('modal-progreso');
    const modalBarra = document.getElementById('modal-barra-relleno');
    const miniBaraProgreso = document.getElementById('mini-barra-progreso');
    const miniBaraRelleno = document.getElementById('mini-barra-relleno');

    if (!modalProgreso || !modalBarra) {
        console.error('No se encontró el modal de progreso');
        return;
    }

    console.log('Iniciando simulación de transcripción');

    // Resetear
    progresoActual = 0;
    transcripcionActiva = true;
    modalBarra.textContent = '0%';
    modalBarra.style.width = '0%';
    
    if (miniBaraRelleno) {
        miniBaraRelleno.style.width = '0%';
        miniBaraRelleno.textContent = '0%';
    }

    // Mostrar modal
    modalProgreso.classList.add('activo');
    
    // Ocultar barra mini al iniciar
    if (miniBaraProgreso) {
        miniBaraProgreso.style.display = 'none';
    }

    // Calcular incremento por intervalo (60 segundos = 60000 ms)
    const duracionTotal = 60000; // 1 minuto
    const intervalo = 100; // Actualizar cada 100ms
    const incremento = 100 / (duracionTotal / intervalo);

    console.log('Duración:', duracionTotal, 'ms');
    console.log('Incremento por intervalo:', incremento);

    clearInterval(intervaloProgreso);
    
    intervaloProgreso = setInterval(function() {
        progresoActual += incremento;
        
        if (progresoActual >= 100) {
            progresoActual = 100;
            finalizarTranscripcion();
        }

        // Actualizar visualmente en modal
        modalBarra.style.width = progresoActual + '%';
        modalBarra.textContent = Math.round(progresoActual) + '%';
        
        // Actualizar barra mini si existe
        if (miniBaraRelleno) {
            miniBaraRelleno.style.width = progresoActual + '%';
            miniBaraRelleno.textContent = Math.round(progresoActual) + '%';
        }

    }, intervalo);
}

/**
 * Finaliza la simulación y muestra resultados
 */
function finalizarTranscripcion() {
    console.log('Transcripción finalizada');
    clearInterval(intervaloProgreso);
    transcripcionActiva = false;
    
    // Esperar un momento en 100%
    setTimeout(function() {
        const modalProgreso = document.getElementById('modal-progreso');
        if (modalProgreso) {
            modalProgreso.classList.remove('activo');
        }
        
        alert('Transcripción completada. Redirigiendo a consultas...');
        window.location.href = 'consultas.html';
    }, 500);
}