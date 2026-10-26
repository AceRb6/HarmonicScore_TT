/* ============================================
   TOAST - Notificaciones emergentes laterales
   Uso: Toast.exito('mensaje') / Toast.error('mensaje')
   Proyecto: Harmonic Score
   ============================================ */

const Toast = {
    DURACION_MS: 5000,

    _contenedor() {
        let c = document.getElementById('toast-contenedor');
        if (!c) {
            c = document.createElement('div');
            c.id = 'toast-contenedor';
            c.className = 'toast-contenedor';
            c.setAttribute('aria-live', 'polite');
            document.body.appendChild(c);
        }
        return c;
    },

    mostrar(mensaje, tipo = 'exito', duracion = Toast.DURACION_MS) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${tipo}`;
        toast.setAttribute('role', tipo === 'error' ? 'alert' : 'status');

        const icono = document.createElement('span');
        icono.className = 'toast-icono';
        icono.textContent = tipo === 'error' ? '✗' : '✓';

        const texto = document.createElement('span');
        texto.textContent = mensaje; // textContent: evita inyeccion de HTML

        const cerrar = document.createElement('button');
        cerrar.type = 'button';
        cerrar.className = 'toast-cerrar';
        cerrar.setAttribute('aria-label', 'Cerrar notificación');
        cerrar.textContent = '×';

        toast.append(icono, texto, cerrar);
        this._contenedor().appendChild(toast);

        // Animacion de entrada (siguiente frame para que aplique la transicion)
        requestAnimationFrame(() => requestAnimationFrame(() => toast.classList.add('visible')));

        const ocultar = () => {
            toast.classList.remove('visible');
            toast.addEventListener('transitionend', () => toast.remove(), { once: true });
            setTimeout(() => toast.remove(), 600); // respaldo si no hay transicion
        };
        const temporizador = setTimeout(ocultar, duracion);
        cerrar.addEventListener('click', () => { clearTimeout(temporizador); ocultar(); });
    },

    exito(mensaje, duracion) { this.mostrar(mensaje, 'exito', duracion); },
    error(mensaje, duracion) { this.mostrar(mensaje, 'error', duracion); },
};

/* Aviso tras restablecer la contrasena (login.html?recuperado=1) */
document.addEventListener('DOMContentLoaded', () => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('recuperado') === '1') {
        Toast.exito('Tu contraseña fue actualizada correctamente. Ya puedes iniciar sesión.', 7000);
        // Limpia el parametro para que no reaparezca al recargar
        history.replaceState(null, '', window.location.pathname);
    }
});
