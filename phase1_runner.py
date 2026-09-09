import urllib.request
import json
import time

URL = 'http://127.0.0.1:8765/ask'
TOKEN = 'FDRLrFSDDa_ojHLB4VanlYOaM5T8FyzQ'

CASES = [
    "привет",
    "какая сегодня дата?",
    "кто ты?",
    "какая модель используется?",
    "список инструментов",
    "что в папке agent/data/shots?",
    "разбери последний трейл",
    "сделай прогноз деградации",
    "найди модель korpus.prt",
    "сколько файлов в базе?",
    "какие роли есть в системе?",
    "покажи последние логи"
]

def run_case(i, q):
    print(f"Running Case {i+1}: {q}")
    data = {'token': TOKEN, 'q': q}
    req = urllib.request.Request(URL, data=json.dumps(data).encode('utf-8'), headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            return res
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    results = []
    for i, q in enumerate(CASES):
        res = run_case(i, q)
        results.append({"case": i+1, "query": q, "response": res})
        time.sleep(1)
    
    with open('phase1_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("Done. Results saved to phase1_results.json")
