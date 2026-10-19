"""
Bateria de pruebas contra el stack Docker real (Django + PostgreSQL).
Ejecutar:  python test_db_completo.py
Requiere contenedores harmonic_django y harmonic_db arriba.
"""
import subprocess
import requests

BASE = 'http://localhost:8001'
resultados = []


def psql(sql):
    out = subprocess.run(
        ['docker', 'exec', 'harmonic_db', 'psql', '-U', 'admin', '-d', 'harmonic', '-t', '-A', '-c', sql],
        capture_output=True, text=True)
    return out.stdout.strip()


def django_shell(code):
    out = subprocess.run(
        ['docker', 'exec', 'harmonic_django', 'python', 'manage.py', 'shell', '-c', code],
        capture_output=True, text=True)
    return out.stdout.strip()


def check(nombre, condicion, detalle=''):
    resultados.append(condicion)
    print(f"[{'OK ' if condicion else 'FALLO'}] {nombre} {detalle}")


# --- Preparacion: dos usuarios de prueba (el registro por API exige reCAPTCHA real) ---
django_shell(
    "from django.contrib.auth.models import User\n"
    "User.objects.filter(username__in=['prueba_a','prueba_b']).delete()\n"
    "User.objects.create_user('prueba_a','a@test.com','ClaveA_12345')\n"
    "User.objects.create_user('prueba_b','b@test.com','ClaveB_12345')\n")

# --- 1. Motor y tablas ---
check('Motor es PostgreSQL', 'PostgreSQL' in psql('SELECT version();'))
check('Tabla transcripciones existe', psql("SELECT to_regclass('public.transcripciones_transcripcion');") != '')
check('Usuarios de prueba guardados', psql("SELECT count(*) FROM auth_user WHERE username LIKE 'prueba_%';") == '2')
check('Contrasena guardada hasheada (no texto plano)',
      psql("SELECT password FROM auth_user WHERE username='prueba_a';").startswith('pbkdf2_sha256$'))

# --- 2. Autenticacion ---
a = requests.Session()
b = requests.Session()
r = a.post(f'{BASE}/api/auth/login/', json={'username': 'prueba_a', 'password': 'ClaveA_12345'})
check('Login correcto -> 200', r.status_code == 200, r.status_code)
r = requests.post(f'{BASE}/api/auth/login/', json={'username': 'prueba_a', 'password': 'mala'})
check('Login con clave incorrecta -> 401', r.status_code == 401, r.status_code)
b.post(f'{BASE}/api/auth/login/', json={'username': 'prueba_b', 'password': 'ClaveB_12345'})

# --- 3. Seguridad: sin sesion ---
r = requests.post(f'{BASE}/api/transcripciones/subir/', files={'audio': ('x.mp3', b'abc', 'audio/mpeg')})
check('Subir sin sesion -> 401', r.status_code == 401, r.status_code)
r = requests.get(f'{BASE}/api/transcripciones/historial/')
check('Historial sin sesion -> 401', r.status_code == 401, r.status_code)

# --- 4. Validaciones de subida ---
r = a.post(f'{BASE}/api/transcripciones/subir/', files={'audio': ('virus.exe', b'abc', 'application/octet-stream')})
check('Formato .exe rechazado -> 400', r.status_code == 400, r.status_code)
r = a.post(f'{BASE}/api/transcripciones/subir/')
check('Sin archivo -> 400', r.status_code == 400, r.status_code)

# --- 5. Insercion real ---
r = a.post(f'{BASE}/api/transcripciones/subir/', files={'audio': ('cancion_a.mp3', b'ID3' + b'0' * 2048, 'audio/mpeg')})
check('Subida valida -> 202', r.status_code == 202, r.status_code)
job_a = r.json().get('job_id')
fila = psql(f"SELECT estado||'|'||titulo_audio FROM transcripciones_transcripcion WHERE id='{job_a}';")
check('Registro en PostgreSQL con estado PENDIENTE', fila == 'PENDIENTE|cancion_a.mp3', fila)
check('Registro ligado al usuario correcto',
      psql(f"SELECT u.username FROM transcripciones_transcripcion t JOIN auth_user u ON u.id=t.usuario_id WHERE t.id='{job_a}';") == 'prueba_a')

a.post(f'{BASE}/api/transcripciones/subir/', files={'audio': ('segunda_a.wav', b'RIFF' + b'0' * 1024, 'audio/wav')})
b.post(f'{BASE}/api/transcripciones/subir/', files={'audio': ('cancion_b.mp3', b'ID3' + b'1' * 512, 'audio/mpeg')})

# --- 6. Historial y aislamiento entre usuarios ---
h_a = a.get(f'{BASE}/api/transcripciones/historial/').json()
h_b = b.get(f'{BASE}/api/transcripciones/historial/').json()
check('Usuario A ve 2 transcripciones', h_a.get('total') == 2, h_a.get('total'))
check('Usuario B ve 1 transcripcion', h_b.get('total') == 1, h_b.get('total'))
r = b.get(f'{BASE}/api/transcripciones/{job_a}/')
check('Usuario B NO puede ver el job de A -> 404', r.status_code == 404, r.status_code)
r = a.get(f'{BASE}/api/transcripciones/{job_a}/')
check('Usuario A consulta su propio job -> 200', r.status_code == 200 and r.json().get('estado') == 'PENDIENTE')

# --- 7. Actualizacion de estado (lo que hara el worker) ---
django_shell(
    "from transcripciones.models import Transcripcion\n"
    f"t=Transcripcion.objects.get(id='{job_a}'); t.estado='EXITO'; t.harmonic_score=0.87; t.save()\n")
r = a.get(f'{BASE}/api/transcripciones/{job_a}/').json()
check('Cambio a EXITO y score 0.87 reflejado en API', r.get('estado') == 'EXITO' and r.get('harmonic_score') == 0.87, r)

# --- 8. Integridad: borrar usuario borra sus transcripciones (CASCADE) ---
antes = psql("SELECT count(*) FROM transcripciones_transcripcion;")
django_shell("from django.contrib.auth.models import User; User.objects.get(username='prueba_b').delete()")
despues = psql("SELECT count(*) FROM transcripciones_transcripcion;")
check('CASCADE: al borrar usuario B se borra su transcripcion', int(despues) == int(antes) - 1, f'{antes}->{despues}')

# --- 9. Archivos fisicos ---
ls = subprocess.run(['docker', 'exec', 'harmonic_django', 'ls', 'media/audios/in/'], capture_output=True, text=True).stdout
check('Archivo fisico cancion_a.mp3 en disco', 'cancion_a' in ls)

# --- Limpieza ---
django_shell("from django.contrib.auth.models import User; User.objects.filter(username__startswith='prueba_').delete()")

print(f"\nRESULTADO: {sum(resultados)}/{len(resultados)} pruebas OK")
