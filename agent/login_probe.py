import urllib.request
import json

url = "http://localhost:8765/login"
data = json.dumps({"login": "admin", "pw": "1945"}).encode('utf-8')
headers = {"Content-Type": "application/json"}

req = urllib.request.Request(url, data=data, headers=headers, method='POST')

try:
    with urllib.request.urlopen(req) as response:
        print(f"Status: {response.getcode()}")
        print(f"Body: {response.read().decode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
