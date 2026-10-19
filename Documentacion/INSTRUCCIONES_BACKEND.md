# ANALISIS TECNICO Y MANUAL DE INTEGRACION - HARMONIC SCORE

Este documento presenta un analisis detallado de la arquitectura, componentes y protocolos de seguridad del proyecto Harmonic Score. Esta diseñado para orientar al desarrollador backend en la integracion de modelos de procesamiento de audio y el mantenimiento del sistema.

---

## 1. CONFIGURACION DEL ENTORNO Y RAIZ DEL PROYECTO

Los siguientes archivos definen el entorno de ejecucion y la configuracion base del area de trabajo.

- **.env**: Almacena variables de entorno sensibles, como claves secretas de Django y configuraciones de servicios externos.
- **.python-version**: Especifica la version exacta de Python requerida para garantizar la compatibilidad entre entornos de desarrollo.
- **docker-compose.yml**: Define la orquestacion de contenedores para el despliegue de servicios, facilitando la replicacion del entorno.
- **README.md**: Contiene las instrucciones iniciales de instalacion y una descripcion general del proposito del proyecto.
- **INSTRUCCIONES_BACKEND.md**: Documento de referencia tecnica para la capa de servicios y puntos de integracion.

---

## 2. ANALISIS DE LA CAPA DE PRESENTACION (FRONTEND-HTML)

La interfaz se compone de vistas independientes que gestionan el ciclo de vida del usuario y el procesamiento de datos.

- **index.html**: Funge como punto de entrada principal, proporcionando la estructura de navegacion global y la presentacion del servicio.
- **login.html**: Gestiona la captura de credenciales de acceso, integrando la biblioteca de Google reCAPTCHA para la prevencion de accesos automatizados.
- **registro.html**: Contiene la logica de captura de datos para nuevos usuarios, incluyendo validaciones visuales y la gestion de aceptacion de terminos legales.
- **carga.html**: Es el núcleo operativo del cliente; permite la seleccion de archivos de audio, su pre-visualizacion y el lanzamiento del proceso de transcripcion.
- **consultas.html**: Proporciona una interfaz de tabla para el seguimiento de piezas procesadas y el acceso a los archivos de salida (PDF/XML).
- **cuenta.html**: Espacio dedicado a la actualizacion de informacion de perfil y parametros de seguridad del usuario registrado.

---

## 3. ANALISIS PROFUNDO DE LA LOGICA DE CLIENTE (FRONTEND-JS)

Los archivos JavaScript estan organizados de manera modular para separar las responsabilidades de comunicacion, estado y procesamiento.

- **api.js**: Implementa un cliente HTTP centralizado basado en la API Fetch. Gestiona la inyeccion automatica del token X-CSRFToken extraido de las cookies para peticiones de escritura y detecta dinamicamente si el cuerpo de la peticion es binario (FormData) o textual (JSON).
- **sesion.js**: Administra el estado de autenticacion mediante persistencia en el almacenamiento local del navegador. Controla el redibujado del encabezado para mostrar opciones de cuenta e incluye un sistema de interceptacion que restringe interacciones a usuarios invitados.
- **wavesurfer-setup.js**: Gestiona el motor visual de ondas sonoras utilizando la libreria WaveSurfer.js. Ejecuta auditorias tecnicas sobre el archivo de audio (validacion de formato, tamaño maximo de 50MB y duracion maxima de 6 minutos) antes de permitir su subida.
- **transcripcion.js**: Coordina la comunicacion asincrona durante el proceso de transcripcion, gestionando las barras de progreso y el manejo de errores provenientes del backend de procesamiento de audio.
- **transcripciones.js**: Procesa la informacion recibida de la API para su despliegue en tablas dinamicas, manejando estados de exito o error y controlando los flujos de descarga segura de documentos musicales.
- **validacion.js**: Centraliza las reglas de integridad de datos en formularios, incluyendo el cumplimiento de estandares PCI-DSS para la complejidad de contraseñas y la verificacion del estado de los componentes reCAPTCHA.
- **config.js**: Punto central de configuracion que define parametros globales como la direccion base de la API y constantes de tiempo.
- **navigation.js**: Controla el enrutamiento interno y asegura que las redirecciones posteriores a eventos de sesion se realicen de manera coherente.
- **main.js**: Script base que inicializa los componentes compartidos y utilerias transversales de la interfaz de usuario.

---

## 4. ANALISIS DE ESTILOS Y DISEÑO (FRONTEND-CSS)

El sistema visual se basa en una arquitectura de separacion de intereses para facilitar el mantenimiento estetico.

- **reset.css**: Proporciona una base neutra eliminando las discrepancias de renderizado entre distintos navegadores web.
- **layout.css**: Define el sistema de rejillas, espaciados y la estructura responsiva que permite a la aplicacion adaptarse a diferentes resoluciones de pantalla.
- **componentes.css**: Contiene la definicion visual de elementos reutilizables como botones, modales, tarjetas y tablas, garantizando una identidad visual premium y consistente.

---

## 5. CAPA DE SERVICIOS Y SEGURIDAD (BACKEND)

El servidor esta construido sobre el framework Django, priorizando la estabilidad y la seguridad de la informacion.

- **manage.py**: Herramienta de administracion para la ejecucion del servidor, gestion de migraciones de datos y creacion de perfiles administrativos.
- **settings.py**: Especifica politicas de seguridad rigurosas, incluyendo listas blancas de CORS, proteccion contra ataques CSRF y la configuracion de la base de datos central.
- **urls.py**: Mapea los puntos de entrada de la API REST hacia sus respectivas funciones de gestion en la capa de vistas.
- **views.py**: Implementa los controladores de la API. En este archivo se encuentran los puntos de integracion marcados para la sustitucion de simulaciones por inferencias reales de modelos de inteligencia artificial.
- **db.sqlite3**: Motor de base de datos relacional ligero utilizado para la persistencia de usuarios y registros operativos.
- **requirements.txt**: Documenta el ecosistema de dependencias necesario para la ejecucion integra del entorno backend.

### Protocolo de Seguridad SHA-256
La plataforma emplea el estandar industrial SHA-256 para el resguardo de credenciales. Durante el registro, Django genera un Hash unico mediante un proceso de salting aleatorio, asegurando que las contraseñas originales nunca se almacenen en texto plano. Este protocolo protege la integridad de las cuentas incluso en escenarios de compromiso de la base de datos.

---

## 6. GUIA PARA LA CONTINUIDAD DEL DESARROLLO

1. **Entorno**: Se requiere la activacion del entorno virtual ubicado en `.venv` para ejecutar el servidor.
2. **Integracion ML**: El desarrollador backend debe localizar en `views.py` el endpoint de subida de transcripcion y reemplazar la logica de espera simulada por la llamada al script de inferencia del modelo YourMT3.
3. **Persistencia**: Se debe configurar el almacenamiento de archivos de salida en el servidor para que el frontend pueda recuperarlos mediante los enlaces proporcionados en el historial.

---
Documentacion tecnica formal generada para Harmonic Score.
