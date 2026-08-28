"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from . import views

# 2026-08-21: Importaciones necesarias para servir archivos /media/ en desarrollo
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/registro/', views.registro_usuario, name='registro_usuario'),
    path('api/auth/recuperar-contrasena/', views.recuperar_contrasena, name='recuperar_contrasena'),
    path('api/transcripciones/subir/', views.subir_transcripcion, name='subir_transcripcion'),
    # 2026-08-21: Nuevo endpoint para obtener el historial de transcripciones del usuario autenticado
    path('api/transcripciones/mis/', views.mis_transcripciones, name='mis_transcripciones'),
]

# 2026-08-21: Servir archivos /media/ en modo DEBUG (desarrollo local)
# En producción esto lo maneja el servidor web (nginx/apache)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
