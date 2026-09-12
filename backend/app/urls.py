from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('carga/', views.carga, name='carga'),
    path('consultas/', views.consultas, name='consultas'),
    path('login/', views.login_view, name='login'),
    path('registro/', views.registro, name='registro'),
    # Alias .html usados por el HTML y el JS existente
    path('index.html', views.home),
    path('carga.html', views.carga),
    path('consultas.html', views.consultas),
    path('login.html', views.login_view),
    path('registro.html', views.registro),
    path('recuperar-contrasena.html', views.recuperar_page),
    # API
    path('admin/', admin.site.urls),
    path('api/auth/registro/', views.registro_usuario, name='registro_usuario'),
    path('api/auth/recuperar-contrasena/', views.recuperar_contrasena, name='recuperar_contrasena'),
    path('api/transcripciones/subir/', views.subir_transcripcion, name='subir_transcripcion'),
]