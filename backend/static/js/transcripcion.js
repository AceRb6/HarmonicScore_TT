/* ============================================
   TRANSCRIPCIÓN — CU-05 (flujo real vía Django orquestador)
   Contrato: POST {origen}/api/transcripciones/subir/ (multipart, campo 'audio')
   Proyecto: Harmonic Score
   ============================================ */
let transcripcionActiva = false;
let intervaloProgreso = null;

document.addEventListener('DOMContentLoaded', inicializarTranscripcion);

function inicializarTranscripcion() {
    const btn = document.getElementById('btn-transcribir');
    if (!btn) return;
    btn.addEventListener('click', iniciarTranscripcionReal);

    const ocultar = () => document.getElementById('modal-progreso').classList.remove('activo');
    document.getElementById('cerrar-modal-progreso').addEventListener('click', ocultar);
    document.getElementById('btn-minimizar-progreso').addEventListener('click', ocultar);
}

function setProgreso(pct, texto) {
    const m = document.getElementById('modal-barra-relleno');
    const mini = document.getElementById('mini-barra-relleno');
    if (m)    { m.style.width = pct + '%'; m.textContent = texto; }
    if (mini) { mini.style.width = pct + '%'; mini.textContent = texto; }
}

function iniciarBarraEstimada() {
    const t0 = Date.now();
    intervaloProgreso = setInterval(() => {
        const t = (Date.now() - t0) / 1000;
        const pct = Math.min(90, Math.round(100 * (1 - Math.exp(-t / 40))));
        setProgreso(pct, pct + '% (estimado)');
    }, 500);
}

/* ------------------------------------------------
   #2026-09-19 + CONVERSIÓN Y RECORTE DE AUDIO
------------------------------------------------ */
function audioBufferToWavBlob(buffer) {
    const numChannels = buffer.numberOfChannels;
    const sampleRate = buffer.sampleRate;
    const format = 1; // PCM
    const bitDepth = 16;
    const bytesPerSample = bitDepth / 8;
    const blockAlign = numChannels * bytesPerSample;
    const length = buffer.length;
    const dataSize = length * blockAlign;
    const bufferSize = 44 + dataSize;
    const arrayBuffer = new ArrayBuffer(bufferSize);
    const view = new DataView(arrayBuffer);

    function writeString(offset, string) {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    }

    writeString(0, 'RIFF');
    view.setUint32(4, 36 + dataSize, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, format, true);
    view.setUint16(22, numChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * blockAlign, true);
    view.setUint16(32, blockAlign, true);
    view.setUint16(34, bitDepth, true);
    writeString(36, 'data');
    view.setUint32(40, dataSize, true);

    let offset = 44;
    for (let i = 0; i < length; i++) {
        for (let channel = 0; channel < numChannels; channel++) {
            let sample = buffer.getChannelData(channel)[i];
            sample = Math.max(-1, Math.min(1, sample));
            view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
            offset += 2;
        }
    }
    return new Blob([arrayBuffer], { type: 'audio/wav' });
}

async function recortarAudioSegmento(archivo, inicio, fin) {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const arrayBuffer = await archivo.arrayBuffer();
        const audioBuffer = await audioCtx.decodeAudioData(arrayBuffer);

        const sampleRate = audioBuffer.sampleRate;
        const canales = audioBuffer.numberOfChannels;
        const startFrame = Math.max(0, Math.floor(inicio * sampleRate));
        const endFrame = Math.min(audioBuffer.length, Math.floor(fin * sampleRate));
        const frameCount = Math.max(0, endFrame - startFrame);

        if (frameCount <= 0) return archivo;

        const slicedBuffer = audioCtx.createBuffer(canales, frameCount, sampleRate);
        for (let c = 0; c < canales; c++) {
            const channelData = audioBuffer.getChannelData(c).subarray(startFrame, endFrame);
            slicedBuffer.copyToChannel(channelData, c);
        }

        const wavBlob = audioBufferToWavBlob(slicedBuffer);
        const nombreBase = archivo.name.replace(/\.[^/.]+$/, "");
        return new File([wavBlob], `${nombreBase}_acotado.wav`, { type: 'audio/wav' });
    } catch (err) {
        console.warn('Aviso: no se pudo recortar en cliente, procesando archivo original:', err);
        return archivo;
    }
}

/* ------------------------------------------------
   #2026-09-19 + ENVÍO DEL AUDIO DELIMITADO AL BACKEND
------------------------------------------------ */
async function iniciarTranscripcionReal() {
    if (typeof archivoActual === 'undefined' || !archivoActual) {
        mostrarError('No hay ningún archivo válido seleccionado para transcribir.');
        return;
    }
    if (typeof DjangoAPI === 'undefined') {
        mostrarError('Falta cargar api.js en esta página.');
        return;
    }

    transcripcionActiva = true;
    setProgreso(5, 'Preparando y procesando audio...');
    document.getElementById('modal-progreso').classList.add('activo');
    iniciarBarraEstimada();

    // #2026-09-19 + Si el usuario delimitó un rango específico, recortar el audio antes de enviarlo
    let archivoParaSubir = archivoActual;
    if (window.seleccionHS && (window.seleccionHS.inicio > 0.05 || (window.seleccionHS.fin && window.seleccionHS.fin < archivoActual.duration - 0.05))) {
        setProgreso(10, 'Recortando fragmento delimitado...');
        archivoParaSubir = await recortarAudioSegmento(archivoActual, window.seleccionHS.inicio, window.seleccionHS.fin);
    }

    const formData = new FormData();
    formData.append('audio', archivoParaSubir);
    if (window.seleccionHS) {
        formData.append('inicio', window.seleccionHS.inicio);
        formData.append('fin', window.seleccionHS.fin);
    }

    try {
        setProgreso(15, 'Enviando audio al servidor...');
        const r = await DjangoAPI.peticion('/transcripciones/subir/', 'POST', formData);
        clearInterval(intervaloProgreso);

        if (r.ok && r.data && r.data.success) {
            setProgreso(100, '100%');
            guardarJobLocal(r.data, archivoParaSubir.name);
            finalizarTranscripcion(true);
        } else {
            throw new Error((r.data && r.data.error) || 'Error en el procesamiento');
        }
    } catch (e) {
        clearInterval(intervaloProgreso);
        document.getElementById('modal-progreso').classList.remove('activo');
        transcripcionActiva = false;
        mostrarError('Error en el procesamiento. Verifica tu conexión con el servidor. (' + e.message + ')');
    }
}

function guardarJobLocal(data, nombreArchivo) {
    const jobs = JSON.parse(localStorage.getItem('hs_jobs') || '[]');
    jobs.unshift({
        titulo: nombreArchivo || archivoActual.name,
        fecha: new Date().toLocaleDateString('es-MX'),
        estado: 'completado',
        url_descarga: CONFIG.API_ML + (data.pdf_url || ''),
        metrics: data.metrics || null
    });
    localStorage.setItem('hs_jobs', JSON.stringify(jobs.slice(0, 20)));
}

function finalizarTranscripcion(esExito) {
    if (!esExito) return;
    transcripcionActiva = false;
    const titulo = document.querySelector('#modal-progreso .modal-titulo');
    if (titulo) titulo.textContent = 'Transcripción completada';
    const nota = document.querySelector('#modal-progreso p');
    if (nota) nota.textContent = 'Redirigiendo a consultas…';
    setTimeout(() => {
        document.getElementById('modal-progreso').classList.remove('activo');
        window.location.href = 'consultas.html';
    }, 2000);
}