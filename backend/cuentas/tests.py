import json
from datetime import timedelta

from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.utils import timezone

from .models import TokenRecuperacion, hash_token


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    DEFAULT_FROM_EMAIL='test@harmonicscore.local',
    RECUPERACION_LIMITE_POR_IP=5,
    CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    },
)
class RecuperacionContrasenaTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = Client()
        self.usuario = User.objects.create_user(
            username='musico_inbal',
            email='musico@inbal.edu.mx',
            password='PasswordInicial!1',
            first_name='Carlos',
            last_name='Chávez',
        )

    def tearDown(self):
        cache.clear()

    def test_1_correo_invalido_rechazado(self):
        resp = self.client.post(
            '/api/auth/recuperar-contrasena/',
            data=json.dumps({'email': 'correo-invalido'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(TokenRecuperacion.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_2_correo_no_registrado_devuelve_mensaje_literal(self):
        resp = self.client.post(
            '/api/auth/recuperar-contrasena/',
            data=json.dumps({'email': 'noexiste@inbal.edu.mx'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 404)
        datos = resp.json()
        self.assertEqual(datos.get('message'), 'Correo no registrado en HarmonicScore')
        self.assertEqual(TokenRecuperacion.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_3_correo_registrado_genera_token_y_envia_correo_con_formato(self):
        resp = self.client.post(
            '/api/auth/recuperar-contrasena/',
            data=json.dumps({'email': 'musico@inbal.edu.mx'}),
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200)
        datos = resp.json()
        self.assertEqual(
            datos.get('message'),
            'Revisa tu bandeja de entrada del correo (musico@inbal.edu.mx)',
        )
        self.assertEqual(TokenRecuperacion.objects.count(), 1)
        token_db = TokenRecuperacion.objects.first()
        self.assertFalse(token_db.usado)
        # Expira aproximadamente en 24 horas
        delta = token_db.fecha_expiracion - token_db.fecha_creacion
        self.assertAlmostEqual(delta.total_seconds(), 24 * 3600, delta=5)

        # Verificar formato del correo enviado
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual(correo.subject, 'Recuperación de contraseña en Harmonic Score')
        self.assertIn('Hola, Carlos.', correo.body)
        self.assertIn('Recibimos una solicitud para recuperar tu contraseña en Harmonic Score.', correo.body)
        self.assertIn('/recuperacion/', correo.body)
        self.assertIn('Este enlace caducará en 24 horas.', correo.body)

    def test_4_flujo_completo_cambio_contrasena_e_invalidacion_token(self):
        # Crear token directamente para obtener el token en claro
        token_obj, token_plano = TokenRecuperacion.objects.crear_para(self.usuario, ip='127.0.0.1')
        self.assertEqual(token_obj.token, hash_token(token_plano))

        # 1. GET a la vista recuperacion
        url = f'/recuperacion/{token_plano}/'
        resp_get = self.client.get(url)
        self.assertEqual(resp_get.status_code, 200)
        contenido = resp_get.content.decode('utf-8')
        self.assertIn('Bienvenido, Carlos', contenido)
        self.assertIn('Aceptar', contenido)
        self.assertIn('Mínimo 8 caracteres.', contenido)

        # 2. POST con contraseña débil -> debe fallar y no consumir el token
        resp_debil = self.client.post(url, {
            'password': '12345678',
            'password_confirmacion': '12345678',
        })
        self.assertEqual(resp_debil.status_code, 400)
        token_obj.refresh_from_db()
        self.assertFalse(token_obj.usado)

        # 3. POST con contraseña válida -> actualiza con hash, marca token usado y redirige a login
        nueva_pass = 'ArmoniaSegura#2026'
        resp_ok = self.client.post(url, {
            'password': nueva_pass,
            'password_confirmacion': nueva_pass,
        })
        self.assertEqual(resp_ok.status_code, 302)
        self.assertEqual(resp_ok['Location'], '/login.html?recuperado=1')

        # Verificar base de datos
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password(nueva_pass))
        self.assertNotEqual(self.usuario.password, nueva_pass)  # Nunca texto plano
        self.assertTrue(self.usuario.password.startswith('pbkdf2_'))

        token_obj.refresh_from_db()
        self.assertTrue(token_obj.usado)
        self.assertIsNotNone(token_obj.fecha_uso)

        # 4. Intentar reutilizar el mismo token -> debe rechazarlo
        resp_reuso = self.client.post(url, {
            'password': 'OtraPassword#2026',
            'password_confirmacion': 'OtraPassword#2026',
        })
        self.assertEqual(resp_reuso.status_code, 400)
        self.assertIn('Enlace no válido', resp_reuso.content.decode('utf-8'))

    def test_5_token_expirado_no_permite_cambio(self):
        token_obj, token_plano = TokenRecuperacion.objects.crear_para(self.usuario)
        TokenRecuperacion.objects.filter(pk=token_obj.pk).update(
            fecha_expiracion=timezone.now() - timedelta(minutes=1)
        )
        url = f'/recuperacion/{token_plano}/'
        resp = self.client.post(url, {
            'password': 'ArmoniaSegura#2026',
            'password_confirmacion': 'ArmoniaSegura#2026',
        })
        self.assertEqual(resp.status_code, 400)
        self.usuario.refresh_from_db()
        self.assertFalse(self.usuario.check_password('ArmoniaSegura#2026'))

    def test_6_rate_limit_por_ip(self):
        for _ in range(5):
            self.client.post(
                '/api/auth/recuperar-contrasena/',
                data=json.dumps({'email': 'noexiste@inbal.edu.mx'}),
                content_type='application/json',
            )
        resp_6 = self.client.post(
            '/api/auth/recuperar-contrasena/',
            data=json.dumps({'email': 'noexiste@inbal.edu.mx'}),
            content_type='application/json',
        )
        self.assertEqual(resp_6.status_code, 429)
