import urllib.request, json

# 1. Получаем токен через логин
try:
    req = urllib.request.Request(
        'http://127.0.0.1:8765/login',
        data=json.dumps({'login': 'admin', 'pw': 'admin'}).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    resp = urllib.request.urlopen(req)
    d = json.loads(resp.read().decode('utf-8'))
    print('Login:', d)
    token = d.get('token', '')
except Exception as e:
    print('Login error:', e)
    token = ''

# 2. Пробуем /chat/poll с токеном
if token:
    try:
        req = urllib.request.Request(
            'http://127.0.0.1:8765/chat/poll?last=0',
            headers={'X-Token': token}
        )
        resp = urllib.request.urlopen(req)
        ct = resp.headers.get('content-type', '')
        data = resp.read()
        print('Status:', resp.status)
        print('Content-Type:', ct)
        print('First 200 bytes:', data[:200])
        try:
            text = data.decode('utf-8')
            print('As text:', text[:500])
        except:
            print('Cannot decode as text')
    except Exception as e:
        print('Poll error:', e)