import requests

BASE_URL = 'http://localhost:8001'
session = requests.Session()

print('1. Login...')
login_data = {'username': 'testadmin', 'password': 'TestAdmin123!'}
res_login = session.post(f'{BASE_URL}/api/auth/login/', json=login_data)
print('Login Status:', res_login.status_code)
print('Login Response:', res_login.text)

print('\n2. Subiendo audio de prueba...')
# Crear un archivo de prueba
with open('test_audio.mp3', 'wb') as f:
    f.write(b'fake mp3 content')

with open('test_audio.mp3', 'rb') as f:
    files = {'audio': ('test_audio.mp3', f, 'audio/mpeg')}
    res_upload = session.post(f'{BASE_URL}/api/transcripciones/subir/', files=files)

print('Upload Status:', res_upload.status_code)
print('Upload Response:', res_upload.text)

print('\n3. Consultando historial...')
res_history = session.get(f'{BASE_URL}/api/transcripciones/historial/')
print('History Status:', res_history.status_code)
print('History Response:', res_history.text)
