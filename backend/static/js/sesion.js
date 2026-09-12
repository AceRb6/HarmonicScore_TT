/* ============================================
   GESTIÓN DE SESIÓN ACTIVA
   Persiste sesión en localStorage, inyecta
   el widget de usuario en el header y
   gestiona el cierre de sesión.
   Proyecto: Harmonic Score
   ============================================ */

const Sesion = {
    KEYS: {
        USERNAME: 'hs_username',
        TOKEN:    'hs_token',
        LOGGEDIN: 'hs_logged_in'
    },

    /** Guarda los datos de la sesión en localStorage */
    iniciar(username, token = '') {
        localStorage.setItem(this.KEYS.USERNAME, username);
        localStorage.setItem(this.KEYS.TOKEN,    token);
        localStorage.setItem(this.KEYS.LOGGEDIN, 'true');
    },

    /** Elimina todos los datos y redirige al login */
    cerrar() {
        localStorage.removeItem(this.KEYS.USERNAME);
        localStorage.removeItem(this.KEYS.TOKEN);
        localStorage.removeItem(this.KEYS.LOGGEDIN);
        window.location.href = 'login.html';
    },

    /** Devuelve true si hay sesión activa */
    estaActiva() {
        return localStorage.getItem(this.KEYS.LOGGEDIN) === 'true';
    },

    /** Devuelve el nombre de usuario almacenado */
    obtenerUsuario() {
        return localStorage.getItem(this.KEYS.USERNAME) || '';
    },

    /** Devuelve el token almacenado */
    obtenerToken() {
        return localStorage.getItem(this.KEYS.TOKEN) || '';
    }
};

/* ------------------------------------------------
   WIDGET DE USUARIO EN HEADER
   Se inyecta dinámicamente en todas las páginas
------------------------------------------------ */

function renderizarWidgetSesion() {
    // Buscar la lista de enlaces del header
    const navUl = document.querySelector('.header-nav ul');
    if (!navUl) return;

    // Eliminar widget previo si existe (evita duplicados)
    const previo = document.getElementById('widget-sesion');
    if (previo) previo.remove();

    if (!Sesion.estaActiva()) return; // No hay sesión, no mostrar nada

    const username = Sesion.obtenerUsuario();

    // Crear el widget como un item de lista para la nav
    const widget = document.createElement('li');
    widget.id = 'widget-sesion';
    widget.innerHTML = `
        <div class="sesion-usuario-btn" id="sesion-usuario-btn">
            <span class="sesion-icono">👤</span>
            <span class="sesion-nombre">${username}</span>
        </div>
        <div class="sesion-dropdown" id="sesion-dropdown">
            <button class="btn-cerrar-sesion" id="btn-cerrar-sesion">
                🚪 Cerrar sesión
            </button>
        </div>
    `;

    // Insertar el widget al final (top-right)
    navUl.appendChild(widget);

    // Evento: cerrar sesión
    document.getElementById('btn-cerrar-sesion').addEventListener('click', () => {
        Sesion.cerrar();
    });

    // Mostrar/ocultar dropdown al hacer hover con mouse
    const btn = document.getElementById('sesion-usuario-btn');
    const dropdown = document.getElementById('sesion-dropdown');

    widget.addEventListener('mouseenter', () => {
        dropdown.classList.add('visible');
    });
    widget.addEventListener('mouseleave', () => {
        dropdown.classList.remove('visible');
    });
}

/* ------------------------------------------------
   OCULTAR LINKS DE NAV CUANDO HAY SESIÓN ACTIVA
   Esconde 'Registrarse' e 'Iniciar Sesión'
   del menú de navegación superior.
------------------------------------------------ */
function ocultarNavSesion() {
    if (!Sesion.estaActiva()) return;

    // Buscar todos los enlaces del nav del header
    const navLinks = document.querySelectorAll('.header-nav a');
    navLinks.forEach(link => {
        const texto = link.textContent.trim().toLowerCase();
        if (texto.includes('registrarse') || texto.includes('iniciar sesi')) {
            link.parentElement.style.display = 'none'; // Ocultar el <li>
        }
    });
}

/* ------------------------------------------------
   ESTILOS DEL WIDGET (Inyectados dinámicamente)
------------------------------------------------ */
function inyectarEstilosSesion() {
    if (document.getElementById('estilos-sesion')) return; // Ya inyectado
    const style = document.createElement('style');
    style.id = 'estilos-sesion';
    style.textContent = `
        /* Contenedor del widget de sesión posicionado a la derecha */
        #widget-sesion {
            position: relative;
            display: inline-flex;
            flex-direction: column;
            align-items: flex-end;
            margin-left: 8px;
        }

        /* Botón que muestra el icono + nombre */
        .sesion-usuario-btn {
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(255, 255, 255, 0.15);
            backdrop-filter: blur(6px);
            border: 1.5px solid rgba(255,255,255,0.35);
            border-radius: 50px;
            padding: 6px 14px 6px 10px;
            cursor: pointer;
            transition: background 0.2s, box-shadow 0.2s;
            box-shadow: 0 2px 8px rgba(0,0,0,0.12);
        }

        .sesion-usuario-btn:hover,
        #widget-sesion:hover .sesion-usuario-btn {
            background: rgba(255,255,255,0.28);
            box-shadow: 0 4px 16px rgba(0,0,0,0.18);
        }

        .sesion-icono {
            font-size: 1.35rem;
            line-height: 1;
        }

        .sesion-nombre {
            font-size: 0.95rem;
            font-weight: 700;
            color: #fff;
            letter-spacing: 0.01em;
            max-width: 150px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }

        /* Dropdown (oculto por defecto, visible al hacer hover) */
        .sesion-dropdown {
            position: absolute;
            top: calc(100% + 5px);
            right: 0;
            display: flex;
            flex-direction: column;
            background: #fff;
            border-radius: 10px;
            box-shadow: 0 6px 24px rgba(0,0,0,0.16);
            overflow: hidden;
            opacity: 0;
            pointer-events: none;
            transform: translateY(-6px);
            transition: opacity 0.18s, transform 0.18s;
            min-width: 160px;
            z-index: 9999;
        }

        .sesion-dropdown.visible {
            opacity: 1;
            pointer-events: auto;
            transform: translateY(0);
        }

        /* Botón de cerrar sesión */
        .btn-cerrar-sesion {
            background: none;
            border: none;
            padding: 12px 18px;
            font-size: 0.95rem;
            font-weight: 600;
            color: #c62828;
            cursor: pointer;
            text-align: left;
            transition: background 0.15s, color 0.15s;
            white-space: nowrap;
        }

        .btn-cerrar-sesion:hover {
            background: #ffebee;
            color: #b71c1c;
        }
    `;
    document.head.appendChild(style);
}

/* ------------------------------------------------
   PROTECCIÓN DE BOTONES PARA INVITADOS
   Si no hay sesión activa, intercepta los botones
   de acción y redirige a login.html
------------------------------------------------ */
function protegerBotonesInvitado() {
    // Solo actúa si el usuario ES invitado
    if (Sesion.estaActiva()) return;

    /**
     * Envuelve un elemento para que, al hacer clic,
     * redirija a login en lugar de ejecutar su acción.
     */
    function bloquear(selector, usarCapture = false) {
        const elementos = document.querySelectorAll(selector);
        elementos.forEach(el => {
            el.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopImmediatePropagation();
                window.location.href = 'login.html';
            }, usarCapture);
        });
    }

    // ── PÁGINA: TRANSCRIBIR (carga.html) ─────────────────────
    // Botón "Cargar Archivo"
    bloquear('#btn-examinar', true);
    // Drop zone (arrastrar archivo)
    bloquear('#drop-zone', true);
    // Botón "Reproducir Selección"
    bloquear('#btn-play', true);
    // Botón "Transcribir"
    bloquear('#btn-transcribir', true);

    // ── PÁGINA: TRANSCRIPCIONES (consultas.html) ─────────────
    // Cualquier botón o enlace dentro de la card de la tabla
    bloquear('#transcripciones-tabla-wrapper .btn', true);
    bloquear('#transcripciones-tabla-wrapper a',    true);
    // Botón "Transcribir ahora" del estado vacío (por si acaso)
    bloquear('#btn-ir-transcribir', true);
}

/* ------------------------------------------------
   INICIALIZACIÓN AUTOMÁTICA
------------------------------------------------ */
document.addEventListener('DOMContentLoaded', () => {
    inyectarEstilosSesion();
    renderizarWidgetSesion();
    ocultarNavSesion();
    protegerBotonesInvitado(); // Bloquea interacciones de usuarios no autenticados
});
