import urllib.request, json

# Попробуем /chat/poll без токена
try:
    req = urllib.request.Request('http://127.0.0.1:8765/chat/poll?last=0')
    resp = urllib.request.urlopen(req)
    ct = resp.headers.get('content-type', '')
    data = resp.read()
    print('No token - Status:', resp.status, 'CT:', ct)
    print('First 300:', data[:300])
except Exception as e:
    print('No token error:', e)

# Попробуем с пустым токеном
try:
    req = urllib.request.Request('http://127.0.0.1:8765/chat/poll?last=0', headers={'X-Token': ''})
    resp = urllib.request.urlopen(req)
    ct = resp.headers.get('content-type', '')
    data = resp.read()
    print('Empty token - Status:', resp.status, 'CT:', ct)
    print('First 300:', data[:300])
except Exception as e:
    print('Empty token error:', e)

# Посмотрим что есть в users.py
try:
    with open('D:\\AI\\Tools\\agent\\users.py', 'r', encoding='utf-8') as f:
        content = f.read()
    print('\\n=== users.py (первые 500 симв) ===')
    print(content[:500])
except Exception as e:
    print('users.py error:', e)