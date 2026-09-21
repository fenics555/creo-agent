import urllib.request
import json

url = "http://localhost:8765/wiz_pdf_preview"
token = "glufsx-GeLW2zOVQM22-qEDkFbBHEXxA"
data = json.dumps({"root": "D:\\AI\\tools\\agent", "limit": 10}).encode('utf-8')
headers = {
    "Content-Type": "application/json",
    "X-Token": token
}

req = urllib.request.Request(url, data=data, headers=headers, method='POST')

try:
    with urllib.request.urlopen(req) as response:
        print(f"Status: {response.getcode()}")
        print(f"Body: {response.read().decode('utf-8')}")
except Exception as e:
    print(f"Error: {e}")
