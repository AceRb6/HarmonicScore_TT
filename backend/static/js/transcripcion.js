/* ============================================
   TRANSCRIPCIÓN — CU-05 (flujo real vía Django orquestador)
   Contrato: POST {origen}/api/transcripciones/subir/  (multipart, campo 'audio')
   Respuesta 200: { success, pdf_url, metrics }  (Django proxyea y polea al ml-service)
   Descarga:      {CONFIG.API_ML}{pdf_url}
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

/* Barra estimada: el proxy Django es síncrono; el progreso real por etapas
   llega en Ciclo 2 (polling async del contrato Ilustración 39). */
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
    if (typeof DjangoAPI === 'undefined') {
        mostrarError('Falta cargar api.js en esta página.');
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

        if (r.ok && r.data && r.data.success) {
            setProgreso(100, '100%');
            guardarJobLocal(r.data);
            finalizarTranscripcion(true);          // msn1 + redirección (CU-05 pasos 8-9)
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

function guardarJobLocal(data) {
    const jobs = JSON.parse(localStorage.getItem('hs_jobs') || '[]');
    jobs.unshift({
        titulo: archivoActual.name,
        fecha: new Date().toLocaleDateString('es-MX'),
        estado: 'completado',
        url_descarga: CONFIG.API_ML + (data.pdf_url || ''),   // artefacto desde FastAPI
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