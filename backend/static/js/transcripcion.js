/* LÓGICA DE TRANSCRIPCIÓN — CU-05: flujo real vía Django orquestador */
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

/* Barra estimada (el proxy Django es síncrono: no hay etapas que pollear
   desde el front en Ciclo 1; se documenta como limitación CU-05/RNF-02) */
function iniciarBarraEstimada() {
    const t0 = Date.now();
    intervaloProgreso = setInterval(() => {
        const t = (Date.now() - t0) / 1000;
        const pct = Math.min(90, Math.round(100 * (1 - Math.exp(-t / 40))));
        setProgreso(pct, pct + '% (estimado)');
    }, 500);
}

async function iniciarTranscripcionReal() {
    if (typeof archivoActual === 'undefined' || !archivoActual) {
        mostrarError('No hay ningún archivo válido seleccionado para transcribir.');
        return;
    }
    transcripcionActiva = true;
    setProgreso(5, 'Enviando audio...');
    document.getElementById('modal-progreso').classList.add('activo');
    iniciarBarraEstimada();

    const formData = new FormData();
    formData.append('audio', archivoActual);

    try {
        const r = await DjangoAPI.peticion('/transcripciones/subir/', 'POST', formData);
        clearInterval(intervaloProgreso);
        if (r.ok) {
            setProgreso(100, '100%');
            guardarJobLocal(r.data);
            setTimeout(() => finalizarTranscripcion(true), 3000);
        } else {
            throw new Error(r.data.error || 'Error en el procesamiento');
        }
    } catch (e) {
        clearInterval(intervaloProgreso);
        document.getElementById('modal-progreso').classList.remove('activo');
        transcripcionActiva = false;
        mostrarError('Error en el procesamiento. Verifica tu conexión con el servidor. (' + e.message + ')');
    }
}

function guardarJobLocal(data) {
    const jobs = JSON.parse(localStorage.getItem('hs_jobs') || '[]');
    jobs.unshift({
        titulo: archivoActual.name,
        fecha: new Date().toLocaleDateString('es-MX'),
        estado: 'completado',
        url_descarga: CONFIG.API_ML_URL + (data.pdf_url || ''),
        metrics: data.metrics || null
    });
    localStorage.setItem('hs_jobs', JSON.stringify(jobs.slice(0, 20)));
}

function finalizarTranscripcion(esExito) {
    if (!esExito) return;
    transcripcionActiva = false;
    setTimeout(() => {
        document.getElementById('modal-progreso').classList.remove('activo');
        alert('Transcripción completada. Redirigiendo a consultas...');   // msn1 CU-05
        window.location.href = 'consultas.html';
    }, 500);
}