/* ============================================
   GESTIÓN DE TRANSCRIPCIONES
   Controla el estado vacío o con datos de la
   tabla de historial del usuario.
   Proyecto: Harmonic Score
   ============================================ */

const Transcripciones = {

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
        document.getElementById('cerrar-modal-mensaje').onclick = cerrarModal;
        document.getElementById('btn-cerrar-mensaje').onclick = cerrarModal;
        modal.onclick = (e) => { if (e.target === modal) cerrarModal(); };
    },

    /**
     * Simula la descarga de un PDF para el CU-06
     */
    descargarPDF(event, exito) {
        event.preventDefault();
        
        // Redirigir a login si es invitado
        if (!Sesion.estaActiva()) {
            window.location.href = 'login.html';
            return;
        }

        if (exito) {
            this.mostrarPopup("Descarga iniciada", false);
        } else {
            this.mostrarPopup("Error al generar PDF", true);
        }
    },

    /**
     * Actualiza la vista según si hay filas en el tbody.
     * - Sin filas → muestra estado vacío
     * - Con filas → muestra tabla y leyenda
     */
    actualizarVista() {
        const vacio   = document.getElementById('transcripciones-vacio');
        const wrapper = document.getElementById('transcripciones-tabla-wrapper');
        const leyenda = document.getElementById('transcripciones-leyenda');
        const tbody   = document.getElementById('transcripciones-tbody');

        if (!vacio || !wrapper || !tbody) return;

        const tieneFilas = tbody.querySelectorAll('tr').length > 0;

        if (tieneFilas) {
            // Hay transcripciones: mostrar tabla y leyenda
            vacio.style.display   = 'none';
            wrapper.style.display = 'block';
            if (leyenda) leyenda.style.display = 'block';
        } else {
            // Historial vacío: mostrar estado vacío
            vacio.style.display   = 'flex';
            wrapper.style.display = 'none';
            if (leyenda) leyenda.style.display = 'none';
        }
    },

    /**
     * Renderiza una lista de objetos de transcripción en la tabla.
     * Listo para recibir datos del backend cuando el endpoint esté disponible.
     *
     * @param {Array} lista - Array de objetos { titulo, fecha, estado, url_descarga }
     *   estado puede ser: 'completado' | 'error' | 'proceso'
     */
    renderizar(lista = []) {
        const tbody = document.getElementById('transcripciones-tbody');
        if (!tbody) return;

        tbody.innerHTML = ''; // Limpiar filas anteriores

        lista.forEach(item => {
            const tr = document.createElement('tr');

            let estadoHtml = '';
            let descargaHtml = '';

            switch (item.estado) {
                case 'completado':
                    estadoHtml   = `<td class="estado-exito">✓ Completado</td>`;
                    // Simulación 80% éxito, 20% error para demo del CU-06
                    const exitoVisual = Math.random() > 0.2;
                    descargaHtml = `<td><a href="#" onclick="Transcripciones.descargarPDF(event, ${exitoVisual})" class="btn btn-primario"
                                        style="padding: 0.25rem 0.75rem; font-size: 0.85rem;">
                                        PDF/XML ↓</a></td>`;
                    break;
                case 'error':
                    estadoHtml   = `<td class="estado-error">✗ Error</td>`;
                    descargaHtml = `<td><span style="color:var(--color-error);font-weight:bold;">Error</span></td>`;
                    break;
                case 'proceso':
                    // #2026-09-19 + Normalización de mayúsculas a texto formal tipo oración
                    estadoHtml   = `<td class="estado-proceso">⊖ En proceso</td>`;
                    descargaHtml = `<td><span style="color:var(--color-proceso);">--</span></td>`;
                    break;
                default:
                    estadoHtml   = `<td>—</td>`;
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
    },

    /**
     * Carga las transcripciones del usuario desde el backend,
     * O muestra datos de demo si el usuario es INVITADO (sin sesión).
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
                if (respuesta.data.length > 0) {
                    const lista = respuesta.data.map(t => ({
                        ...t,
                        fecha: t.fecha ? new Date(t.fecha).toLocaleDateString('es-MX') : '—'
                    }));
                    this.renderizar(lista);
                } else {
                    // Autenticado pero sin transcripciones aún
                    this.renderizar([]);
                }
                return;
            }

            // 2. No autenticado (401)
            if (respuesta.status === 401) {
                // Si había una sesión falsa/antigua en localStorage, limpiarla
                if (Sesion.estaActiva()) {
                    Sesion.cerrar(false); // Limpiar sin bucle
                }
                this.renderizar([]);
                this.mostrarPopup('Debes iniciar sesión con una cuenta registrada para ver tus transcripciones.', true);
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
   INICIALIZACIÓN AUTOMÁTICA
   Solo aplica si estamos en la página de consultas
------------------------------------------------ */
document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('transcripciones-tbody')) return;
    Transcripciones.cargarDesdeBackend();
});
