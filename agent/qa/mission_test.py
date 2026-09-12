import urllib.request
import json

URL = "http://127.0.0.1:8765"
TK = "PAHJolcRE0dNd4H05J0bRUsptGTHaC9d"

def post_json(url, data):
    req = urllib.request.Request(url, method='POST')
    req.add_header('Content-Type', 'application/json')
    json_data = json.dumps(data).encode('utf-8')
    req.add_header('Content-Length', str(len(json_data)))
    with urllib.request.urlopen(req, data=json_data) as response:
        return response.read().decode('utf-8')

def get_json(url, headers=None):
    req = urllib.request.Request(url, method='GET')
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    with urllib.request.urlopen(req) as response:
        return response.read().decode('utf-8')

def run_mission():
    print("--- START MISSION ---")
    
    # 1. POST /ask
    print("Step 1: POST /ask...")
    try:
        res1_raw = post_json(f"{URL}/ask", {"token": TK, "q": "какая модель открыта в Creo?"})
        print(f"Response 1: {res1_raw}")
        ans1 = json.loads(res1_raw)
        if "error" in ans1:
            print(f"Error in Step 1: {ans1['error']}")
            return
    except Exception as e:
        print(f"Exception in Step 1: {e}")
        return

    # Get last line of log
    print("Step 1.1: GET /log...")
    try:
        res_log_raw = get_json(f"{URL}/log", {"X-Token": TK})
        print(f"Log Response: {res_log_raw}")
        log_data = json.loads(res_log_raw)
        log_content = log_data.get("log", "")
        lines = log_content.splitlines()
        last_log_line = lines[-1] if lines else "LOG EMPTY"
        print(f"Last log line: {last_log_line}")
    except Exception as e:
        print(f"Exception in Step 1.1: {e}")
        last_log_line = "LOG ERROR"

    # 2. POST /setcfg
    print("Step 2: POST /setcfg...")
    try:
        res2_raw = post_json(f"{URL}/setcfg", {"token": TK, "key": "think_mode", "value": 2})
        print(f"Response 2: {res2_raw}")
        ans2 = json.loads(res2_raw)
        if ans2.get("ok") is not True:
            print(f"Error in Step 2: {ans2}")
            return
    except Exception as e:
        print(f"Exception in Step 2: {e}")
        return

    # 3. POST /ask (razberi)
    print("Step 3: POST /ask (разбери)...")
    try:
        res3_raw = post_json(f"{URL}/ask", {"token": TK, "q": "разбери последний трейл"})
        print(f"Response 3: {res3_raw}")
        ans3 = json.loads(res3_raw)
        if "error" in ans3:
            print(f"Error in Step 3: {ans3['error']}")
            return
        think_val = ans3.get("think", "NO THINK FIELD")
        print(f"Think field: {think_val}")
    except Exception as e:
        print(f"Exception in Step 3: {e}")
        think_val = "EXCEPTION"

    print("\n--- MISSION RESULTS ---")
    print(f"ANS1: {ans1.get('answer')}")
    print(f"LOG_LAST: {last_log_line}")
    print(f"THINK: {think_val}")
    
    # Verdict logic
    # If ans1 ok, r2 ok, and think_val not empty/error
    if "error" not in ans1 and ans2.get("ok") is True and think_val not in ["NO THINK FIELD", "EXCEPTION"]:
        print("VERDICT: цепь login→ask→setcfg жива")
    else:
        print("VERDICT: цепь login→ask→setcfg не жива")

if __name__ == "__main__":
    run_mission()
