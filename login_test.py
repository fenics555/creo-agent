import urllib.request
import json

URL = "http://127.0.0.1:8765/login"
DATA = {"login": "admin", "pw": "1945"}

try:
    req = urllib.request.Request(URL, method='POST')
    req.add_header('Content-Type', 'application/json')
    json_data = json.dumps(DATA).encode('utf-8')
    req.add_header('Content-Length', str(len(json_data)))
    with urllib.request.urlopen(req, data=json_data) as response:
        print(f"Status: {response.status}")
        print(f"Response: {response.read().decode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
