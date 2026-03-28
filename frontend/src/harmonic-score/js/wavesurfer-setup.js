/* ============================================
   CONFIGURACIÓN WAVESURFER.JS
   Inicialización del visualizador de audio
   Proyecto: Harmonic Score
   ============================================ */

let wavesurfer = null;
let archivoCargado = false;
let archivoActual = null;

// Esperar a que el DOM esté completamente cargado
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM cargado - Inicializando Wavesurfer...');
    inicializarWavesurfer();
    inicializarCargaArchivo();
});

/**
 * Inicializa la instancia de Wavesurfer
 */
function inicializarWavesurfer() {
    const contenedorWaveform = document.getElementById('waveform');
    if (!contenedorWaveform) {
        console.error('No se encontró el contenedor del waveform');
        return;
    }

    try {
        wavesurfer = WaveSurfer.create({
            container: '#waveform',
            waveColor: '#FF9100',
            progressColor: '#1A237E',
            cursorColor: '#E53935',
            barWidth: 2,
            barRadius: 3,
            cursorWidth: 1,
            height: 120,
            barGap: 3,
            normalize: true,
            interact: true,
            plugins: [
                WaveSurfer.regions.create({
                    regions: [
                        {
                            start: 0,
                            end: 10,
                            loop: false,
                            color: 'rgba(255, 145, 0, 0.3)'
                        }
                    ]
                }),
                WaveSurfer.timeline.create({
                    container: '#waveform-timeline'
                })
            ]
        });

        console.log('Wavesurfer creado exitosamente');

        wavesurfer.on('ready', function() {
            console.log('Wavesurfer listo');
            archivoCargado = true;
            habilitarBotonTranscribir();
            if (archivoActual) {
                actualizarInfoDuracion(wavesurfer.getDuration());
            }
        });

        wavesurfer.on('play', function() {
            const btnPlay = document.getElementById('btn-play');
            if (btnPlay) btnPlay.textContent = 'Pausar';
        });

        wavesurfer.on('pause', function() {
            const btnPlay = document.getElementById('btn-play');
            if (btnPlay) btnPlay.textContent = 'Reproducir Selección';
        });

    } catch (error) {
        console.error('Error al crear Wavesurfer:', error);
    }
}

/**
 * Maneja la carga de archivos desde el input
 */
function inicializarCargaArchivo() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const btnExaminar = document.getElementById('btn-examinar');

    console.log('Buscando elementos del DOM...');
    console.log('- dropZone:', dropZone);
    console.log('- fileInput:', fileInput);
    console.log('- btnExaminar:', btnExaminar);

    if (!dropZone || !fileInput || !btnExaminar) {
        console.error('No se encontraron todos los elementos del DOM para carga de archivos');
        return;
    }

    // Click en botón "Cargar Archivo" - ABRE EXPLORADOR
    btnExaminar.addEventListener('click', function(e) {
        console.log('Click en botón Cargar Archivo');
        e.preventDefault();
        e.stopPropagation();
        fileInput.click();
    });

    // Click en el área completa - ABRE EXPLORADOR
    dropZone.addEventListener('click', function(e) {
        // Solo abrir si no es el botón
        if (e.target !== btnExaminar && !btnExaminar.contains(e.target)) {
            console.log('Click en drop zone');
            fileInput.click();
        }
    });

    // Cambio en input file
    fileInput.addEventListener('change', function(e) {
        console.log('Cambio en input file');
        const archivo = e.target.files[0];
        if (archivo) {
            console.log('Archivo seleccionado:', archivo.name);
            console.log('Tamaño:', archivo.size, 'bytes');
            console.log('Tipo:', archivo.type);
            validarYProcesarArchivo(archivo);
        } else {
            console.log('No se seleccionó ningún archivo');
        }
    });

    // Drag and Drop
    dropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        dropZone.style.borderColor = '#F57C00';
        dropZone.style.backgroundColor = '#FFF3E0';
    });

    dropZone.addEventListener('dragleave', function() {
        dropZone.style.borderColor = '#FF9100';
        dropZone.style.backgroundColor = '#F5F5F5';
    });

    dropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        dropZone.style.borderColor = '#FF9100';
        dropZone.style.backgroundColor = '#F5F5F5';
        const archivo = e.dataTransfer.files[0];
        if (archivo) {
            console.log('Archivo arrastrado:', archivo.name);
            validarYProcesarArchivo(archivo);
        }
    });

    console.log('Event listeners de carga de archivo configurados');
}

/**
 * Valida y procesa el archivo
 */
function validarYProcesarArchivo(archivo) {
    console.log('Validando archivo:', archivo);
    
    // Validar formato
    const extension = archivo.name.split('.').pop().toLowerCase();
    const formatosValidos = ['mp3', 'wav'];
    
    console.log('Extensión:', extension);
    console.log('Formatos válidos:', formatosValidos);
    
    if (!formatosValidos.includes(extension)) {
        console.log('Formato no válido');
        mostrarError('Formato no soportado. Solo se aceptan archivos MP3 o WAV');
        return;
    }

    // Validar tamaño (50 MB)
    const tamañoMB = archivo.size / (1024 * 1024);
    console.log('Tamaño del archivo:', tamañoMB, 'MB');
    
    if (tamañoMB > 50) {
        console.log('Archivo muy grande');
        mostrarError('El archivo excede el límite de 50 MB');
        return;
    }

    // Archivo válido - procesar
    console.log('Archivo válido, procesando...');
    archivoActual = archivo;
    procesarArchivo(archivo, tamañoMB);
}

/**
 * Muestra modal de error
 */
function mostrarError(mensaje) {
    console.log('Mostrando error:', mensaje);
    
    const modalError = document.getElementById('modal-error');
    const mensajeError = document.getElementById('mensaje-error');
    const cerrarModalError = document.getElementById('cerrar-modal-error');
    const btnCerrarError = document.getElementById('btn-cerrar-error');
    
    if (!modalError || !mensajeError) {
        console.error('No se encontró el modal de error en el DOM');
        alert('Error: ' + mensaje);
        return;
    }
    
    mensajeError.textContent = mensaje;
    modalError.classList.add('activo');

    const cerrarError = function() {
        modalError.classList.remove('activo');
    };

    if (cerrarModalError) {
        cerrarModalError.onclick = cerrarError;
    }
    
    if (btnCerrarError) {
        btnCerrarError.onclick = cerrarError;
    }

    // Cerrar al hacer clic fuera
    modalError.addEventListener('click', function(e) {
        if (e.target === modalError) {
            cerrarError();
        }
    }, { once: true });
}

/**
 * Procesa el archivo seleccionado
 */
function procesarArchivo(archivo, tamañoMB) {
    console.log('Procesando archivo:', archivo.name);
    
    // Mostrar información
    mostrarInfoArchivo(archivo, tamañoMB);

    // Cargar en Wavesurfer
    const url = URL.createObjectURL(archivo);
    console.log('Cargando en Wavesurfer...');
    wavesurfer.load(url);
}

/**
 * Muestra la información del archivo
 */
function mostrarInfoArchivo(archivo, tamañoMB) {
    console.log('Mostrando información del archivo');
    
    const archivoInfo = document.getElementById('archivo-info');
    if (archivoInfo) {
        archivoInfo.style.display = 'block';
        console.log('Información visible');
    }
    
    const infoNombre = document.getElementById('info-nombre');
    const infoPeso = document.getElementById('info-peso');
    const infoFormato = document.getElementById('info-formato');
    const infoClasificacion = document.getElementById('info-clasificacion');
    
    if (infoNombre) infoNombre.textContent = archivo.name;
    if (infoPeso) infoPeso.textContent = tamañoMB.toFixed(2) + ' MB';
    if (infoFormato) infoFormato.textContent = archivo.name.split('.').pop().toUpperCase();
    if (infoClasificacion) infoClasificacion.textContent = 'Detectando...';
    
    // Simular clasificación después de cargar
    setTimeout(function() {
        if (infoClasificacion) infoClasificacion.textContent = 'Polifónico (Piano)';
    }, 2000);
}

/**
 * Actualiza la duración en la información
 */
function actualizarInfoDuracion(duracion) {
    const infoDuracion = document.getElementById('info-duracion');
    if (!infoDuracion || !duracion) return;
    
    const minutos = Math.floor(duracion / 60);
    const segundos = Math.floor(duracion % 60);
    infoDuracion.textContent = 
        minutos + ':' + segundos.toString().padStart(2, '0');
}

/**
 * Habilita el botón de transcribir
 */
function habilitarBotonTranscribir() {
    const btnTranscribir = document.getElementById('btn-transcribir');
    if (btnTranscribir) {
        btnTranscribir.disabled = false;
        btnTranscribir.classList.remove('btn-deshabilitado');
        console.log('Botón transcribir habilitado');
    }
}

// Función global para el botón de play
window.reproducirAudio = function() {
    if (wavesurfer) {
        wavesurfer.playPause();
    }
};

document.addEventListener('DOMContentLoaded', function() {
    const btnPlay = document.getElementById('btn-play');
    if (btnPlay) {
        btnPlay.addEventListener('click', window.reproducirAudio);
    }
});