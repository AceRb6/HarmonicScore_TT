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

    // 2026-08-21: Remueve listeners previos por si acaso y asigna el click
    btnTranscribir.onclick = function() {
        console.log('--- ¡BOTÓN TRANSCRIBIR CLICKED! ---');
        iniciarSimulacionTranscripcion();
    };

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

    // 2026-08-21: Llamada al backend — incluye el username del usuario de sesión
    // El backend usa este campo porque el login todavía es simulado (no hay sesión real)
    const formData = new FormData();
    formData.append('audio', archivoActual);
    formData.append('username', Sesion.obtenerUsuario()); // nombre del usuario actual

    try {
        console.log('--- ENVIANDO PETICIÓN AL BACKEND ---', formData.get('username'));
        // 2026-08-29: Cambiamos el endpoint para apuntar directamente a FastAPI (puerto 8001) en lugar de Django
        const respuesta = await DjangoAPI.peticion('http://127.0.0.1:8001/api/transcribir', 'POST', formData);
        console.log('--- RESPUESTA RECIBIDA ---', respuesta);

        if (respuesta.ok) {
            // Completar barra
            progresoActual = 100;
            modalBarra.style.width = '100%';
            modalBarra.textContent = '100%';
            if (miniBaraRelleno) {
                miniBaraRelleno.style.width = '100%';
                miniBaraRelleno.textContent = '100%';
            }

            // 2026-08-29: Guardar la transcripción devuelta por el backend en localStorage
            // para que consultas.html pueda mostrarla en la tabla con su URL de descarga real
            if (respuesta.data && respuesta.data.transcripcion) {
                const historialActual = JSON.parse(localStorage.getItem('hs_mock_historial') || '[]');
                historialActual.unshift(respuesta.data.transcripcion); // agregar al inicio
                localStorage.setItem('hs_mock_historial', JSON.stringify(historialActual));
            }

            finalizarTranscripcion(true); // Éxito
        } else {
            // Error en servidor
            modalProgreso.classList.remove('activo');
            transcripcionActiva = false;
            // 2026-08-29: Mensaje actualizado según requerimientos
            mostrarError(respuesta.data.error || 'Error en el procesamiento');
        }

    } catch (error) {
        modalProgreso.classList.remove('activo');
        transcripcionActiva = false;
        // 2026-08-29: Mensaje actualizado según requerimientos
        mostrarError('Error en el procesamiento. Verifica tu conexión con el servidor');
    }
}

/**
 * 2026-08-21: Finaliza la transcripción, limpia el área de carga y redirige a Transcripciones.
 * Se eliminó el alert() bloqueante y se reemplazó con una espera visual en la barra al 100%.
 */
function finalizarTranscripcion(esExito) {
    if (!esExito) return;
    console.log('Transcripción finalizada — limpiando estado y redirigiendo');
    transcripcionActiva = false;

    // 2026-08-21: Limpiar la variable global del archivo actual para dejar el área limpia
    if (typeof archivoActual !== 'undefined') {
        archivoActual = null;
    }

    // 2026-08-21: Esperar brevemente en 100% para que el usuario vea la barra completa
    // y luego redirigir automáticamente a la pestaña de Transcripciones
    setTimeout(function() {
        const modalProgreso = document.getElementById('modal-progreso');
        if (modalProgreso) {
            modalProgreso.classList.remove('activo');
        }
        // Redirigir a la pestaña Transcripciones donde se verá el PDF generado
        window.location.href = 'consultas.html';
    }, 1000);
}