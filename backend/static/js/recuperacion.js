/* ============================================
   RECUPERACION - Nueva contraseña (CU-03)
   Validación en vivo de los requisitos. El backend
   vuelve a validar todo (incluida la lista de
   contraseñas comunes) antes de guardar.
   Proyecto: Harmonic Score
   ============================================ */
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('formulario-recuperacion');
    if (!form) return;

    const pass = document.getElementById('nueva-contrasena');
    const conf = document.getElementById('confirmar-nueva-contrasena');
    const lista = document.getElementById('requisitos-contrasena');

    // Muestra mínima de contraseñas comunes; la validación completa ocurre en el servidor
    const COMUNES = ['password', 'contraseña', 'contrasena', '12345678', '123456789', 'qwerty123',
                     'password1', 'admin123', 'iloveyou', 'harmonicscore'];

    const reglas = {
        'longitud':        (p) => p.length >= 8,
        'mayuscula':       (p) => /[A-Z]/.test(p),
        'minuscula':       (p) => /[a-z]/.test(p),
        'numero':          (p) => /\d/.test(p),
        'simbolo':         (p) => /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/.test(p),
        'comun':           (p) => p.length > 0 && !COMUNES.some(c => p.toLowerCase().replace(/[^a-z0-9ñ]/g, '') === c),
        'no-solo-numeros': (p) => p.length > 0 && !/^\d+$/.test(p),
        'coincide':        (p, c) => p.length > 0 && p === c,
    };

    const evaluar = () => {
        let todas = true;
        lista.querySelectorAll('li[data-regla]').forEach(li => {
            const ok = reglas[li.dataset.regla](pass.value, conf.value);
            li.classList.toggle('cumple', ok);
            if (!ok) todas = false;
        });
        return todas;
    };

    pass.addEventListener('input', evaluar);
    conf.addEventListener('input', evaluar);

    form.addEventListener('submit', (e) => {
        if (!evaluar()) {
            e.preventDefault();
            if (typeof Toast !== 'undefined') {
                Toast.error('La nueva contraseña no cumple con todos los requisitos.');
            }
            return;
        }
        const btn = document.getElementById('btn-aceptar-recuperacion');
        if (btn) { btn.disabled = true; btn.textContent = 'Guardando...'; }
    });
});
