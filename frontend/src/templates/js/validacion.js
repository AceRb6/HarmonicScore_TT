/* ============================================
   VALIDACIÓN DE FORMULARIOS
   Lógica para registro, login y términos
   Proyecto: Harmonic Score
   ============================================ */

// #--nuevo--
// Estado global del reCAPTCHA de REGISTRO
let captchaVerificado = false;
let captchaToken = '';

/**
 * Callback de Google para el captcha del REGISTRO
 */
function onRecaptchaSuccess(token) {
    captchaVerificado = true;
    captchaToken = token;
    const error = document.getElementById('captcha-error');
    if (error) error.style.display = 'none';
}

/**
 * Callback cuando el captcha de REGISTRO expira
 */
function onRecaptchaExpired() {
    captchaVerificado = false;
    captchaToken = '';
}

// Estado global del reCAPTCHA de LOGIN
let captchaLoginVerificado = false;
let captchaLoginToken = '';

/**
 * Callback de Google para el captcha del LOGIN
 */
function onRecaptchaLoginSuccess(token) {
    captchaLoginVerificado = true;
    captchaLoginToken = token;
    const error = document.getElementById('captcha-login-error');
    if (error) error.style.display = 'none';
}

/**
 * Callback cuando el captcha de LOGIN expira
 */
function onRecaptchaLoginExpired() {
    captchaLoginVerificado = false;
    captchaLoginToken = '';
}
// #-----------

document.addEventListener('DOMContentLoaded', () => {
    inicializarToggleContrasena();
    inicializarTerminosCondiciones();
    inicializarValidacionRegistro();
    inicializarValidacionLogin();
    inicializarTerminosGlobal();
    inicializarRecuperarContrasena(); // CU-03
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
    const mensajeContenedor = document.getElementById('mensaje-registro');
    if (!formulario) return;

    formulario.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const nombres = document.getElementById('nombres').value.trim();
        const apellidos = document.getElementById('apellidos').value.trim();
        const correo = document.getElementById('correo').value.trim();
        const usuario = document.getElementById('nombre-usuario').value.trim();
        const contrasena = document.getElementById('contrasena').value;
        const confirmarContrasena = document.getElementById('confirmar-contrasena').value;
        const terminos = document.getElementById('checkbox-terminos').checked;
        
        // Resetear visualización de mensaje
        if (mensajeContenedor) {
            mensajeContenedor.style.display = 'none';
        }
        
        const mostrarMensaje = (msn, esError) => {
            if (!mensajeContenedor) return;
            mensajeContenedor.textContent = msn;
            mensajeContenedor.style.display = 'block';
            mensajeContenedor.style.backgroundColor = esError ? '#ffebee' : '#e8f5e9';
            mensajeContenedor.style.color = esError ? '#c62828' : '#2e7d32';
            mensajeContenedor.style.border = `1px solid ${esError ? '#ef9a9a' : '#a5d6a7'}`;
        };

        // Validación de campos vacíos (por si HTML required falla)
        if (!nombres || !apellidos || !correo || !usuario || !contrasena || !confirmarContrasena || !terminos) {
            let camposFaltantes = [];
            if (!nombres) camposFaltantes.push("Nombres");
            if (!apellidos) camposFaltantes.push("Apellidos");
            if (!correo) camposFaltantes.push("Correo");
            if (!usuario) camposFaltantes.push("Usuario");
            if (!contrasena) camposFaltantes.push("Contraseña");
            mostrarMensaje(`Error al registrar cuenta: Faltan completar los siguientes campos (${camposFaltantes.join(', ')})`, true);
            return;
        }

        // Validación PCI-DSS: Mínimo 8 caracteres, 1 mayúscula, 1 símbolo especial
        // La expresión busca que exista al menos 1 mayúscula (?=.*[A-Z]), al menos 1 símbolo especial (?=.*[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]) y tenga longitud >= 8 (.{8,})
        const pciDssRegex = /^(?=.*[A-Z])(?=.*[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]).{8,}$/;
        if (!pciDssRegex.test(contrasena)) {
            mostrarMensaje('Error al registrar cuenta: La contraseña debe tener al menos 8 caracteres, 1 mayúscula y 1 símbolo especial.', true);
            return;
        }

        if (contrasena !== confirmarContrasena) {
            mostrarMensaje('Error al registrar cuenta: Las contraseñas no coinciden.', true);
            return;
        }

        // #--nuevo--
        // Validación del reCAPTCHA antes de continuar
        if (!captchaVerificado || !captchaToken) {
            const captchaError = document.getElementById('captcha-error');
            if (captchaError) captchaError.style.display = 'block';
            mostrarMensaje('Error al registrar cuenta: Completa la verificación reCAPTCHA.', true);
            return;
        }
        // #-----------

        // Consumo de la API centralizada para Django
        try {
            const formData = {
                first_name: nombres,
                last_name: apellidos,
                email: correo,
                username: usuario,
                password: contrasena,
                recaptcha_token: captchaToken  // #--nuevo-- Token del captcha para verificar en backend
            };

            // Consumo Real
            const respuesta = await DjangoAPI.registrarUsuario(formData);
            
            if (respuesta.ok) {
                 // Guardar internamente para la demostración el mapeo de correo a usuario
                 localStorage.setItem(`hs_demo_user_${correo}`, usuario);
                 mostrarMensaje('Cuenta registrada exitosamente', false); // msn1
                 setTimeout(() => { window.location.href = 'login.html'; }, 2000);
            } else if (respuesta.data && (respuesta.data.error === "correo_existente" || respuesta.data.email)) {
                 mostrarMensaje('Este correo ya está registrado', true); // msn3
            } else if (respuesta.data && respuesta.data.error === "usuario_existente") {
                 mostrarMensaje('Este nombre de usuario ya está registrado', true); 
            } else if (respuesta.data && respuesta.data.error === "captcha_invalido") {
                 mostrarMensaje('Error de verificación: El captcha no es válido. Intenta de nuevo.', true);
            } else {
                 mostrarMensaje('Error al registrar cuenta', true); // msn2
            }

        } catch (error) {
            mostrarMensaje(error.message || 'Error al registrar cuenta: Problema de conexión', true);
        }
    });
}

/**
 * Validación del formulario de login
 */
function inicializarValidacionLogin() {
    const formulario = document.getElementById('formulario-login');
    const mensajeContenedor = document.getElementById('mensaje-login');
    if (!formulario) return;

    const mostrarMensaje = (msn, esError) => {
        if (!mensajeContenedor) return;
        mensajeContenedor.textContent = msn;
        mensajeContenedor.style.display = 'block';
        mensajeContenedor.style.backgroundColor = esError ? '#ffebee' : '#e8f5e9';
        mensajeContenedor.style.color = esError ? '#c62828' : '#2e7d32';
        mensajeContenedor.style.border = `1px solid ${esError ? '#ef9a9a' : '#a5d6a7'}`;
    };

    formulario.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (mensajeContenedor) mensajeContenedor.style.display = 'none';

        // Campo actualizado a Correo (CU-02)
        const loginCorreo = document.getElementById('login-correo').value.trim();
        const loginContrasena = document.getElementById('login-contrasena').value;

        if (!loginCorreo || !loginContrasena) {
            mostrarMensaje('Correo o contraseña inválidos', true); // msn2
            return;
        }

        // Validar captcha de login
        if (!captchaLoginVerificado || !captchaLoginToken) {
            const captchaError = document.getElementById('captcha-login-error');
            if (captchaError) captchaError.style.display = 'block';
            mostrarMensaje('Error: Completa la verificación reCAPTCHA.', true);
            return;
        }

        try {
            const credenciales = {
                email: loginCorreo,
                password: loginContrasena,
                recaptcha_token: captchaLoginToken
            };

            /* 
            Activar cuando el endpoint de Django esté listo:
            const respuesta = await DjangoAPI.loginUsuario(credenciales);
            if (respuesta.ok) {
                const nombreUsuario = respuesta.data.username || '';
                mostrarMensaje(`Bienvenido, ${nombreUsuario}`, false); // msn1
                // Guardar sesión en localStorage usando el módulo Sesion
                Sesion.iniciar(nombreUsuario, respuesta.data.token || '');
                setTimeout(() => { window.location.href = 'index.html'; }, 1200); // Redirige al main
            } else {
                mostrarMensaje('Correo o contraseña inválidos', true); // msn2
            }
            */

            // --- Simulación de bienvenida ---
            // Usa primero el nombre registrado guardado para este correo, sino usa el prefijo del correo
            let nombreSimulado = localStorage.getItem(`hs_demo_user_${loginCorreo}`);
            if (!nombreSimulado) {
                nombreSimulado = loginCorreo.split('@')[0];
            }
            Sesion.iniciar(nombreSimulado, 'token-simulado'); // Guardar sesión en localStorage
            mostrarMensaje(`Bienvenido, ${nombreSimulado}`, false); // msn1
            setTimeout(() => { window.location.href = 'index.html'; }, 1200); // Redirige al main

        } catch (error) {
            mostrarMensaje('Ups, tenemos un problema desde nuestro lado', true); // msn3
        }
    });
}

/**
 * CU-03: Recuperar contraseña
 */
function inicializarRecuperarContrasena() {
    const formulario = document.getElementById('formulario-recuperar');
    const mensajeContenedor = document.getElementById('mensaje-recuperar');
    if (!formulario) return;

    const mostrarMensaje = (msn, esError) => {
        if (!mensajeContenedor) return;
        mensajeContenedor.textContent = msn;
        mensajeContenedor.style.display = 'block';
        mensajeContenedor.style.backgroundColor = esError ? '#ffebee' : '#e8f5e9';
        mensajeContenedor.style.color = esError ? '#c62828' : '#2e7d32';
        mensajeContenedor.style.border = `1px solid ${esError ? '#ef9a9a' : '#a5d6a7'}`;
    };

    formulario.addEventListener('submit', async (e) => {
        e.preventDefault();
        if (mensajeContenedor) mensajeContenedor.style.display = 'none';

        const correo = document.getElementById('recuperar-correo').value.trim();
        if (!correo) {
            mostrarMensaje('Error al recuperar contraseña: ingresa tu correo.', true); // msn2
            return;
        }

        const btnRecuperar = document.getElementById('btn-recuperar');
        if (btnRecuperar) {
            btnRecuperar.disabled = true;
            btnRecuperar.textContent = 'Enviando...';
        }

        try {
            // Llamada real al backend: verifica si el correo existe en la BD
            const respuesta = await DjangoAPI.peticion('/auth/recuperar-contrasena/', 'POST', { email: correo });

            if (respuesta.ok) {
                // msn1: el correo existe en la BD
                mostrarMensaje('Se ha enviado la recuperación a tu correo', false);
            } else if (respuesta.status === 404 || (respuesta.data && respuesta.data.error === 'correo_no_encontrado')) {
                // msn2: el correo no está registrado
                mostrarMensaje('Error al recuperar contraseña', true);
            } else {
                mostrarMensaje('Error al recuperar contraseña', true);
            }

        } catch (error) {
            mostrarMensaje('Error al recuperar contraseña', true);
        } finally {
            if (btnRecuperar) {
                btnRecuperar.disabled = false;
                btnRecuperar.textContent = 'Enviar enlace de recuperación';
            }
        }
    });
}