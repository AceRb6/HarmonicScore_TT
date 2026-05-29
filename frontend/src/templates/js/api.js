/* ============================================
   CLIENTE API DJANGO
   Módulo para gestionar peticiones al backend
   ============================================ */

/**
 * URL base del servidor Django local (Por defecto en puerto 8000)
 */
const API_BASE_URL = 'http://127.0.0.1:8000/api';

const DjangoAPI = {
    /**
     * Extrae el token CSRF de las cookies (Requerido por Django para métodos POST si se usa sesión)
     */
    obtenerCSRFToken: () => {
        const valor = `; ${document.cookie}`;
        const partes = valor.split(`; csrftoken=`);
        if (partes.length === 2) return partes.pop().split(';').shift();
        return '';
    },

    /**
     * Envoltorio para Fetch con configuración predeterminada
     */
    peticion: async (endpoint, metodo = 'GET', datos = null) => {
        const opciones = {
            method: metodo,
            headers: {
                'X-CSRFToken': DjangoAPI.obtenerCSRFToken()
            }
        };

        // Si no es FormData, enviamos como JSON
        if (!(datos instanceof FormData)) {
            opciones.headers['Content-Type'] = 'application/json';
        }

        if (datos && (metodo === 'POST' || metodo === 'PUT' || metodo === 'PATCH')) {
            if (datos instanceof FormData) {
                opciones.body = datos;
            } else {
                opciones.body = JSON.stringify(datos);
            }
        }

        try {
            const respuesta = await fetch(`${API_BASE_URL}${endpoint}`, opciones);
            const data = await respuesta.json().catch(() => ({})); // Captura si el servidor no devuelve JSON
            
            return {
                ok: respuesta.ok,
                status: respuesta.status,
                data: data
            };
        } catch (error) {
            console.error('Error conectando a Django:', error);
            throw new Error('Error de conexión con el servidor. Verifica que Django esté encendido.');
        }
    },

    /**
     * Registra un nuevo usuario en la base de datos
     * @param {Object} formData {first_name, last_name, email, username, password}
     */
    registrarUsuario: async (formData) => {
        return await DjangoAPI.peticion('/auth/registro/', 'POST', formData);
    },

    /**
     * Inicia sesión (Ejemplo futuro)
     */
    loginUsuario: async (credenciales) => {
        return await DjangoAPI.peticion('/auth/login/', 'POST', credenciales);
    }
};
