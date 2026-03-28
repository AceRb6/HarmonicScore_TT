/* ============================================
   VALIDACIÓN DE FORMULARIOS
   Lógica para registro, login y términos
   Proyecto: Harmonic Score
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
    inicializarToggleContrasena();
    inicializarTerminosCondiciones();
    inicializarValidacionRegistro();
    inicializarValidacionLogin();
    inicializarTerminosGlobal();
});

/**
 * Funcionalidad para mostrar/ocultar contraseña
 */
function inicializarToggleContrasena() {
    const toggles = document.querySelectorAll('.password-toggle');
    
    toggles.forEach(toggle => {
        toggle.addEventListener('click', () => {
            const input = toggle.previousElementSibling;
            if (input && input.type === 'password') {
                input.type = 'text';
                toggle.textContent = '🔒';
            } else if (input) {
                input.type = 'password';
                toggle.textContent = '👁️';
            }
        });
    });
}

/**
 * Lógica para el modal de Términos y Condiciones (Registro)
 */
function inicializarTerminosCondiciones() {
    const labelTerminos = document.getElementById('label-terminos');
    const modalTerminos = document.getElementById('modal-terminos');
    const cerrarTerminos = document.getElementById('cerrar-terminos');
    const scrollTerminos = document.getElementById('terminos-scroll');
    const btnAcepto = document.getElementById('btn-acepto');
    const btnNoAcepto = document.getElementById('btn-no-acepto');
    const checkboxTerminos = document.getElementById('checkbox-terminos');
    const btnRegistrar = document.getElementById('btn-registrar');

    if (!labelTerminos || !modalTerminos) return;

    // Abrir modal SOLO al hacer clic en el texto azul
    labelTerminos.addEventListener('click', (e) => {
        e.preventDefault();
        modalTerminos.classList.add('activo');
        scrollTerminos.scrollTop = 0;
        btnAcepto.disabled = true;
        btnAcepto.classList.add('btn-deshabilitado');
    });

    // Cerrar modal
    if (cerrarTerminos) {
        cerrarTerminos.addEventListener('click', () => {
            modalTerminos.classList.remove('activo');
        });
    }

    // Cerrar al hacer clic fuera
    modalTerminos.addEventListener('click', (e) => {
        if (e.target === modalTerminos) {
            modalTerminos.classList.remove('activo');
        }
    });

    // Detectar scroll hasta el final
    if (scrollTerminos) {
        scrollTerminos.addEventListener('scroll', () => {
            const { scrollTop, scrollHeight, clientHeight } = scrollTerminos;
            if (scrollTop + clientHeight >= scrollHeight - 10) {
                btnAcepto.disabled = false;
                btnAcepto.classList.remove('btn-deshabilitado');
            }
        });
    }

    // Botón No Acepto
    if (btnNoAcepto) {
        btnNoAcepto.addEventListener('click', () => {
            modalTerminos.classList.remove('activo');
            if (checkboxTerminos) checkboxTerminos.checked = false;
            if (btnRegistrar) {
                btnRegistrar.disabled = true;
                btnRegistrar.classList.add('btn-deshabilitado');
            }
        });
    }

    // Botón Acepto
    if (btnAcepto) {
        btnAcepto.addEventListener('click', () => {
            modalTerminos.classList.remove('activo');
            if (checkboxTerminos) checkboxTerminos.checked = true;
            if (btnRegistrar) {
                btnRegistrar.disabled = false;
                btnRegistrar.classList.remove('btn-deshabilitado');
            }
        });
    }

    // Si el checkbox se marca manualmente
    if (checkboxTerminos) {
        checkboxTerminos.addEventListener('change', () => {
            if (btnRegistrar) {
                if (checkboxTerminos.checked) {
                    btnRegistrar.disabled = false;
                    btnRegistrar.classList.remove('btn-deshabilitado');
                } else {
                    btnRegistrar.disabled = true;
                    btnRegistrar.classList.add('btn-deshabilitado');
                }
            }
        });
    }
}

/**
 * Lógica para términos globales (footer y otras páginas)
 */
function inicializarTerminosGlobal() {
    const modalGlobal = document.getElementById('modal-terminos-global');
    if (!modalGlobal) return;

    const cerrarGlobal = document.getElementById('cerrar-terminos-global');
    const btnAceptoGlobal = document.getElementById('btn-acepto-global');
    const btnNoAceptoGlobal = document.getElementById('btn-no-acepto-global');
    const scrollGlobal = document.getElementById('terminos-scroll-global');
    const footerTerminos = document.getElementById('footer-terminos');

    // Abrir desde footer
    if (footerTerminos) {
        footerTerminos.addEventListener('click', (e) => {
            e.preventDefault();
            modalGlobal.classList.add('activo');
        });
    }

    // Cerrar
    if (cerrarGlobal) {
        cerrarGlobal.addEventListener('click', () => {
            modalGlobal.classList.remove('activo');
        });
    }

    // Clic fuera
    modalGlobal.addEventListener('click', (e) => {
        if (e.target === modalGlobal) {
            modalGlobal.classList.remove('activo');
        }
    });

    // Scroll para habilitar botón
    if (scrollGlobal && btnAceptoGlobal) {
        scrollGlobal.addEventListener('scroll', () => {
            const { scrollTop, scrollHeight, clientHeight } = scrollGlobal;
            if (scrollTop + clientHeight >= scrollHeight - 10) {
                btnAceptoGlobal.disabled = false;
                btnAceptoGlobal.classList.remove('btn-deshabilitado');
            }
        });
    }

    // Botones
    if (btnNoAceptoGlobal) {
        btnNoAceptoGlobal.addEventListener('click', () => {
            modalGlobal.classList.remove('activo');
        });
    }

    if (btnAceptoGlobal) {
        btnAceptoGlobal.addEventListener('click', () => {
            modalGlobal.classList.remove('activo');
        });
    }
}

/**
 * Validación del formulario de registro
 */
function inicializarValidacionRegistro() {
    const formulario = document.getElementById('formulario-registro');
    if (!formulario) return;

    formulario.addEventListener('submit', (e) => {
        e.preventDefault();
        alert('Registro simulado exitoso. Redirigiendo a Login...');
        window.location.href = 'login.html';
    });
}

/**
 * Validación del formulario de login
 */
function inicializarValidacionLogin() {
    const formulario = document.getElementById('formulario-login');
    if (!formulario) return;

    formulario.addEventListener('submit', (e) => {
        e.preventDefault();
        alert('Inicio de sesión simulado exitoso. Redirigiendo a Carga...');
        window.location.href = 'carga.html';
    });
}