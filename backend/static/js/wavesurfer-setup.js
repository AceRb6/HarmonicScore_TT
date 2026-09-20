/* ============================================
   WAVESURFER SETUP — Espectrograma & Delimitación (RF-01 / RF-04)
   Harmonic Score - Transcripción y Recorte de Audio
   ============================================ */
import WaveSurfer     from '/static/js/vendor/dist/wavesurfer.esm.js';
import RegionsPlugin  from '/static/js/vendor/dist/plugins/regions.esm.js';
import TimelinePlugin from '/static/js/vendor/dist/plugins/timeline.esm.js';

// #2026-09-19 + Restricciones de tiempo: Mínimo 60s (1 min) y Máximo 360s (6 min)
const MIN_DURACION_S = 60;
const MAX_DURACION_S = 360;
const $ = (id) => document.getElementById(id);

let wavesurfer = null;
let wavesurferMinimap = null;
let regions = null;
let regionActual = null;
let audioUrlActual = null;
let duracionTotal = 0;

window.archivoActual = null;              // Lo consume transcripcion.js
window.seleccionHS = null;                // { inicio, fin } en segundos para la API

/* ---------- #2026-09-19 + Formateadores de tiempo y tamaño ---------- */
const fmtDuracion = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

const fmtTiempoConDecima = (s) => {
    if (isNaN(s) || s < 0) s = 0;
    const min = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    const ms = Math.floor((s % 1) * 10);
    return `${String(min).padStart(2, '0')}:${String(sec).padStart(2, '0')}.${ms}`;
};

const fmtPeso = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/* ---------- #2026-09-19 + Utilidad de error expuesta ---------- */
window.mostrarError = function (msg) {
    const modal = $('modal-error'), texto = $('mensaje-error');
    if (modal && texto) { texto.textContent = msg; modal.classList.add('activo'); }
    else alert(msg);
};

/* ---------- #2026-09-19 + Actualización de indicadores formales ---------- */
function actualizarInsigniasTiempo(inicio, fin) {
    inicio = Math.max(0, inicio);
    fin = Math.min(duracionTotal || fin, fin);
    if (fin < inicio) fin = inicio;

    const durSegmento = fin - inicio;

    if ($('tiempo-inicio'))    $('tiempo-inicio').textContent    = fmtTiempoConDecima(inicio);
    if ($('tiempo-fin'))       $('tiempo-fin').textContent       = fmtTiempoConDecima(fin);
    if ($('tiempo-seleccion')) $('tiempo-seleccion').textContent = fmtTiempoConDecima(durSegmento);
    if ($('tiempo-reproduccion-total')) $('tiempo-reproduccion-total').textContent = fmtTiempoConDecima(durSegmento);

    window.seleccionHS = { inicio: parseFloat(inicio.toFixed(2)), fin: parseFloat(fin.toFixed(2)) };
}

/* ---------- #2026-09-19 + Control del botón circular de reproducción ---------- */
function actualizarEstadoBotonPlay(estaReproduciendo) {
    const btnPlayCircular = $('btn-play-circular');
    const icono = $('icono-play-circular');
    const textoInfo = $('estado-reproduccion-texto');

    if (!btnPlayCircular) return;

    if (estaReproduciendo) {
        btnPlayCircular.classList.add('reproduciendo');
        if (icono) icono.textContent = '⏸';
        if (textoInfo) textoInfo.textContent = 'Reproduciendo fragmento...';
    } else {
        btnPlayCircular.classList.remove('reproduciendo');
        if (icono) icono.textContent = '▶';
        if (textoInfo) textoInfo.textContent = 'Reproducir fragmento delimitado';
    }
}

/* ---------- #2026-09-19 + Restringir la posición del cursor rojo dentro de la zona acotada ---------- */
function restringirCursorAZonaAcotada(tiempoObjetivo) {
    if (!window.seleccionHS || !duracionTotal) return;
    const inicio = window.seleccionHS.inicio;
    const fin = window.seleccionHS.fin;

    if (tiempoObjetivo < inicio) {
        wavesurfer.seekTo(inicio / duracionTotal);
        if (wavesurferMinimap) wavesurferMinimap.seekTo(inicio / duracionTotal);
        if ($('tiempo-reproduccion-actual')) $('tiempo-reproduccion-actual').textContent = fmtTiempoConDecima(0);
    } else if (tiempoObjetivo > fin) {
        wavesurfer.seekTo(fin / duracionTotal);
        if (wavesurferMinimap) wavesurferMinimap.seekTo(fin / duracionTotal);
        if ($('tiempo-reproduccion-actual')) $('tiempo-reproduccion-actual').textContent = fmtTiempoConDecima(fin - inicio);
    } else {
        const tiempoRelativo = tiempoObjetivo - inicio;
        if ($('tiempo-reproduccion-actual')) $('tiempo-reproduccion-actual').textContent = fmtTiempoConDecima(tiempoRelativo);
    }
}

/* ------------------------------------------------
   #2026-09-19 + INICIALIZACIÓN DE VISUALIZADORES
------------------------------------------------ */
function initWaveSurfer() {
    // 1. Espectrograma de Onda Principal (Módulo Mayor Superior con cursor rojo)
    wavesurfer = WaveSurfer.create({
        container: '#waveform',
        height: 200,
        waveColor: '#0284C7',
        progressColor: '#0369A1',
        cursorColor: '#DC2626',      // #2026-09-19 + Barra de posición roja interactiva
        cursorWidth: 3,
        barWidth: 2,
        barGap: 2,
        barRadius: 2,
        normalize: true,
    });

    // 2. Módulo de Delimitación y Línea de Tiempo Fina (Módulo Inferior con cursor rojo)
    regions = RegionsPlugin.create({});
    wavesurferMinimap = WaveSurfer.create({
        container: '#waveform-minimap',
        height: 65,
        waveColor: '#94A3B8',
        progressColor: '#7DD3FC',
        cursorColor: '#DC2626',      // #2026-09-19 + Barra de posición roja interactiva
        cursorWidth: 2,
        barWidth: 1,
        barGap: 1,
        normalize: true,
        plugins: [
            regions,
            TimelinePlugin.create({ container: '#waveform-timeline' }),
        ],
    });

    // #2026-09-19 + Interacción y arrastre del cursor rojo restringido a la zona acotada
    wavesurfer.on('seeking', (tiempo) => restringirCursorAZonaAcotada(tiempo));
    wavesurfer.on('interaction', (tiempo) => {
        restringirCursorAZonaAcotada(tiempo);
        if (wavesurferMinimap && duracionTotal) {
            const tClamped = Math.max(window.seleccionHS?.inicio || 0, Math.min(window.seleccionHS?.fin || duracionTotal, tiempo));
            wavesurferMinimap.seekTo(tClamped / duracionTotal);
        }
    });

    // #2026-09-19 + Sincronización del cursor rojo al hacer clic en el minimapa
    wavesurferMinimap.on('seeking', (tiempo) => {
        restringirCursorAZonaAcotada(tiempo);
        if (wavesurfer && duracionTotal) {
            const tClamped = Math.max(window.seleccionHS?.inicio || 0, Math.min(window.seleccionHS?.fin || duracionTotal, tiempo));
            wavesurfer.seekTo(tClamped / duracionTotal);
        }
    });
    wavesurferMinimap.on('interaction', (tiempo) => {
        restringirCursorAZonaAcotada(tiempo);
        if (wavesurfer && duracionTotal) {
            const tClamped = Math.max(window.seleccionHS?.inicio || 0, Math.min(window.seleccionHS?.fin || duracionTotal, tiempo));
            wavesurfer.seekTo(tClamped / duracionTotal);
        }
    });

    // #2026-09-19 + Sincronización al completar la carga del audio y aplicación de límites min/max
    wavesurfer.on('ready', (dur) => {
        duracionTotal = dur;
        $('waveform-placeholder').style.display = 'none';
        $('info-duracion').textContent = fmtDuracion(dur);
        $('badge-estado-audio').textContent = 'Audio cargado';
        $('badge-estado-audio').style.background = '#F1F5F9';
        $('badge-estado-audio').style.borderColor = '#CBD5E1';
        $('badge-estado-audio').style.color = '#1E293B';

        if (dur > MAX_DURACION_S) {
            window.mostrarError('Duración excedida. El archivo no debe superar los seis minutos');
            $('btn-transcribir').disabled = true;
            $('btn-play-circular').disabled = true;
            window.seleccionHS = null;
            return;
        }

        // #2026-09-19 + Configurar región delimitadora con límites estrictos (min: 60s, max: 360s)
        const durMinima = Math.min(MIN_DURACION_S, dur);
        const durMaxima = Math.min(MAX_DURACION_S, dur);
        const durInicial = Math.min(MAX_DURACION_S, dur);

        if (regions) regions.clearRegions();
        regionActual = regions.addRegion({
            start: 0,
            end: durInicial,
            color: 'rgba(2, 132, 199, 0.18)',
            drag: true,
            resize: true,
            minLength: durMinima,  // #2026-09-19 + Asegura que no se contraiga a menos del mínimo
            maxLength: durMaxima,  // #2026-09-19 + Asegura que no se expanda a más del máximo
        });

        actualizarInsigniasTiempo(0, durInicial);

        // #2026-09-19 + Si el usuario manipula la delimitación en tiempo real, parar la reproducción de inmediato
        regionActual.on('update', () => {
            if (wavesurfer && wavesurfer.isPlaying()) {
                wavesurfer.pause();
                actualizarEstadoBotonPlay(false);
            }
            actualizarInsigniasTiempo(regionActual.start, regionActual.end);
        });

        regionActual.on('update-end', () => {
            actualizarInsigniasTiempo(regionActual.start, regionActual.end);
            console.info('Segmento acotado actualizado (Límites aplicados):', window.seleccionHS);
        });

        $('btn-transcribir').disabled = false;
        $('btn-play-circular').disabled = false;
    });

    // #2026-09-19 + Monitoreo de tiempo durante la reproducción para respetar los límites acotados
    wavesurfer.on('timeupdate', (tiempoActual) => {
        if (!window.seleccionHS) return;
        const inicio = window.seleccionHS.inicio;
        const fin = window.seleccionHS.fin;

        // Mostrar tiempo transcurrido dentro del segmento
        const tiempoEnSegmento = Math.max(0, tiempoActual - inicio);
        if ($('tiempo-reproduccion-actual')) {
            $('tiempo-reproduccion-actual').textContent = fmtTiempoConDecima(tiempoEnSegmento);
        }

        // Si la reproducción sobrepasa el límite final del segmento acotado, pausar y volver al inicio
        if (tiempoActual >= fin) {
            wavesurfer.pause();
            wavesurfer.seekTo(inicio / duracionTotal);
            if (wavesurferMinimap) wavesurferMinimap.seekTo(inicio / duracionTotal);
            actualizarEstadoBotonPlay(false);
            if ($('tiempo-reproduccion-actual')) {
                $('tiempo-reproduccion-actual').textContent = fmtTiempoConDecima(0);
            }
        }
    });

    wavesurfer.on('play', () => actualizarEstadoBotonPlay(true));
    wavesurfer.on('pause', () => actualizarEstadoBotonPlay(false));
    wavesurfer.on('finish', () => {
        actualizarEstadoBotonPlay(false);
        if (window.seleccionHS) {
            wavesurfer.seekTo(window.seleccionHS.inicio / duracionTotal);
            if (wavesurferMinimap) wavesurferMinimap.seekTo(window.seleccionHS.inicio / duracionTotal);
        }
    });

    wavesurfer.on('error', (err) => {
        console.error('WaveSurfer Principal:', err);
        window.mostrarError('Error al decodificar el audio. Verifica que el archivo no esté corrupto.');
    });

    // #2026-09-19 + Manejador de clic en el botón circular de Play (reproduce únicamente el rango acotado)
    $('btn-play-circular').addEventListener('click', () => {
        if (!wavesurfer || !window.seleccionHS) return;

        if (wavesurfer.isPlaying()) {
            wavesurfer.pause();
        } else {
            const tiempoActual = wavesurfer.getCurrentTime();
            const inicio = window.seleccionHS.inicio;
            const fin = window.seleccionHS.fin;

            // Si el cursor rojo está fuera del rango acotado, moverlo al inicio del segmento
            if (tiempoActual < inicio || tiempoActual >= fin - 0.05) {
                wavesurfer.seekTo(inicio / duracionTotal);
                if (wavesurferMinimap) wavesurferMinimap.seekTo(inicio / duracionTotal);
            }
            wavesurfer.play();
        }
    });

    // #2026-09-19 + Botón para restablecer la selección al rango permitido (mínimo 60s, máximo 360s)
    if ($('btn-reset-region')) {
        $('btn-reset-region').addEventListener('click', () => {
            if (!regionActual || !duracionTotal) return;
            const durMinima = Math.min(MIN_DURACION_S, duracionTotal);
            const durMaxima = Math.min(MAX_DURACION_S, duracionTotal);
            regionActual.setOptions({
                start: 0,
                end: durMaxima,
                minLength: durMinima,
                maxLength: durMaxima
            });
            actualizarInsigniasTiempo(0, durMaxima);
            wavesurfer.seekTo(0);
            if (wavesurferMinimap) wavesurferMinimap.seekTo(0);
        });
    }
}

/* ------------------------------------------------
   #2026-09-19 + CARGA Y VALIDACIÓN DE ARCHIVOS
------------------------------------------------ */
function manejarArchivo(file) {
    if (!file) return;
    const ext = '.' + (file.name.split('.').pop() || '').toLowerCase();
    const mimeOk = ['audio/mpeg', 'audio/mp3', 'audio/wav'].includes(file.type);
    if (!['.mp3', '.wav'].includes(ext) && !mimeOk) {
        window.mostrarError(CONFIG.MENSAJES.ERROR_FORMATO);   // msn2 CU-04
        return;
    }
    if (file.size > CONFIG.TAMANO_MAXIMO_ARCHIVO_MB * 1024 * 1024) {
        window.mostrarError(CONFIG.MENSAJES.ERROR_TAMANO);    // msn3 CU-04
        return;
    }

    window.archivoActual = file;
    $('info-nombre').textContent = file.name;
    $('info-peso').textContent = fmtPeso(file.size);
    $('info-formato').textContent = ext.replace('.', '').toUpperCase();
    $('info-duracion').textContent = '--';
    $('detalles-vacio').style.display = 'none';
    $('archivo-info').style.display = 'block';
    $('btn-transcribir').disabled = true;
    $('btn-play-circular').disabled = true;

    $('drop-texto-1').textContent = '¡Archivo cargado con éxito!';

    if (regions) regions.clearRegions();
    window.seleccionHS = null;

    if (audioUrlActual) {
        URL.revokeObjectURL(audioUrlActual);
    }
    audioUrlActual = URL.createObjectURL(file);

    // #2026-09-19 + Cargar el archivo simultáneamente en el espectrograma mayor y en el minimapa
    wavesurfer.load(audioUrlActual).catch((e) => {
        console.error(e);
        window.mostrarError('Error al decodificar el audio en el visor principal.');
    });

    wavesurferMinimap.load(audioUrlActual).catch((e) => {
        console.error(e);
    });
}

/* ------------------------------------------------
   #2026-09-19 + MODALES Y EVENTOS DE INTERFAZ
------------------------------------------------ */
function initModales() {
    const modal = $('modal-error');
    if (!modal) return;
    const cerrar = () => modal.classList.remove('activo');

    const btnX  = $('cerrar-modal-error');
    const btnOk = $('btn-cerrar-error');
    if (btnX)  btnX.addEventListener('click', cerrar);
    if (btnOk) btnOk.addEventListener('click', cerrar);

    modal.addEventListener('click', (e) => { if (e.target === modal) cerrar(); });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && modal.classList.contains('activo')) cerrar();
    });
}

function initInterfazCarga() {
    $('btn-examinar').addEventListener('click', () => $('file-input').click());
    $('file-input').addEventListener('change', (e) => manejarArchivo(e.target.files[0]));

    const zone = $('drop-zone');
    zone.addEventListener('dragover', (e) => { e.preventDefault(); zone.style.borderColor = '#0284C7'; });
    zone.addEventListener('dragleave', () => { zone.style.borderColor = '#7DD3FC'; });
    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.style.borderColor = '#7DD3FC';
        manejarArchivo(e.dataTransfer.files[0]);
    });
}

document.addEventListener('DOMContentLoaded', () => {
    if (!$('waveform')) return;
    initWaveSurfer();
    initInterfazCarga();
    initModales();
});