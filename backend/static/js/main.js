/* ============================================
   PUNTO DE ENTRADA PRINCIPAL
   Inicialización general de la aplicación
   Proyecto: Harmonic Score
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
    console.log('Harmonic Score - Mockup Inicializado');
    console.log('Versión: 1.1 (Prototipo Visual)');
    console.log('Equipo: Arroyo Parra, Cano Portugal, Garcés Valencia');
    console.log('ESCOM-IPN 2026-B115');
    
    // Inicializaciones globales adicionales
    inicializarAnimaciones();
    restaurarAvisoModeloPendiente();
    inicializarModalLegalFooter();
    inicializarFondoAnimadoGlobal();
    inicializarTransicionesYBotones();
});

/**
 * Inicializa animaciones globales
 */
function inicializarAnimaciones() {
    // Agregar clase de animación a elementos al hacer scroll
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animado');
            }
        });
    }, { threshold: 0.1 });

    // Observar elementos con clase 'animar'
    document.querySelectorAll('.animar').forEach(el => {
        observer.observe(el);
    });
}

/**
 * Función utilitaria para formatear bytes a MB
 */
function formatearTamañoBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Función utilitaria para formatear duración
 */
function formatearDuracion(segundos) {
    const mins = Math.floor(segundos / 60);
    const secs = Math.floor(segundos % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Exportar funciones utilitarias
window.formatearTamañoBytes = formatearTamañoBytes;
window.formatearDuracion = formatearDuracion;

/* ============================================
   AVISO DE PRECISIÓN DEL MODELO (CU-05)
   Persiste entre carga.html -> consultas.html hasta
   que el usuario presione "X" o se cumplan 15 segundos.
   ============================================ */
const AVISO_MODELO_DURACION_MS = 15000;
const AVISO_MODELO_STORAGE_KEY = 'hs_aviso_modelo_expira';

function mostrarAvisoModelo(duracionRestanteMs) {
    const esNuevo = typeof duracionRestanteMs !== 'number';
    const duracion = esNuevo ? AVISO_MODELO_DURACION_MS : Math.max(0, duracionRestanteMs);
    if (duracion <= 0) {
        sessionStorage.removeItem(AVISO_MODELO_STORAGE_KEY);
        return;
    }

    if (esNuevo) {
        sessionStorage.setItem(AVISO_MODELO_STORAGE_KEY, String(Date.now() + AVISO_MODELO_DURACION_MS));
    }

    const anterior = document.getElementById('aviso-modelo');
    if (anterior) anterior.remove();

    const aviso = document.createElement('div');
    aviso.id = 'aviso-modelo';
    aviso.className = 'aviso-modelo';
    aviso.setAttribute('role', 'dialog');
    aviso.setAttribute('aria-live', 'polite');
    aviso.innerHTML = `
        <button type="button" class="aviso-modelo-cerrar" aria-label="Cerrar aviso">&times;</button>
        <h4 class="aviso-modelo-titulo">Gracias por usar Harmonic Score</h4>
        <p class="aviso-modelo-texto">Recuerda que nuestro modelo de transcripción automática puede presentar
        imprecisiones dependiendo de la dificultad de la pieza, la cantidad de instrumentos o el ruido de fondo
        en la grabación.</p>
        <div class="aviso-modelo-barra"></div>`;
    document.body.appendChild(aviso);

    const fraccionInicial = Math.min(1, Math.max(0, duracion / AVISO_MODELO_DURACION_MS));
    const barra = aviso.querySelector('.aviso-modelo-barra');
    if (barra && typeof barra.animate === 'function') {
        barra.animate(
            [{ transform: `scaleX(${fraccionInicial})` }, { transform: 'scaleX(0)' }],
            { duration: duracion, easing: 'linear', fill: 'forwards' }
        );
    }

    if (esNuevo) {
        requestAnimationFrame(() => requestAnimationFrame(() => aviso.classList.add('visible')));
    } else {
        aviso.classList.add('visible');
    }

    let cerrado = false;
    const cerrar = () => {
        if (cerrado) return;
        cerrado = true;
        clearTimeout(temporizador);
        sessionStorage.removeItem(AVISO_MODELO_STORAGE_KEY);
        aviso.classList.remove('visible');
        setTimeout(() => aviso.remove(), 400);
    };
    const temporizador = setTimeout(cerrar, duracion);
    aviso.querySelector('.aviso-modelo-cerrar').addEventListener('click', cerrar);
}

function restaurarAvisoModeloPendiente() {
    const expira = Number(sessionStorage.getItem(AVISO_MODELO_STORAGE_KEY) || 0);
    if (!expira) return;
    const restante = expira - Date.now();
    if (restante > 250) {
        mostrarAvisoModelo(restante);
    } else {
        sessionStorage.removeItem(AVISO_MODELO_STORAGE_KEY);
    }
}

window.mostrarAvisoModelo = mostrarAvisoModelo;

/* ============================================
   POP-UP DE AVISO DE PRIVACIDAD Y TÉRMINOS EN FOOTER
   Muestra el contenido legal del registro y se cierra
   haciendo clic en cualquier lado.
   ============================================ */
function inicializarModalLegalFooter() {
    let modalFondo = document.getElementById('modal-legal-footer');
    if (!modalFondo) {
        modalFondo = document.createElement('div');
        modalFondo.id = 'modal-legal-footer';
        modalFondo.className = 'modal-fondo';
        modalFondo.style.cursor = 'pointer';
        modalFondo.innerHTML = `
            <div class="modal-contenido" style="cursor: pointer;">
                <button type="button" class="modal-cerrar" aria-label="Cerrar">&times;</button>
                <h3 class="modal-titulo" id="modal-legal-footer-titulo">Aviso de privacidad</h3>
                <div class="terminos-contenido" id="modal-legal-footer-scroll" style="cursor: default;">
                    <div class="terminos-texto" style="cursor: pointer;">
                        <p><strong>1. ACEPTACIÓN DE TÉRMINOS</strong></p>
                        <p>Al registrarse en Harmonic Score, usted acepta los términos y condiciones establecidos en este documento. Si no está de acuerdo con alguno de los términos, no debe utilizar este servicio.</p>
                        <br>
                        <p><strong>2. USO DEL SERVICIO</strong></p>
                        <p>Harmonic Score es una herramienta gratuita destinada exclusivamente para fines educativos y de investigación. Queda prohibido el uso comercial sin autorización previa.</p>
                        <br>
                        <p><strong>3. PROPIEDAD INTELECTUAL</strong></p>
                        <p>Los usuarios conservan todos los derechos sobre sus grabaciones de audio. Harmonic Score solo procesa temporalmente los archivos para generar la transcripción.</p>
                        <br>
                        <p><strong>4. PRIVACIDAD DE DATOS</strong></p>
                        <p>Los datos personales proporcionados durante el registro serán tratados conforme a la Ley Federal de Protección de Datos Personales. Los archivos de audio se eliminan automáticamente después de 30 días.</p>
                        <br>
                        <p><strong>5. LIMITACIÓN DE RESPONSABILIDAD</strong></p>
                        <p>Harmonic Score proporciona el servicio "tal cual" sin garantías de precisión absoluta. Los usuarios son responsables de verificar la exactitud de las transcripciones generadas.</p>
                        <br>
                        <p><strong>6. PROPIEDAD INTELECTUAL DEL SOFTWARE</strong></p>
                        <p>El código fuente de Harmonic Score está disponible bajo licencia MIT. Los usuarios pueden consultar, modificar y distribuir el código conforme a los términos de dicha licencia.</p>
                        <br>
                        <p><strong>7. MODIFICACIONES AL SERVICIO</strong></p>
                        <p>El equipo de desarrollo se reserva el derecho de modificar o discontinuar el servicio en cualquier momento, notificando previamente a los usuarios registrados.</p>
                        <br>
                        <p><strong>8. LEGISLACIÓN APLICABLE</strong></p>
                        <p>Este servicio se rige por las leyes mexicanas, incluyendo la Ley Federal de Derechos de Autor y la Ley Federal de Protección de Datos Personales en Posesión de los Particulares.</p>
                        <br>
                        <p><strong>9. CONTACTO</strong></p>
                        <p>Para cualquier duda o aclaración sobre estos términos, puede contactar al equipo de desarrollo a través del correo electrónico proporcionado en el pie de página.</p>
                        <br>
                        <p><strong>10. ACEPTACIÓN FINAL</strong></p>
                        <p>Al hacer scroll hasta el final de este documento y marcar la casilla de aceptación, usted confirma haber leído y comprendido todos los términos establecidos.</p>
                    </div>
                </div>
                <p style="text-align: center; font-size: 0.9rem; color: var(--color-texto-secundario); margin: 0.5rem 0 0 0;">
                    Haz clic en cualquier lugar para cerrar esta ventana
                </p>
            </div>
        `;
        document.body.appendChild(modalFondo);

        // Cerrar al hacer clic en cualquier lado (excepto si arrastra la barra de scroll)
        modalFondo.addEventListener('click', (e) => {
            const scrollEl = document.getElementById('modal-legal-footer-scroll');
            if (scrollEl && e.target === scrollEl && e.offsetX > scrollEl.clientWidth) {
                return;
            }
            modalFondo.classList.remove('activo');
        });

        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modalFondo.classList.contains('activo')) {
                modalFondo.classList.remove('activo');
            }
        });
    }

    const abrirModalLegal = (titulo) => {
        const tituloEl = document.getElementById('modal-legal-footer-titulo');
        const scrollEl = document.getElementById('modal-legal-footer-scroll');
        if (tituloEl) tituloEl.textContent = titulo;
        if (scrollEl) scrollEl.scrollTop = 0;
        modalFondo.classList.add('activo');
    };

    document.querySelectorAll('.footer a').forEach(enlace => {
        const texto = (enlace.textContent || '').trim().toLowerCase();
        if (texto.includes('aviso de privacidad') || enlace.id === 'footer-privacidad') {
            enlace.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                abrirModalLegal('Aviso de privacidad');
            });
        } else if (texto.includes('términos') || texto.includes('terminos') || enlace.id === 'footer-terminos') {
            enlace.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                abrirModalLegal('Términos y condiciones');
            });
        }
    });
}

/* ============================================
   ANIMACIONES DE FONDO EN EL RESTO DE VISTAS
   Inyecta la cascada de notas musicales grandes y las
   ondas acústicas con velocidad más lenta y pausada.
   ============================================ */
function inicializarFondoAnimadoGlobal() {
    if (document.querySelector('.hs-lluvia-notas')) return;

    const lluvia = document.createElement('div');
    lluvia.className = 'hs-lluvia-notas hs-animacion-lenta';
    lluvia.setAttribute('aria-hidden', 'true');
    lluvia.innerHTML = `
        <span class="hs-nota-cayendo" style="--x:4%;--tam:3.2rem;--dur:21s;--ret:0s;--op:0.42">&#9833;</span>
        <span class="hs-nota-cayendo" style="--x:11%;--tam:4.1rem;--dur:25s;--ret:-5s;--op:0.38">&#9834;</span>
        <span class="hs-nota-cayendo" style="--x:18%;--tam:3.4rem;--dur:19s;--ret:-11s;--op:0.46">&#9835;</span>
        <span class="hs-nota-cayendo" style="--x:26%;--tam:4.5rem;--dur:27s;--ret:-3s;--op:0.35">&#9836;</span>
        <span class="hs-nota-cayendo" style="--x:34%;--tam:3.0rem;--dur:18s;--ret:-8s;--op:0.44">&#9834;</span>
        <span class="hs-nota-cayendo" style="--x:42%;--tam:3.9rem;--dur:23s;--ret:-14s;--op:0.40">&#9835;</span>
        <span class="hs-nota-cayendo" style="--x:50%;--tam:3.3rem;--dur:20s;--ret:-2s;--op:0.45">&#9833;</span>
        <span class="hs-nota-cayendo" style="--x:58%;--tam:4.4rem;--dur:26s;--ret:-9s;--op:0.36">&#9836;</span>
        <span class="hs-nota-cayendo" style="--x:66%;--tam:3.5rem;--dur:22s;--ret:-16s;--op:0.42">&#9834;</span>
        <span class="hs-nota-cayendo" style="--x:74%;--tam:4.6rem;--dur:28s;--ret:-6s;--op:0.34">&#9835;</span>
        <span class="hs-nota-cayendo" style="--x:82%;--tam:3.1rem;--dur:19.5s;--ret:-12s;--op:0.46">&#9833;</span>
        <span class="hs-nota-cayendo" style="--x:89%;--tam:3.8rem;--dur:24s;--ret:-4s;--op:0.40">&#9836;</span>
        <span class="hs-nota-cayendo" style="--x:95%;--tam:3.3rem;--dur:21.5s;--ret:-10s;--op:0.42">&#9834;</span>
    `;
    document.body.prepend(lluvia);

    const ondasSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    ondasSvg.setAttribute('class', 'hs-ondas-acusticas-bg hs-animacion-lenta');
    ondasSvg.setAttribute('viewBox', '0 0 1440 320');
    ondasSvg.setAttribute('preserveAspectRatio', 'none');
    ondasSvg.setAttribute('aria-hidden', 'true');
    ondasSvg.innerHTML = `
        <path class="hs-onda-linea hs-onda-1" d="M0,160 C320,60 640,260 960,150 C1200,70 1340,210 1440,140" fill="none"/>
        <path class="hs-onda-linea hs-onda-2" d="M0,210 C280,290 620,80 980,200 C1220,280 1360,110 1440,190" fill="none"/>
        <path class="hs-onda-linea hs-onda-3" d="M0,110 C360,220 720,40 1080,170 C1260,230 1380,90 1440,120" fill="none"/>
    `;
    document.body.prepend(ondasSvg);
}

/* ============================================
   TRANSICIONES ENTRE PESTAÑAS Y ONDA EN BOTONES
   ============================================ */
function inicializarTransicionesYBotones() {
    // 1. Onda luminosa exacta en el punto de clic para todos los botones
    document.addEventListener('pointerdown', (e) => {
        const btn = e.target.closest('.btn, .hs-btn-principal, .hs-btn-secundario, .header-nav a, .hs-tab-inst, .btn-restaurar-audio, .btn-play-circular');
        if (!btn || btn.disabled) return;

        const rect = btn.getBoundingClientRect();
        const tam = Math.max(rect.width, rect.height);
        const onda = document.createElement('span');
        onda.className = 'hs-onda-clic';
        onda.style.width = onda.style.height = `${tam}px`;
        onda.style.left = `${e.clientX - rect.left - tam / 2}px`;
        onda.style.top = `${e.clientY - rect.top - tam / 2}px`;
        btn.appendChild(onda);
        setTimeout(() => onda.remove(), 600);
    });

    // 2. Barra luminosa superior y transición suave al cambiar de pestaña
    const barraTop = document.createElement('div');
    barraTop.className = 'hs-barra-transicion-top';
    document.body.appendChild(barraTop);

    document.querySelectorAll('.header-nav a, .hs-btn-principal, .hs-btn-secundario').forEach(enlace => {
        enlace.addEventListener('click', (e) => {
            const href = enlace.getAttribute('href');
            if (!href || href.startsWith('#') || href.startsWith('javascript:') || e.ctrlKey || e.metaKey || e.shiftKey || e.defaultPrevented) {
                return;
            }
            barraTop.style.width = '85%';
        });
    });

    // 3. Calcular el vector exacto (--hs-dx, --hs-dy) desde el centro inferior
    //    de la pantalla (50vw, 95vh) hacia la posición final de cada elemento
    inicializarSalidaCentroInferior();
}

function inicializarSalidaCentroInferior() {
    const selectores = [
        '.header-logo',
        '.header-nav ul li',
        '.hs-eyebrow',
        '.hs-hero-titulo',
        '.hs-hero-descripcion',
        '.hs-panel-usuario-activo',
        '.hs-hero-acciones',
        '.hs-metricas-bar .hs-metrica-pill',
        '.hs-consola-card',
        '.hs-encabezado-seccion',
        '.hs-beneficio-card',
        '.hs-paso-card',
        '.hs-tutorial-fila',
        '.hs-ondas-divisor',
        '.hs-cta-caja',
        '.workspace-left > div:first-child h2',
        '#badge-estado-audio',
        '.spectrogram-card',
        '.delimitation-card',
        '.controles-reproduccion-circular',
        '.workspace-right .card',
        '#btn-transcribir',
        '.contenedor-pagina',
        '.login-image-side',
        '.formulario-contenedor'
    ].join(', ');

    const elementos = Array.from(document.querySelectorAll(selectores));
    if (!elementos.length) return;

    // Pausar temporalmente la animación para medir la posición real final en pantalla
    elementos.forEach(el => {
        el.style.animation = 'none';
    });

    const origenX = window.innerWidth / 2;
    const origenY = window.innerHeight * 0.96;

    elementos.forEach(el => {
        const rect = el.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0) {
            el.style.animation = '';
            return;
        }
        const centroX = rect.left + rect.width / 2;
        const centroY = Math.min(rect.top + rect.height / 2, window.innerHeight * 0.55);
        const dx = Math.round(origenX - centroX);
        const dy = Math.round(Math.max(240, origenY - centroY));
        el.style.setProperty('--hs-dx', `${dx}px`);
        el.style.setProperty('--hs-dy', `${dy}px`);
    });

    // Forzar reflow y reactivar las animaciones escalonadas desde el centro inferior
    void document.body.offsetHeight;
    elementos.forEach(el => {
        el.style.animation = '';
    });
}