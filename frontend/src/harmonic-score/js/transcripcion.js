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
 * Inicia la carga real del archivo al backend y gestiona progreso. (CU-05)
 */
async function iniciarSimulacionTranscripcion() {
    const modalProgreso = document.getElementById('modal-progreso');
    const modalBarra = document.getElementById('modal-barra-relleno');
    const miniBaraProgreso = document.getElementById('mini-barra-progreso');
    const miniBaraRelleno = document.getElementById('mini-barra-relleno');

    if (!modalProgreso || !modalBarra) {
        console.error('No se encontró el modal de progreso');
        return;
    }

    // El archivoActual viene de wavesurfer-setup.js (variable global compartida)
    if (typeof archivoActual === 'undefined' || !archivoActual) {
        mostrarError('No hay ningún archivo válido seleccionado para transcribir.');
        return;
    }

    console.log('Iniciando subida de archivo para transcripción');

    // Resetear visuales de progreso
    progresoActual = 0;
    transcripcionActiva = true;
    modalBarra.textContent = 'En proceso...';
    modalBarra.style.width = '50%';
    
    if (miniBaraRelleno) {
        miniBaraRelleno.style.width = '50%';
        miniBaraRelleno.textContent = 'En proceso...';
    }

    // Mostrar modal
    modalProgreso.classList.add('activo');
    
    // Ocultar barra mini al iniciar
    if (miniBaraProgreso) {
        miniBaraProgreso.style.display = 'none';
    }

    // Llamada al backend
    const formData = new FormData();
    formData.append('audio', archivoActual);
    
    try {
        const respuesta = await DjangoAPI.peticion('/transcripciones/subir/', 'POST', formData);

        if (respuesta.ok) {
            // Completar barra
            progresoActual = 100;
            modalBarra.style.width = '100%';
            modalBarra.textContent = '100%';
            if (miniBaraRelleno) {
                miniBaraRelleno.style.width = '100%';
                miniBaraRelleno.textContent = '100%';
            }
            finalizarTranscripcion(true); // Éxito
        } else {
            // Error en servidor
            modalProgreso.classList.remove('activo');
            transcripcionActiva = false;
            // msn2
            mostrarError(respuesta.data.error || 'Error en el procesamiento. ' + JSON.stringify(respuesta.data));
        }

    } catch (error) {
        modalProgreso.classList.remove('activo');
        transcripcionActiva = false;
        // msn2
        mostrarError('Error en el procesamiento. Verifica tu conexión con el servidor.');
    }
}

/**
 * Finaliza la transcripción y muestra resultados
 */
function finalizarTranscripcion(esExito) {
    if (!esExito) return;
    console.log('Transcripción finalizada');
    transcripcionActiva = false;
    
    // Esperar un momento en 100%
    setTimeout(function() {
        const modalProgreso = document.getElementById('modal-progreso');
        if (modalProgreso) {
            modalProgreso.classList.remove('activo');
        }
        
        // msn1
        alert('Transcripción completada. Redirigiendo a consultas...');
        window.location.href = 'consultas.html';
    }, 500);
}