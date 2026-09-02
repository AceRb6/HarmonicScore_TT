/* ============================================
   CONTROLES DE RECORTADOR SOBRE FORMA DE ONDA
   Dos tiradores verticales arrastrables (#FFC107)
   Zona interior azul (#2196F3) y exterior gris oscuro
   Barra delgada roja de progreso en tiempo real (#EF4444)
   Botón Play redondo y azul para pausar/reproducir exclusivamente el fragmento acotado
   Proyecto: Harmonic Score
   2026-09-01
   ============================================ */

let trimmerInicioSeg      = 0;
let trimmerFinSeg         = 0;
let decodedMasterBuffer   = null;
let fragmentAudioCtx      = null;
let fragmentSource        = null;
let fragmentStartTime     = 0;
let fragmentPauseOffset   = 0; // Segundos relativos desde trimmerInicioSeg
let reproduciendo         = false;
let avisoDuracionMostrado = false;
let blobFragmento         = null;
let animProgresoId        = null;

document.addEventListener('DOMContentLoaded', function() {
    inicializarRecortadorTiradores();
});

/**
 * 2026-09-01: Inicializa los eventos de arrastre y el botón play redondo
 */
function inicializarRecortadorTiradores() {
    const contenedor    = document.getElementById('trimmer-contenedor');
    const tiradorInicio = document.getElementById('tirador-inicio');
    const tiradorFin    = document.getElementById('tirador-fin');
    const btnPlay       = document.getElementById('btn-play-fragmento');

    if (!contenedor || !tiradorInicio || !tiradorFin) return;

    let arrastrandoInicio = false;
    let arrastrandoFin    = false;

    // 1. Iniciar arrastre Tirador Inicio
    tiradorInicio.addEventListener('mousedown', function(e) {
        e.preventDefault();
        e.stopPropagation();
        arrastrandoInicio = true;
        document.body.style.cursor = 'ew-resize';
    });
    tiradorInicio.addEventListener('touchstart', function(e) {
        e.stopPropagation();
        arrastrandoInicio = true;
    }, { passive: true });

    // 2. Iniciar arrastre Tirador Fin
    tiradorFin.addEventListener('mousedown', function(e) {
        e.preventDefault();
        e.stopPropagation();
        arrastrandoFin = true;
        document.body.style.cursor = 'ew-resize';
    });
    tiradorFin.addEventListener('touchstart', function(e) {
        e.stopPropagation();
        arrastrandoFin = true;
    }, { passive: true });

    // 3. Movimiento de arrastre
    function procesarMovimiento(clientX) {
        if (!arrastrandoInicio && !arrastrandoFin) return;
        const durTotal = window.obtenerDuracionTotal ? window.obtenerDuracionTotal() : 0;
        if (durTotal <= 0) return;

        const rect   = contenedor.getBoundingClientRect();
        const mouseX = Math.max(0, Math.min(rect.width, clientX - rect.left));
        const pct    = mouseX / rect.width;
        const tiempo = pct * durTotal;

        if (arrastrandoInicio) {
            // El tirador izquierdo nunca cruza al derecho (mínimo 1s)
            let nuevoInicio = Math.max(0, Math.min(tiempo, trimmerFinSeg - 1.0));
            if (trimmerFinSeg - nuevoInicio > 360) {
                nuevoInicio = Math.max(0, trimmerFinSeg - 360);
                mostrarAvisoDuracionMaxima();
            }
            trimmerInicioSeg = nuevoInicio;
        } else if (arrastrandoFin) {
            // El tirador derecho nunca es menor a inicio + 1s
            let nuevoFin = Math.min(durTotal, Math.max(tiempo, trimmerInicioSeg + 1.0));
            if (nuevoFin - trimmerInicioSeg > 360) {
                nuevoFin = Math.min(durTotal, trimmerInicioSeg + 360);
                mostrarAvisoDuracionMaxima();
            }
            trimmerFinSeg = nuevoFin;
        }

        // Si se cambia la acotación durante la reproducción, reiniciar offset y ocultar cursor
        detenerFragmento();
        blobFragmento = null;
        actualizarVisualRecortador();
    }

    document.addEventListener('mousemove', function(e) {
        procesarMovimiento(e.clientX);
    });
    document.addEventListener('touchmove', function(e) {
        if (e.touches && e.touches[0]) {
            procesarMovimiento(e.touches[0].clientX);
        }
    });

    // 4. Finalizar arrastre
    function finalizarArrastre() {
        if (arrastrandoInicio || arrastrandoFin) {
            arrastrandoInicio = false;
            arrastrandoFin    = false;
            document.body.style.cursor = 'default';
        }
    }

    document.addEventListener('mouseup', finalizarArrastre);
    document.addEventListener('touchend', finalizarArrastre);

    // 5. Botón único redondo azul Play / Pause
    if (btnPlay) {
        btnPlay.addEventListener('click', async function() {
            if (reproduciendo) {
                pausarFragmento();
            } else {
                await iniciarReproduccionFragmento();
            }
        });
    }
}

/**
 * 2026-09-01: Actualiza visualmente los tiradores, zonas y textos
 */
function actualizarVisualRecortador() {
    const durTotal = window.obtenerDuracionTotal ? window.obtenerDuracionTotal() : 0;
    if (durTotal <= 0) return;

    const pctInicio = (trimmerInicioSeg / durTotal) * 100;
    const pctFin    = (trimmerFinSeg / durTotal) * 100;

    const tiradorInicio = document.getElementById('tirador-inicio');
    const tiradorFin    = document.getElementById('tirador-fin');
    const zonaActiva    = document.getElementById('trimmer-zona-activa');
    const maskLeft      = document.getElementById('trimmer-mask-left');
    const maskRight     = document.getElementById('trimmer-mask-right');
    const txtInicio     = document.getElementById('txt-inicio');
    const txtFin        = document.getElementById('txt-fin');
    const lblSeleccion  = document.getElementById('lbl-seleccion');

    if (tiradorInicio) tiradorInicio.style.left = `${pctInicio}%`;
    if (tiradorFin)    tiradorFin.style.left    = `${pctFin}%`;

    if (zonaActiva) {
        zonaActiva.style.left  = `${pctInicio}%`;
        zonaActiva.style.width = `${Math.max(0, pctFin - pctInicio)}%`;
    }

    if (maskLeft)  maskLeft.style.width  = `${pctInicio}%`;
    if (maskRight) maskRight.style.width = `${Math.max(0, 100 - pctFin)}%`;

    if (txtInicio) txtInicio.textContent = formatearTiempo(trimmerInicioSeg);
    if (txtFin)    txtFin.textContent    = formatearTiempo(trimmerFinSeg);

    const durSel = Math.max(0, trimmerFinSeg - trimmerInicioSeg);
    if (lblSeleccion) {
        lblSeleccion.textContent = `Fragmento: ${formatearTiempo(trimmerInicioSeg)} - ${formatearTiempo(trimmerFinSeg)} (Duración: ${formatearTiempo(durSel)})`;
    }
}

/**
 * 2026-09-01: Inicializa el rango del recortador al cargar audio
 */
window.inicializarRangoRecortador = function(duracion) {
    trimmerInicioSeg    = 0;
    trimmerFinSeg       = duracion;
    decodedMasterBuffer = null;
    detenerFragmento();
    actualizarVisualRecortador();
};

/**
 * 2026-09-01: Reproduce EXACTA Y EXCLUSIVAMENTE el audio acotado con barra roja en tiempo real
 */
async function iniciarReproduccionFragmento() {
    const archivo = (window.obtenerArchivoActual ? window.obtenerArchivoActual() : null) || window.archivoActual;
    if (!archivo) {
        alert('Carga un archivo de audio primero');
        return;
    }

    const durSegmento = Math.max(0.1, trimmerFinSeg - trimmerInicioSeg);
    if (fragmentPauseOffset >= durSegmento - 0.05) {
        fragmentPauseOffset = 0;
    }

    const startOffsetEnAudio = trimmerInicioSeg + fragmentPauseOffset;
    const duracionRestante   = Math.max(0.05, trimmerFinSeg - startOffsetEnAudio);

    try {
        if (!decodedMasterBuffer) {
            const arrayBuffer = await archivo.arrayBuffer();
            const tempCtx = new (window.AudioContext || window.webkitAudioContext)();
            decodedMasterBuffer = await tempCtx.decodeAudioData(arrayBuffer);
            tempCtx.close();
        }

        fragmentAudioCtx = new (window.AudioContext || window.webkitAudioContext)();
        fragmentSource   = fragmentAudioCtx.createBufferSource();
        fragmentSource.buffer = decodedMasterBuffer;
        fragmentSource.connect(fragmentAudioCtx.destination);

        // Inicia exactamente en startOffsetEnAudio y dura EXACTAMENTE duracionRestante
        fragmentSource.start(0, startOffsetEnAudio, duracionRestante);
        fragmentStartTime = fragmentAudioCtx.currentTime;
        reproduciendo     = true;
        actualizarIconoPlay(true);
        iniciarAnimacionCursorRojo();

        fragmentSource.onended = function() {
            if (reproduciendo && fragmentAudioCtx) {
                const transcurrido = fragmentAudioCtx.currentTime - fragmentStartTime;
                if (transcurrido >= duracionRestante - 0.15) {
                    detenerFragmento();
                }
            }
        };

    } catch (err) {
        console.error('Error al reproducir fragmento:', err);
        detenerFragmento();
    }
}

/**
 * 2026-09-01: Anima la barra delgada roja en tiempo real conforme avanza la música
 */
function iniciarAnimacionCursorRojo() {
    cancelarAnimacionCursorRojo();
    const cursor = document.getElementById('trimmer-cursor-play');
    if (!cursor) return;
    cursor.style.display = 'block';

    function paso() {
        if (!reproduciendo || !fragmentAudioCtx) return;

        const durTotal = window.obtenerDuracionTotal ? window.obtenerDuracionTotal() : 0;
        if (durTotal > 0) {
            const transcurrido = fragmentAudioCtx.currentTime - fragmentStartTime;
            const tiempoActual = Math.min(trimmerFinSeg, trimmerInicioSeg + fragmentPauseOffset + transcurrido);
            const pct = (tiempoActual / durTotal) * 100;
            cursor.style.left = `${pct}%`;
        }

        animProgresoId = requestAnimationFrame(paso);
    }

    animProgresoId = requestAnimationFrame(paso);
}

function cancelarAnimacionCursorRojo() {
    if (animProgresoId) {
        cancelAnimationFrame(animProgresoId);
        animProgresoId = null;
    }
}

/**
 * Pausa la reproducción del fragmento
 */
function pausarFragmento() {
    cancelarAnimacionCursorRojo();
    if (fragmentAudioCtx && reproduciendo) {
        const transcurrido = fragmentAudioCtx.currentTime - fragmentStartTime;
        fragmentPauseOffset += transcurrido;
        try {
            fragmentSource.stop();
            fragmentAudioCtx.close();
        } catch (e) {}
    }
    reproduciendo = false;
    actualizarIconoPlay(false);
}

/**
 * Detiene la reproducción del fragmento y oculta la barra roja
 */
function detenerFragmento() {
    cancelarAnimacionCursorRojo();
    if (fragmentAudioCtx && reproduciendo) {
        try {
            fragmentSource.stop();
            fragmentAudioCtx.close();
        } catch (e) {}
    }
    reproduciendo       = false;
    fragmentPauseOffset = 0;
    actualizarIconoPlay(false);

    const cursor = document.getElementById('trimmer-cursor-play');
    if (cursor) {
        cursor.style.display = 'none';
    }
}

/**
 * Actualiza el ícono del botón play redondo
 */
function actualizarIconoPlay(enPlay) {
    const icono = document.getElementById('icono-play-fragmento');
    if (!icono) return;
    if (enPlay) {
        icono.textContent  = '❚❚';
        icono.style.marginLeft = '0px';
        icono.style.fontSize   = '1.2rem';
    } else {
        icono.textContent  = '▶';
        icono.style.marginLeft = '3px';
        icono.style.fontSize   = '1.5rem';
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
 * Muestra aviso si se superan los 6 minutos
 */
function mostrarAvisoDuracionMaxima() {
    if (avisoDuracionMostrado) return;
    avisoDuracionMostrado = true;
    const lblSeleccion = document.getElementById('lbl-seleccion');
    if (lblSeleccion) {
        lblSeleccion.textContent = 'Duración máxima alcanzada (6 minutos)';
        lblSeleccion.style.color = '#DC2626';
        setTimeout(() => {
            lblSeleccion.style.color = '#0284C7';
            actualizarVisualRecortador();
            avisoDuracionMostrado = false;
        }, 2500);
    }
}

/**
 * Codificador WAV para exportación a la API
 */
function audioBufferToWavBlob(buffer) {
    const numChannels = buffer.numberOfChannels;
    const sampleRate  = buffer.sampleRate;
    const bitsPerSample = 16;
    const byteRate    = sampleRate * numChannels * bitsPerSample / 8;
    const blockAlign  = numChannels * bitsPerSample / 8;
    const samples     = buffer.length;
    const dataSize    = samples * numChannels * 2;
    const bufferSize  = 44 + dataSize;

    const arrayBuffer = new ArrayBuffer(bufferSize);
    const view        = new DataView(arrayBuffer);

    writeString(view, 0, 'RIFF');
    view.setUint32(4, bufferSize - 8, true);
    writeString(view, 8, 'WAVE');
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, byteRate, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitsPerSample, true);
    writeString(view, 36, 'data');
    view.setUint32(40, dataSize, true);

    let offset = 44;
    for (let i = 0; i < samples; i++) {
        for (let ch = 0; ch < numChannels; ch++) {
            const sample = Math.max(-1, Math.min(1, buffer.getChannelData(ch)[i]));
            view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
            offset += 2;
        }
    }

    return new Blob([arrayBuffer], { type: 'audio/wav' });
}

function writeString(view, offset, str) {
    for (let i = 0; i < str.length; i++) {
        view.setUint8(offset + i, str.charCodeAt(i));
    }
}

/**
 * 2026-09-01: Obtener el fragmento acotado para envío al backend
 */
window.obtenerBlobFragmento = async function() {
    const archivo  = (window.obtenerArchivoActual ? window.obtenerArchivoActual() : null) || window.archivoActual;
    const durTotal = window.obtenerDuracionTotal ? window.obtenerDuracionTotal() : 0;
    if (!archivo) return null;

    const esCompleto = (trimmerInicioSeg <= 0.1) && (trimmerFinSeg >= durTotal - 0.1);
    if (esCompleto) return archivo;

    if (blobFragmento) return blobFragmento;

    try {
        const arrayBuffer   = await archivo.arrayBuffer();
        const tempCtx       = new (window.AudioContext || window.webkitAudioContext)();
        const audioBuffer   = await tempCtx.decodeAudioData(arrayBuffer);
        const sampleRate    = audioBuffer.sampleRate;
        const muestraInicio = Math.floor(trimmerInicioSeg * sampleRate);
        const muestraFin    = Math.floor(trimmerFinSeg * sampleRate);
        const durFragmento  = Math.max(1, muestraFin - muestraInicio);

        const offlineCtx = new OfflineAudioContext(audioBuffer.numberOfChannels, durFragmento, sampleRate);
        const source     = offlineCtx.createBufferSource();
        source.buffer    = audioBuffer;
        source.connect(offlineCtx.destination);
        source.start(0, trimmerInicioSeg, trimmerFinSeg - trimmerInicioSeg);

        const bufferRecortado = await offlineCtx.startRendering();
        tempCtx.close();

        blobFragmento = audioBufferToWavBlob(bufferRecortado);
        return blobFragmento;
    } catch (e) {
        console.error('Error al generar blob recortado:', e);
        return archivo;
    }
};
