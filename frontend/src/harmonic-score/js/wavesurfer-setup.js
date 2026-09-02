/* ============================================
   CONFIGURACIÓN WAVESURFER.JS v7
   Visualizador de audio principal + Mini-onda para recortador
   Proyecto: Harmonic Score
   2026-09-01
   ============================================ */

let wavesurfer = null;
let wsRegions  = null;
let regionActiva = null;
let trimmerWavesurfer = null;
let archivoCargado = false;
let archivoActual  = null;
let duracionTotal  = 0;

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM cargado - Inicializando visualizadores de audio...');
    inicializarWavesurfer();
    inicializarTrimmerWaveform();
    inicializarCargaArchivo();
});

/**
 * 2026-09-01: Inicializa WaveSurfer principal sobre fondo blanco
 */
function inicializarWavesurfer() {
    const contenedorWaveform = document.getElementById('waveform');
    if (!contenedorWaveform) return;

    try {
        wavesurfer = WaveSurfer.create({
            container:     '#waveform',
            waveColor:     '#94A3B8',
            progressColor: '#0284C7',
            cursorColor:   '#DC2626',
            barWidth:      2,
            barRadius:     3,
            cursorWidth:   2,
            height:        380,        // Espectrograma alto y amplio
            barGap:        3,
            normalize:     true,
            interact:      true,
        });

        if (WaveSurfer.TimelinePlugin) {
            wavesurfer.registerPlugin(
                WaveSurfer.TimelinePlugin.create({ container: '#waveform-timeline' })
            );
        }

        wavesurfer.on('ready', function() {
            archivoCargado = true;
            duracionTotal  = wavesurfer.getDuration();

            const placeholder = document.getElementById('waveform-placeholder');
            if (placeholder) placeholder.style.display = 'none';

            const badge = document.getElementById('badge-estado-audio');
            if (badge) {
                badge.textContent = 'Audio listo';
                badge.style.background = '#DCFCE7';
                badge.style.color = '#15803D';
            }

            actualizarInfoDuracion(duracionTotal);

            // 2026-09-01: Inicializar el recortador en el rango completo por defecto
            if (window.inicializarRangoRecortador) {
                window.inicializarRangoRecortador(duracionTotal);
            }
        });

    } catch (error) {
        console.error('Error al crear Wavesurfer principal:', error);
    }
}

/**
 * 2026-09-01: Inicializa la segunda instancia de WaveSurfer para el recortador
 * (con interact: false para no cambiar selección al hacer clic en la onda)
 */
function inicializarTrimmerWaveform() {
    const contenedorTrimmer = document.getElementById('trimmer-waveform');
    if (!contenedorTrimmer) return;

    try {
        trimmerWavesurfer = WaveSurfer.create({
            container:     '#trimmer-waveform',
            waveColor:     '#64748B',  // Gris oscuro para el audio base
            progressColor: '#64748B',
            height:        85,
            barWidth:      2,
            barRadius:     2,
            barGap:        2,
            normalize:     true,
            interact:      false,      // No interactivo por clic directo
        });
    } catch (error) {
        console.error('Error al crear trimmer Wavesurfer:', error);
    }
}

/**
 * Formatea segundos a mm:ss
 */
function formatearTiempo(seg) {
    const m = Math.floor(seg / 60);
    const s = Math.floor(seg % 60);
    return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}

/**
 * Maneja la carga de archivos
 */
function inicializarCargaArchivo() {
    const dropZone    = document.getElementById('drop-zone');
    const fileInput   = document.getElementById('file-input');
    const btnExaminar = document.getElementById('btn-examinar');

    if (!dropZone || !fileInput || !btnExaminar) return;

    function cancelarInvitado(e) {
        if (!Sesion.estaActiva()) {
            if (e) { e.preventDefault(); e.stopPropagation(); }
            window.location.href = 'login.html';
            return true;
        }
        return false;
    }

    btnExaminar.addEventListener('click', function(e) {
        if (cancelarInvitado(e)) return;
        e.preventDefault();
        e.stopPropagation();
        fileInput.click();
    });

    dropZone.addEventListener('click', function(e) {
        if (e.target !== btnExaminar && !btnExaminar.contains(e.target)) {
            if (cancelarInvitado(e)) return;
            fileInput.click();
        }
    });

    fileInput.addEventListener('change', function(e) {
        if (cancelarInvitado(e)) return;
        const archivo = e.target.files[0];
        if (archivo) validarYProcesarArchivo(archivo);
    });

    dropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        dropZone.style.borderColor = '#0284C7';
        dropZone.style.backgroundColor = '#F0F9FF';
    });

    dropZone.addEventListener('dragleave', function() {
        dropZone.style.borderColor = '#94A3B8';
        dropZone.style.backgroundColor = '#F8FAFC';
    });

    dropZone.addEventListener('drop', function(e) {
        if (cancelarInvitado(e)) return;
        e.preventDefault();
        dropZone.style.borderColor = '#94A3B8';
        dropZone.style.backgroundColor = '#F8FAFC';
        const archivo = e.dataTransfer.files[0];
        if (archivo) validarYProcesarArchivo(archivo);
    });
}

/**
 * Valida y procesa el archivo
 */
function validarYProcesarArchivo(archivo) {
    const extension = archivo.name.split('.').pop().toLowerCase();
    const formatosValidos = ['mp3', 'wav'];

    if (!formatosValidos.includes(extension)) {
        mostrarError('Formato no soportado. Solo se aceptan archivos MP3 o WAV.');
        return;
    }

    const tamañoMB = archivo.size / (1024 * 1024);
    if (tamañoMB > 50) {
        mostrarError('Tamaño excedido. El archivo no debe superar los cincuenta megabytes.');
        return;
    }

    archivoActual = archivo;
    window.archivoActual = archivo;
    habilitarBotonTranscribir();
    procesarArchivo(archivo, tamañoMB);
}

/**
 * Muestra modal de error
 */
function mostrarError(mensaje) {
    const modalError     = document.getElementById('modal-error');
    const mensajeError   = document.getElementById('mensaje-error');
    const cerrarModalErr = document.getElementById('cerrar-modal-error');
    const btnCerrarErr   = document.getElementById('btn-cerrar-error');

    if (!modalError || !mensajeError) {
        alert('Error: ' + mensaje);
        return;
    }

    mensajeError.textContent = mensaje;
    modalError.classList.add('activo');

    const cerrar = () => modalError.classList.remove('activo');
    if (cerrarModalErr) cerrarModalErr.onclick = cerrar;
    if (btnCerrarErr)   btnCerrarErr.onclick   = cerrar;
    modalError.addEventListener('click', e => { if (e.target === modalError) cerrar(); }, { once: true });
}

/**
 * Procesa el archivo y carga en ambos visualizadores
 */
function procesarArchivo(archivo, tamañoMB) {
    mostrarInfoArchivo(archivo, tamañoMB);
    actualizarInterfazCargaExitosa(archivo);

    const url = URL.createObjectURL(archivo);
    if (wavesurfer) wavesurfer.load(url);
    if (trimmerWavesurfer) trimmerWavesurfer.load(url);
}

/**
 * Actualiza la zona de drop
 */
function actualizarInterfazCargaExitosa(archivo) {
    const dropTexto1  = document.getElementById('drop-texto-1');
    const dropTexto3  = document.getElementById('drop-texto-3');
    const btnExaminar = document.getElementById('btn-examinar');
    const dropZone    = document.getElementById('drop-zone');

    if (dropTexto1) {
        dropTexto1.textContent = archivo.name;
        dropTexto1.style.color = '#0284C7';
    }
    if (dropTexto3) {
        dropTexto3.textContent = 'Archivo cargado con éxito';
        dropTexto3.style.color = '#15803D';
        dropTexto3.style.fontWeight = '600';
    }
    if (btnExaminar) {
        btnExaminar.textContent = 'Seleccionar otro archivo';
    }
    if (dropZone) {
        dropZone.style.borderColor = '#15803D';
        dropZone.style.backgroundColor = '#F0FDF4';
    }
}

/**
 * Muestra info de archivo
 */
function mostrarInfoArchivo(archivo, tamañoMB) {
    const archivoInfo   = document.getElementById('archivo-info');
    const detallesVacio = document.getElementById('detalles-vacio');

    if (archivoInfo)   archivoInfo.style.display = 'block';
    if (detallesVacio) detallesVacio.style.display = 'none';

    const infoNombre        = document.getElementById('info-nombre');
    const infoPeso          = document.getElementById('info-peso');
    const infoFormato       = document.getElementById('info-formato');
    const infoClasificacion = document.getElementById('info-clasificacion');

    if (infoNombre)  infoNombre.textContent  = archivo.name;
    if (infoPeso)    infoPeso.textContent    = tamañoMB.toFixed(2) + ' MB';
    if (infoFormato) infoFormato.textContent = archivo.name.split('.').pop().toUpperCase();
    if (infoClasificacion) {
        infoClasificacion.textContent = 'Detectando...';
        setTimeout(() => { infoClasificacion.textContent = 'Polifónico (Piano)'; }, 1500);
    }
}

/**
 * Actualiza la duración en la información
 */
function actualizarInfoDuracion(duracion) {
    const infoDuracion = document.getElementById('info-duracion');
    if (!infoDuracion || !duracion) return;
    infoDuracion.textContent = formatearTiempo(duracion);
}

/**
 * Habilita el botón de transcribir
 */
function habilitarBotonTranscribir() {
    const btn = document.getElementById('btn-transcribir');
    if (btn) {
        btn.disabled = false;
        btn.classList.remove('btn-deshabilitado');
    }
}

// Getters públicos
window.obtenerDuracionTotal = function() { return duracionTotal; };
window.obtenerWavesurfer    = function() { return wavesurfer; };
window.obtenerTrimmerWave   = function() { return trimmerWavesurfer; };
window.obtenerArchivoActual = function() { return archivoActual || window.archivoActual; };