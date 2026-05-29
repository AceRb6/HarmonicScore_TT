# 🎵 Harmonic Score

Plataforma web moderna para transcripción y análisis de audio de alta calidad. Permite cargar archivos de audio, transcribir automáticamente y analizar características armónicas.

## 📋 Características

- ✅ **Autenticación de usuarios** - Registro e inicio de sesión seguros
- 🎧 **Transcripción de audio** - Conversión automática de audio a texto
- 📊 **Análisis armónico** - Identificación de estructuras armónicas
- 🌊 **Visualización de forma de onda** - Vista interactiva del audio con Wavesurfer.js
- 💾 **Gestión de transcripciones** - Almacenamiento y búsqueda de transcripciones
- 📥 **Descarga de resultados** - Exportar en múltiples formatos (TXT, JSON, CSV)
- 📱 **Diseño responsivo** - Interfaz optimizada para móviles y escritorio
- 🎨 **Interfaz moderna** - Diseño limpio basado en variables CSS personalizables

## 🗂️ Estructura del Proyecto

```
harmonic-score/
│
├── index.html                    # Página principal/Home
├── registro.html                 # Vista de registro de usuarios
├── login.html                    # Vista de inicio de sesión
├── carga.html                    # Vista para cargar y transcribir audio
├── consultas.html                # Vista de consulta de transcripciones
│
├── css/
│   ├── variables.css             # Variables globales (colores, fuentes, tamaños)
│   ├── reset.css                 # Reset y normalización CSS
│   ├── layout.css                # Estilos de header, footer, grid
│   ├── componentes.css           # Botones, formularios, tablas, cards
│   ├── wavesurfer-custom.css     # Estilos para visualización de audio
│   └── estilos.css               # Archivo principal que importa todos
│
├── js/
│   ├── config.js                 # Configuración global y constantes
│   ├── navigation.js             # Lógica de navegación entre vistas
│   ├── wavesurfer-setup.js       # Configuración de Wavesurfer.js
│   ├── transcripcion.js          # Lógica de transcripción
│   ├── validacion.js             # Validación de formularios
│   └── main.js                   # Archivo principal que inicializa todo
│
├── assets/
│   ├── img/
│   │   ├── logo-placeholder.png  # Logo del proyecto
│   │   └── favicon.ico           # Icono del navegador
│   │
│   └── audio/
│       └── demo.mp3              # Audio de ejemplo
│
└── README.md                      # Este archivo
```

## 🚀 Instalación y Configuración

### Requisitos previos
- Navegador web moderno (Chrome, Firefox, Safari, Edge)
- Conexión a internet (para usar la API)

### Pasos de instalación

1. **Clonar o descargar el proyecto**
```bash
git clone https://github.com/tuusuario/harmonic-score.git
cd harmonic-score
```

2. **Abrir en el navegador**
Simplemente abre `index.html` en tu navegador preferido o usa un servidor local:

```bash
# Con Python 3
python -m http.server 8000

# Con Node.js (http-server)
npx http-server

# Con PHP
php -S localhost:8000
```

Luego accede a `http://localhost:8000` en tu navegador.

## 💻 Estructura de Vistas

### Vista 1: Home (index.html)
- Página de bienvenida
- Información sobre la plataforma
- Botones de navegación a registro y login
- Características principales

### Vista 2: Registro (registro.html)
- Formulario de creación de cuenta
- Validación en tiempo real
- Término de servicio
- Link a página de login

### Vista 3: Login (login.html)
- Formulario de inicio de sesión
- Opción "Recuérdame"
- Link a recuperación de contraseña
- Link a página de registro

### Vista 4: Carga y Transcripción (carga.html)
- Carga de archivos de audio
- Vista previa con Wavesurfer.js
- Barra de progreso de transcripción
- Resultado de la transcripción

### Vista 5: Consultas de Transcripciones (consultas.html)
- Tabla de transcripciones guardadas
- Búsqueda y filtrado
- Vista detallada de cada transcripción
- Opciones de descarga y compartir

## 🎨 Sistema de Estilos

### Estructura CSS modular

El proyecto utiliza un sistema CSS modular organizado de la siguiente manera:

- **variables.css** - Todas las variables CSS globales (colores, espaciado, tipografía)
- **reset.css** - Reset de estilos del navegador y normalización
- **layout.css** - Estilos estructurales (header, footer, grid)
- **componentes.css** - Componentes reutilizables (botones, formularios, tablas)
- **wavesurfer-custom.css** - Estilos específicos para audio
- **estilos.css** - Archivo principal que importa todos los demás

### Variables CSS principales

```css
--color-primary: #6366f1      /* Indigo */
--color-secondary: #10b981    /* Verde */
--color-danger: #ef4444       /* Rojo */

--font-family: 'Segoe UI', sans-serif
--spacing-md: 1rem            /* 16px */
--radius-lg: 0.5rem           /* 8px */
```

## 🔧 Archivos JavaScript

### config.js
Configuración global, constantes y URLs de API.

**Funciones principales:**
- `getApiUrl()` - Obtiene URL completa del API
- `getAuthToken()` / `setAuthToken()` - Gestión de tokens
- `getUserData()` / `setUserData()` - Gestión de datos de usuario
- `showNotification()` - Mostrar notificaciones

### navigation.js
Gestión de navegación y vistas.

**Funciones principales:**
- `showSection()` - Mostrar una sección
- `navigate()` - Navegar a una URL
- `openDetail()` / `closeDetail()` - Abrir detalle de transcripción
- `loadTranscriptions()` - Cargar lista de transcripciones
- Funciones de búsqueda y filtrado

### main.js
Inicialización principal de la aplicación.

**Funciones principales:**
- `initializeApp()` - Inicializa toda la aplicación
- `checkAuthentication()` - Verifica estado de autenticación
- `setupGlobalEventListeners()` - Configura listeners globales
- `handleLogout()` - Cierra sesión

### validacion.js
Validación de formularios en tiempo real.

**Funciones principales:**
- `validateForm()` - Valida un formulario completo
- `validateEmail()`, `validatePassword()`, etc. - Validaciones específicas
- `setupRealTimeValidation()` - Configura validación en tiempo real
- `showValidationErrors()` - Muestra errores en formatos

### wavesurfer-setup.js
Configuración de Wavesurfer.js para visualización de audio.

**Funciones principales:**
- `initWavesurfer()` - Inicializa Wavesurfer
- `loadAudioFile()` - Carga un archivo de audio
- `playAudio()`, `pauseAudio()`, `togglePlayPause()` - Control de reproducción
- `setVolume()`, `setPlaybackRate()` - Controles de audio

### transcripcion.js
Lógica de transcripción (simulada para demostración).

**Funciones principales:**
- `handleAudioUpload()` - Procesa carga de audio
- `generateTranscription()` - Genera transcripción simulada
- `saveTranscription()` - Guarda en almacenamiento local
- `analyzeTranscription()` - Analiza contenido
- `exportTranscription()` - Exporta en diferentes formatos

## 🔐 Autenticación

### Flujo de autenticación

1. El usuario se registra en `registro.html`
2. Los datos se guardan en `localStorage`
3. El usuario inicia sesión en `login.html`
4. Se genera un token y se guarda en `localStorage`
5. Las vistas protegidas verifican el token
6. El usuario puede cerrar sesión desde cualquier página

### Almacenamiento local

```javascript
localStorage.harmonic_token          // Token de autenticación
localStorage.harmonic_user           // Datos del usuario
localStorage.harmonic_transcriptions // Lista de transcripciones
```

## 📊 Formatos de almacenamiento

### Estructura de transcripción

```javascript
{
    id: "trans_1234567890_abc123",
    title: "Mi primera transcripción",
    description: "Descripción de la transcripción",
    content: "Contenido transcrito del audio",
    date: "2024-01-15T10:30:00Z",
    duration: 120.5,  // en segundos
    status: "completada",  // pendiente, procesando, completada, error
    audioUrl: "blob:...",
    fileSize: 5242880,  // en bytes
    processedDate: "2024-01-15T10:35:00Z"
}
```

### Estructura de usuario

```javascript
{
    id: "user_123",
    nombre: "Juan Pérez",
    usuario: "juanperez",
    email: "juan@example.com",
    registerDate: "2024-01-01T00:00:00Z"
}
```

## 🔄 Funcionamiento de la transcripción

1. **Carga del archivo** (2 segundos)
   - Validación del formato
   - Validación del tamaño
   - Carga en Wavesurfer

2. **Procesamiento de audio** (3 segundos)
   - Análisis de señal
   - Extracción de características

3. **Transcripción** (4 segundos)
   - Conversión de audio a texto
   - Detección de entidades

4. **Finalización** (2 segundos)
   - Guardado en base de datos
   - Generación de reportes

**Nota:** En la versión actual, la transcripción es simulada. Para usar transcripción real, integra una API como Google Cloud Speech-to-Text, AWS Transcribe o similar.

## 📱 Responsividad

El diseño es completamente responsivo:
- **Desktop** (1200px+) - 2 columnas, navegación horizontal
- **Tablet** (768px - 1199px) - 1-2 columnas adaptables
- **Móvil** (< 768px) - 1 columna, navegación simplificada

## 🌐 URLs y Endpoints

### Endpoints del API (configurables en config.js)

```javascript
CONFIG.API_BASE_URL = 'https://api.harmonicscore.com'
CONFIG.ENDPOINTS = {
    register: '/auth/register',
    login: '/auth/login',
    logout: '/auth/logout',
    transcriptions: '/transcriptions',
    upload: '/upload',
    process: '/process'
}
```

## 🛠️ Desarrollo

### Modo Debug

Accede con `?debug=true` para activar modo debug:
```
http://localhost:8000/?debug=true
```

En esto se exponen objetos para debugging en la consola:
- `APP_CONFIG` - Configuración
- `APP_CONSTANTS` - Constantes
- `APP_DEBUG` - Utilidades de debug

### Logging

Todas las acciones importantes se registran en la consola:
```javascript
logEvent('nombre_evento', { datos: 'adicionales' });
```

## 🔄 Integración de API

Para integrar con una API real:

1. **Configura los endpoints en config.js**
2. **Actualiza las funciones de fetch en cada módulo**
3. **Maneja errores y timeouts apropiadamente**

Ejemplo de integración:

```javascript
async function uploadAudio(file) {
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch(getApiUrl('/upload'), {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            },
            body: formData
        });
        
        if (!response.ok) throw new Error('Error en carga');
        return await response.json();
    } catch (error) {
        showNotification('Error al cargar archivo', 'error');
    }
}
```

## 📦 Dependencias externas

El proyecto usa las siguientes librerías (opcionales):
- **Wavesurfer.js** - Visualización de audio
- **Font Awesome** - Iconos (opcional)
- **Smooth Scroll** - Scroll suave (nativo en navegadores modernos)

## 🐛 Solución de problemas

### El audio no carga
- Verifica que el formato sea MP3, WAV, OGG o M4A
- Comprueba el tamaño del archivo (máximo 100MB)
- Abre la consola (F12) para ver mensajes de error

### Validación no funciona
- Asegúrate que los campos tengan atributos `name` correctos
- Verifica que `validacion.js` esté cargado antes del formulario
- Comprueba la consola para mensajes de error

### Transcripción no aparece
- Comprueba que el navegador tenga almacenamiento local habilitado
- Abre DevTools > Storage > localStorage
- Verifica que `harmonic_transcriptions` existe y tiene datos

## 📝 Notas de seguridad

> ⚠️ **IMPORTANTE:** Este proyecto es una demostración. Para producción:
>
> - Usa HTTPS siempre
> - Valida datos en el servidor
> - No guardes tokens en localStorage (usa httpOnly cookies)
> - Implementa CSRF protection
> - Sanitiza entrada de usuarios
> - Usa variables de entorno para configuración sensible

## 📄 Licencia

Este proyecto está bajo licencia MIT. Ver `LICENSE` para más detalles.

## 👥 Contribuciones

Las contribuciones son bienvenidas. Abre un issue o pull request para sugerir mejoras.

## 📞 Soporte

Para reportar bugs o pedir features, contacta a:
- Email: soporte@harmonicscore.com
- Issues: [GitHub Issues](https://github.com/tuusuario/harmonic-score/issues)

## 🎓 Recursos útiles

- [MDN Web Docs](https://developer.mozilla.org/)
- [Wavesurfer.js Docs](https://wavesurfer-js.org/)
- [CSS Variables](https://developer.mozilla.org/en-US/docs/Web/CSS/--*)
- [Web Audio API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Audio_API)

---

**Versión:** 1.0.0  
**Última actualización:** Enero 2024  
**Estado:** Desarrollo
