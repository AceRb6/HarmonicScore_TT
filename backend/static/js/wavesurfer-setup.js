/* ============================================
   WAVESURFER SETUP — RF-01 / RF-04 (módulo ES)
   Visualización, reproducción y selección de segmento
   con marcadores arrastrables (RegionsPlugin).
   Ajustes aplicados:
   - initModales(): cableado de cierre del modal de error (X, Aceptar, clic fuera, Escape)
   - regions.clearRegions() al cargar un archivo nuevo (evita regiones fantasma)
   - Listener de loop (region-out) registrado una sola vez
   ============================================ */
import WaveSurfer     from '/static/js/vendor/dist/wavesurfer.esm.js';
import RegionsPlugin  from '/static/js/vendor/dist/plugins/regions.esm.js';
import TimelinePlugin from '/static/js/vendor/dist/plugins/timeline.esm.js';

const MAX_DURACION_S = 360;               // CU-04 / msn4: máximo 6 minutos
const $ = (id) => document.getElementById(id);

let wavesurfer = null;
let regions = null;
let regionActual = null;

window.archivoActual = null;              // lo consume transcripcion.js
window.seleccionHS = null;                // { inicio, fin } en segundos

/* ---------- utilidades expuestas (las usa transcripcion.js) ---------- */
window.mostrarError = function (msg) {
    const modal = $('modal-error'), texto = $('mensaje-error');
    if (modal && texto) { texto.textContent = msg; modal.classList.add('activo'); }
    else alert(msg);
};

const fmtDuracion = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`;

const fmtPeso = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

/* ----------------------------- inicialización ----------------------------- */
function initWaveSurfer() {
    regions = RegionsPlugin.create({});
    wavesurfer = WaveSurfer.create({
        container: '#waveform',
        height: 220,
        waveColor: '#94A3B8',
        progressColor: '#0284C7',
        cursorColor: '#023E8A',
        barWidth: 2, barGap: 2, barRadius: 2,
        normalize: true,
        plugins: [
            regions,
            TimelinePlugin.create({ container: '#waveform-timeline' }),
        ],
    });

    // Loop dentro de la región (reproducción segmentada, RF-04).
    // Se registra UNA sola vez sobre el plugin, no en cada 'ready'.
    regions.on('region-out', (region) => region.play());

    wavesurfer.on('ready', (dur) => {
        $('waveform-placeholder').style.display = 'none';
        $('info-duracion').textContent = fmtDuracion(dur);

        if (dur > MAX_DURACION_S) {
            // msn4 CU-04
            window.mostrarError('Duración excedida. El archivo no debe superar los seis minutos');
            $('btn-transcribir').disabled = true;
            window.seleccionHS = null;
            return;
        }

        // Región por defecto = pieza completa; arrastrable y redimensionable (RF-04)
        regionActual = regions.addRegion({
            start: 0, end: dur,
            color: 'rgba(2, 132, 199, 0.15)',
            drag: true, resize: true,
        });
        window.seleccionHS = { inicio: 0, fin: dur };

        regionActual.on('update-end', () => {
            window.seleccionHS = { inicio: regionActual.start, fin: regionActual.end };
            console.info('Segmento seleccionado:', window.seleccionHS);
        });

        $('btn-transcribir').disabled = false;
    });

    wavesurfer.on('error', (err) => {
        console.error('WaveSurfer:', err);
        window.mostrarError('Error al decodificar el audio. Verifica que el archivo no esté corrupto.');
    });

    // Reproducir / Pausar
    $('btn-play').addEventListener('click', () => {
        if (wavesurfer) wavesurfer.playPause();
    });
}

/* ------------------------- carga y validación (RF-02/03) ------------------------- */
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

    // Estado visual del drop-zone
    $('drop-texto-1').textContent = '¡Archivo cargado con éxito!';

    // Limpiar regiones del archivo anterior (evita marcadores fantasma)
    if (regions) regions.clearRegions();
    window.seleccionHS = null;

    wavesurfer.load(URL.createObjectURL(file)).catch((e) => {
        console.error(e);
        window.mostrarError('Error al decodificar el audio. Verifica que el archivo no esté corrupto.');
    });
}

/* ------------------- AJUSTE: cierre del modal de error ------------------- */
function initModales() {
    const modal = $('modal-error');
    if (!modal) return;
    const cerrar = () => modal.classList.remove('activo');

    const btnX  = $('cerrar-modal-error');   // la X
    const btnOk = $('btn-cerrar-error');     // botón Aceptar
    if (btnX)  btnX.addEventListener('click', cerrar);
    if (btnOk) btnOk.addEventListener('click', cerrar);

    // Cierre con clic fuera del contenido (sobre el overlay)
    modal.addEventListener('click', (e) => { if (e.target === modal) cerrar(); });

    // Cierre con tecla Escape
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
    if (!$('waveform')) return;           // solo en carga.html
    initWaveSurfer();
    initInterfazCarga();
    initModales();                        // ← AJUSTE: cierre del modal de error
});