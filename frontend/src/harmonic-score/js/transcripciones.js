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
     * 2026-08-21: Descarga el PDF real generado por el backend.
     * Recibe la URL directa del PDF almacenado en /media/ del servidor Django.
     */
    descargarPDF(event, urlPdf) {
        event.preventDefault();

        // Redirigir a login si es invitado
        if (!Sesion.estaActiva()) {
            window.location.href = 'login.html';
            return;
        }

        // 2026-08-21: Si existe la URL real del PDF, abrir en nueva pestaña
        if (urlPdf && urlPdf !== 'null' && urlPdf !== '') {
            window.open(urlPdf, '_blank');
            this.mostrarPopup("Descarga iniciada", false);
        } else {
            this.mostrarPopup("El PDF aún no está disponible", true);
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

            // 2026-09-01: Estados en texto limpio sin símbolos ni emojis
            switch (item.estado) {
                case 'Finalizado':
                    estadoHtml   = `<td class="estado-exito">Finalizado</td>`;
                    // 2026-08-21: Usar la URL real del PDF devuelta por el backend
                    descargaHtml = `<td><a href="#" onclick="Transcripciones.descargarPDF(event, '${item.url_pdf || ''}')" class="btn btn-primario"
                                        style="padding: 0.25rem 0.75rem; font-size: 0.85rem;">
                                        PDF</a></td>`;
                    break;
                case 'Error en el procesamiento':
                    estadoHtml   = `<td class="estado-error">Error en el procesamiento</td>`;
                    descargaHtml = `<td><button class="btn btn-secundario" disabled 
                                        style="padding: 0.25rem 0.75rem; font-size: 0.85rem;">
                                        Fallo</button></td>`;
                    break;
                case 'En proceso':
                    estadoHtml   = `<td class="estado-proceso">En proceso</td>`;
                    descargaHtml = `<td><button class="btn btn-secundario" disabled 
                                        style="padding: 0.25rem 0.75rem; font-size: 0.85rem;">
                                        Procesando...</button></td>`;
                    break;
                default:
                    estadoHtml   = `<td>${item.estado}</td>`;
                    descargaHtml = `<td>-</td>`;
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
        // INVITADO: sin sesión activa → mostrar tabla de ejemplo
        if (!Sesion.estaActiva()) {
            this.renderizar([
                { titulo: '"1.mp3"',               fecha: '15/5/26',  estado: 'Finalizado' },
                { titulo: '"2.mp3"',               fecha: '10/6/26',  estado: 'Error en el procesamiento'       },
                { titulo: '"3.mp3"',               fecha: '11/6/26',  estado: 'En proceso'     },
                { titulo: '"ejercicio_piano.wav"',  fecha: '12/6/26',  estado: 'Finalizado' }
            ]);
            return;
        }

        // 2026-08-21: USUARIO AUTENTICADO — consultar el endpoint real del backend.
        // Se pasa el username del localStorage porque el login sigue siendo simulado.
        const username = Sesion.obtenerUsuario();
        try {
            const respuesta = await DjangoAPI.peticion(`/transcripciones/mis/?username=${encodeURIComponent(username)}`, 'GET');

            if (respuesta.ok && respuesta.data.transcripciones) {
                // 2026-08-21: Renderizar el historial real devuelto por Django
                this.renderizar(respuesta.data.transcripciones);
                this.mostrarPopup("Historial cargado", false);
            } else {
                // El backend respondió pero sin datos esperados
                this.renderizar([]);
                this.mostrarPopup("No se pudo cargar el historial", true);
            }
        } catch (e) {
            // 2026-08-21: Si el backend no responde, mostrar vacío con mensaje de error
            console.error('Error al cargar transcripciones:', e);
            this.renderizar([]);
            this.mostrarPopup("Error de conexión con el servidor", true);
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
