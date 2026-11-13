/* ============================================
   GESTIÓN DE TRANSCRIPCIONES
   Controla el estado vacío o con datos de la
   tabla de historial del usuario.
   Actualización reactiva por eventos (SSE):
   solo refresca la tabla cuando el worker de Celery
   notifica que una transcripción se completó o falló.
   Proyecto: Harmonic Score
   ============================================ */

const Transcripciones = {
    eventSource: null,

    /**
     * Muestra un popup visual en pantalla para avisos y errores.
     */
    mostrarPopup(mensaje, esError = false) {
        const modal = document.getElementById('modal-mensaje');
        const titulo = document.getElementById('titulo-mensaje');
        const texto = document.getElementById('texto-mensaje');

        if (!modal || !titulo || !texto) {
            alert(mensaje);
            return;
        }

        titulo.textContent = esError ? 'Error' : 'Notificación';
        titulo.style.color = esError ? 'var(--color-error)' : 'var(--color-header)';
        texto.textContent = mensaje;
        modal.style.display = 'flex';

        const cerrarModal = () => modal.style.display = 'none';
        const btnCerrar = document.getElementById('cerrar-modal-mensaje');
        const btnAceptar = document.getElementById('btn-cerrar-mensaje');

        if (btnCerrar) btnCerrar.onclick = cerrarModal;
        if (btnAceptar) btnAceptar.onclick = cerrarModal;
        modal.onclick = (e) => { if (e.target === modal) cerrarModal(); };
    },

    /**
     * Renderiza una lista de objetos de transcripción en la tabla.
     * Incluye dos botones reales y directos para descargar PDF y MusicXML.
     *
     * @param {Array} lista - Array de objetos { job_id, titulo, fecha, estado }
     */
    renderizar(lista = []) {
        const tbody = document.getElementById('transcripciones-tbody');
        if (!tbody) return;

        tbody.innerHTML = ''; // Limpiar filas anteriores

        let hayEnProceso = false;

        lista.forEach(item => {
            const tr = document.createElement('tr');
            const jobId = item.job_id || item.id; // Asegurar compatibilidad de nombres

            let estadoHtml = '';
            let descargaHtml = '';

            switch (item.estado) {
                case 'completado':
                case 'EXITO':
                    estadoHtml = `<td class="estado-exito">✓ Completado</td>`;
                    descargaHtml = `
                        <td>
                            <div style="display: flex; flex-direction: column; gap: 0.5rem; align-items: center;">
                                <a href="/api/transcripciones/${jobId}/descargar-pdf/" target="_blank" class="btn btn-primario" style="padding: 0.25rem 0.75rem; font-size: 0.85rem; text-decoration: none; text-align: center; width: 100%; max-width: 130px;">
                                    📄 Partitura (PDF)
                                </a>
                                <a href="/api/transcripciones/${jobId}/descargar-mxl/" target="_blank" class="btn" style="padding: 0.25rem 0.75rem; font-size: 0.85rem; text-decoration: none; text-align: center; width: 100%; max-width: 130px; background-color: var(--color-fondo-secundario); color: var(--color-texto); border: 1px solid var(--color-borde);">
                                    🎼 Archivo MusicXML
                                </a>
                            </div>
                        </td>
                    `;
                    break;
                case 'error':
                case 'ERROR':
                    estadoHtml = `<td class="estado-error">✗ Error</td>`;
                    descargaHtml = `<td><span style="color:var(--color-error); font-weight:bold; font-size: 0.85rem;">Falló</span></td>`;
                    break;
                case 'proceso':
                case 'PENDIENTE':
                case 'PROCESANDO':
                    hayEnProceso = true;
                    estadoHtml = `<td class="estado-proceso">⊖ En proceso</td>`;
                    descargaHtml = `<td><span style="color:var(--color-proceso); font-size: 0.85rem;">--</span></td>`;
                    break;
                default:
                    estadoHtml = `<td>—</td>`;
                    descargaHtml = `<td>—</td>`;
            }

            tr.innerHTML = `
                <td>${item.titulo || '—'}</td>
                <td>${item.fecha || '—'}</td>
                ${estadoHtml}
                ${descargaHtml}
            `;
            tbody.appendChild(tr);
        });

        // Después de insertar, actualizar la vista (vacío o tabla)
        this.actualizarVista();

        // Si hay tareas en proceso, escuchar el evento del worker; si no, cerrar escucha
        if (hayEnProceso) {
            this.suscribirEventosWorker();
        } else {
            this.cerrarEventosWorker();
        }
    },

    /**
     * Abre un canal Server-Sent Events (SSE) para recibir notificación push
     * únicamente cuando el worker de Celery reporte que una transcripción
     * terminó con éxito o falló (sin hacer polling periódico).
     */
    suscribirEventosWorker() {
        if (this.eventSource || typeof EventSource === 'undefined') return;

        const baseUrl = (typeof CONFIG !== 'undefined' && CONFIG.API_BASE_URL)
            ? CONFIG.API_BASE_URL
            : '/api';

        this.eventSource = new EventSource(`${baseUrl}/transcripciones/eventos/`, {
            withCredentials: true
        });

        this.eventSource.onmessage = (evento) => {
            try {
                const data = JSON.parse(evento.data);
                if (data.estado === 'completado' || data.estado === 'error' ||
                    data.estado_db === 'EXITO' || data.estado_db === 'ERROR') {
                    this.cargarDesdeBackend();
                }
            } catch (_) {
                this.cargarDesdeBackend();
            }
        };

        this.eventSource.onerror = () => {
            // Si ya no hay filas en proceso en la tabla, cerrar definitivamente
            const sigueEnProceso = document.querySelectorAll('.estado-proceso').length > 0;
            if (!sigueEnProceso) {
                this.cerrarEventosWorker();
            }
        };
    },

    /**
     * Cierra el canal de eventos cuando todas las transcripciones ya finalizaron.
     */
    cerrarEventosWorker() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    },

    /**
     * Actualiza la vista según si hay filas en el tbody.
     */
    actualizarVista() {
        const vacio   = document.getElementById('transcripciones-vacio');
        const wrapper = document.getElementById('transcripciones-tabla-wrapper');
        const leyenda = document.getElementById('transcripciones-leyenda');
        const tbody   = document.getElementById('transcripciones-tbody');

        if (!vacio || !wrapper || !tbody) return;

        const tieneFilas = tbody.querySelectorAll('tr').length > 0;

        if (tieneFilas) {
            vacio.style.display   = 'none';
            wrapper.style.display = 'block';
            if (leyenda) leyenda.style.display = 'block';
        } else {
            vacio.style.display   = 'flex';
            wrapper.style.display = 'none';
            if (leyenda) leyenda.style.display = 'none';
        }
    },

    /**
     * Carga las transcripciones del usuario desde el backend.
     */
    async cargarDesdeBackend() {
        if (typeof DjangoAPI === 'undefined') {
            console.warn('DjangoAPI no disponible.');
            return;
        }

        try {
            const respuesta = await DjangoAPI.peticion('/transcripciones/mis/', 'GET');

            // 1. Usuario autenticado con transcripciones en PostgreSQL
            if (respuesta.ok && Array.isArray(respuesta.data)) {
                const lista = respuesta.data.map(t => ({
                    ...t,
                    fecha: t.fecha ? new Date(t.fecha).toLocaleDateString('es-MX', {
                        year: 'numeric', month: '2-digit', day: '2-digit',
                        hour: '2-digit', minute: '2-digit'
                    }) : '—'
                }));
                this.renderizar(lista);
                return;
            }

            // 2. No autenticado (401)
            if (respuesta.status === 401) {
                this.cerrarEventosWorker();
                if (typeof Sesion !== 'undefined' && Sesion.estaActiva()) {
                    Sesion.cerrar(false);
                }
                this.renderizar([]);
                this.mostrarPopup('Debes iniciar sesión para ver tus transcripciones.', true);
                setTimeout(() => {
                    window.location.href = 'login.html';
                }, 1800);
                return;
            }

            this.renderizar([]);
        } catch (e) {
            console.error('Error al cargar historial:', e);
            this.renderizar([]);
        }
    }
};

/* ------------------------------------------------
   INICIALIZACIÓN AUTOMÁTICA (SIN POLLING)
------------------------------------------------ */
document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('transcripciones-tbody')) return;
    Transcripciones.cargarDesdeBackend();
});

window.addEventListener('beforeunload', () => {
    Transcripciones.cerrarEventosWorker();
});
