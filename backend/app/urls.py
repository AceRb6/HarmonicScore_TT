from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from . import views
from cuentas import views as cuentas_views

urlpatterns = [
    # ─── Vistas HTML ──────────────────────────────────────────────────────────
    path('', views.home, name='home'),
    path('carga/', views.carga, name='carga'),
    path('consultas/', views.consultas, name='consultas'),
    path('login/', views.login_view, name='login'),
    path('registro/', views.registro, name='registro'),
    # Alias .html para compatibilidad con JS existente
    path('index.html', views.home),
    path('carga.html', views.carga),
    path('consultas.html', views.consultas),
    path('login.html', views.login_view),
    path('registro.html', views.registro),
    path('recuperar-contrasena.html', views.recuperar_page),

    # ─── Admin ────────────────────────────────────────────────────────────────
    path('admin/', admin.site.urls),

    # ─── API: Autenticacion ───────────────────────────────────────────────────
    path('api/auth/registro/', views.registro_usuario, name='registro_usuario'),
    path('api/auth/login/', views.login_usuario, name='login_usuario'),
    path('api/auth/logout/', views.logout_usuario, name='logout_usuario'),
    path('api/auth/recuperar-contrasena/', cuentas_views.solicitar_recuperacion, name='recuperar_contrasena'),

    # ─── Recuperacion de contrasena (enlace enviado por correo) ───────────────
    path('recuperacion/', cuentas_views.recuperacion, name='recuperacion_sin_token'),
    path('recuperacion/<str:token>/', cuentas_views.recuperacion, name='recuperacion'),

    # ─── API: Transcripciones ─────────────────────────────────────────────────
    path('api/transcripciones/subir/', views.subir_transcripcion, name='subir_transcripcion'),
    path('api/transcripciones/historial/', views.historial_transcripciones, name='historial_transcripciones'),
    path('api/transcripciones/mis/', views.mis_transcripciones, name='mis_transcripciones'),
    path('api/transcripciones/<str:job_id>/', views.estado_transcripcion, name='estado_transcripcion'),
    path('api/transcripciones/<uuid:transcripcion_id>/descargar-pdf/', views.descargar_pdf, name='descargar_pdf'),
    path('api/transcripciones/<uuid:transcripcion_id>/descargar-mxl/', views.descargar_mxl, name='descargar_mxl'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)