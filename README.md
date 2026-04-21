# 🎵 Harmonic Score App

Proyecto de Trabajo Terminal enfocado en el análisis y cálculo de un **Harmonic Score**, utilizando una arquitectura basada en contenedores con separación de servicios.

---

# 🧱 Arquitectura del sistema

El sistema está dividido en tres servicios principales:

* 🧠 **ML Service**: Procesamiento del modelo (FastAPI + soporte CUDA)
* 🌐 **Backend**: API en Django
* 🗄️ **Base de datos**: PostgreSQL

Comunicación:

Frontend → Django → ML Service → DB

---

# 📁 Estructura del proyecto

```
harmonic-score-app/
│
├── backend/          # Django
├── ml-service/       # Modelo + FastAPI
├── frontend/         # (opcional)
├── database/         # scripts SQL
├── docker-compose.yml
└── README.md
```

---

# ⚙️ Requisitos

Antes de comenzar, asegúrate de tener instalado:

* Docker
* Docker Compose
* (Opcional) NVIDIA Container Toolkit (para GPU)

---

# 🚀 Instalación y ejecución

## 1. Clonar el repositorio

```
git clone https://github.com/USUARIO/harmonic-score-app.git
cd harmonic-score-app
```

---

## 2. Construir y levantar los contenedores

```
docker-compose up --build
```

Esto levantará:

* Django → http://localhost:8000
* ML Service → http://localhost:5000
* PostgreSQL → puerto 5432

---

## 3. Verificar servicios

### ML Service

```
http://localhost:5000/docs
```

### Backend Django

```
http://localhost:8000
```

---

# 🧪 Uso básico

El backend se comunica con el servicio de ML mediante:

```
POST http://ml:5000/analyze
```

Ejemplo de respuesta:

```
{
  "score": 0.87
}
```

---

# 🐳 Comandos útiles

## Detener contenedores

```
docker-compose down
```

## Reconstruir desde cero

```
docker-compose up --build
```

## Ver logs

```
docker-compose logs -f
```

---

# ⚠️ Notas importantes

* No usar `localhost` para comunicación entre servicios → usar nombres de servicio (`ml`, `db`)
* Si hay errores, ejecutar:

```
docker-compose down -v
```

---

# 💡 Recomendaciones

* Evitar ejecutar el proyecto dentro de OneDrive
* Usar rutas locales como:

```
C:\dev\harmonic-score-app
```

---

# 👥 Colaboración (Git)
##  uziel xd
## Crear nueva rama

```
git checkout -b feature/nombre-feature
```

## Guardar cambios

```
git add .
git commit -m "feat: descripción del cambio"
```

## Subir cambios

```
git push origin feature/nombre-feature
```

---

# 🔥 Estado actual

✅ Arquitectura base funcional
✅ Contenedores Docker operativos
✅ Comunicación entre servicios

---

# 📌 Pendientes

* Integración frontend
* Persistencia de resultados
* Implementación completa del modelo

---

# 👨‍💻 Equipo

Proyecto desarrollado como parte del Trabajo Terminal (TT).

---
