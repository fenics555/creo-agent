# -*- coding: utf-8 -*-
"""QA regression runner for CREO-AGENT. Stdlib only. Run from D:\\AI\\tools\\service."""
import urllib.request, json, re, time, os, datetime, subprocess, sys

BASE = "http://127.0.0.1:8765"
TOKEN = None
import socket
HOST = socket.gethostname().replace(" ", "").replace("-", "")[:16]
LOG_FILE = r"D:\AI\tools" + ("\\agent_log_%s.txt" % HOST)

def post(path, data):
    req = urllib.request.Request(
        BASE + path,
        json.dumps(data).encode("utf-8"),
        {"Content-Type": "application/json", "X-Token": TOKEN or ""},
    )
    r = urllib.request.urlopen(req, timeout=180)
    return json.loads(r.read().decode("utf-8"))

def _creds():
    import json as _j
    p = r"D:\AI\tools\agent\data\secrets.json"
    try:
        d = _j.load(open(p, encoding="utf-8"))
        return d.get("qa_login", "qa_bot_admin"), d.get("qa_password", "")
    except Exception:
        return "qa_bot_admin", ""


def login():
    print("DEBUG: starting login")
    global TOKEN
    ql, qp = _creds()
    r = post("/login", {"login": ql, "pw": qp})
    print(f"DEBUG: login result ok={r.get('ok')}")
    if r.get("ok"):
        TOKEN = r.get("token")
        print("DEBUG: login success")
        return TOKEN
    
    print("DEBUG: login failed, trying register")
    post("/register", {"login": ql, "pw": qp})
    print("DEBUG: register done, retrying login")
    r = post("/login", {"login": ql, "pw": qp})
    print(f"DEBUG: retry login result ok={r.get('ok')}")
    TOKEN = r.get("token")
    return TOKEN

def ask(q):
    return post("/ask", {"token": TOKEN, "q": q})

def extract_tools(log_lines):
    tools = []
    for l in log_lines:
        m = re.match(r"^\s*([A-Za-z0-9_]+)\(", l)
        if m:
            tools.append(m.group(1))
    return list(dict.fromkeys(tools))

def lat_ratio(text):
    if not text:
        return 0.0
    cleaned_text = re.sub(r'[A-Za-z]:\\[^ ]+|/[^ ]+|[A-Za-z0-9_\-]+\.(?:prt|asm|drw|step)', '', text)
    letters = [c for c in cleaned_text if c.isalpha()]
    latin = [c for c in letters if c.isascii()]
    return len(latin) / len(letters) if letters else 0.0

def is_pid_running(pid):
    try:
        check = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], capture_output=True, text=True)
        return str(pid) in check.stdout
    except Exception:
        return False

def run():
    pid_file = r"D:\AI\tools\agent\data\tmp\qa_run.pid"
    os.makedirs(os.path.dirname(pid_file), exist_ok=True)
    
    if os.path.exists(pid_file):
        try:
            with open(pid_file, 'r') as f:
                old_pid = int(f.read().strip())
            if is_pid_running(old_pid):
                print("уже идёт")
                return
        except Exception:
            pass

    try:
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))

        before = 0
        if os.path.exists(LOG_FILE):
            before = len(open(LOG_FILE, encoding="utf-8", errors="ignore").read().splitlines())

        cases = [
            ("какая модель открыта в Creo?", "creo_get_active"),
            ("найди модель корпус", "models_find"),
            (None, "models_where"),
            ("сколько всего моделей в базе?", "models_stats"),
            (r"прочитай файл D:\AI\repo\SKILL_index.md", "read_file"),
            ("что в базе знаний про пружины?", "search_kb"),
            ("переведи 150 Нм в кгсм", "calc"),
            ("какие накопленные проблемы по трейлам?", "trail_problems"),
            ("покажи текущие настройки", "settings_show"),
            ("привет", "answer"),
            ("найди модель держатель и покажи, где она используется", "models_find"),
            ("посмотри деталь", "creo_get_active"),
            ("index_state", "index_state"),
            ("creo_save", "approval"),
            ("у тебя нет доступа к файлам?", "no_refusal"),
            ("разбери последний трейл", "trail_analyze"),
        ]

        results = []
        model_name_holder = None
        think_count = 0

        for i, (q, expected) in enumerate(cases, 1):
            if q is None:
                q = f"где используется {model_name_holder}?" if model_name_holder else "где используется корпус?"
            
            time.sleep(0.1)
            try:
                r = ask(q)
            except Exception as e:
                results.append({"#": i, "q": q, "expected": expected, "error": str(e), "verdict": "FAIL"})
                continue

            answer = (r.get("answer") or "")
            think = (r.get("think") or "")
            log = r.get("log") or []
            log_str = "\n".join(log)
            
            if think.strip():
                think_count += 1

            if i == 2 and answer:
                m = re.search(r"[A-Za-z0-9_\-]+\.(?:prt|asm|drw)", answer, re.I)
                if m:
                    model_name_holder = m.group(0)

            tools = extract_tools(log)
            verdict = "PASS"
            note = ""

            if expected == "answer":
                if tools:
                    verdict = "FAIL"
                    note = f"ждал ANSWER, получил инструменты: {tools}"
            elif expected == "approval":
                if "[СОГЛАСОВАНИЕ]" in answer and expected in tools:
                    pass
                elif "не подтверждал" in answer.lower():
                    pass
                else:
                    verdict = "FAIL"
                    note = f"ждал {expected} в инструментах И [СОГЛАСОВАНИЕ] в ответе"
            elif expected == "no_refusal":
                refusals = ["нет доступа", "не могу", "как языковая модель", "не имею доступа", "у меня нет"]
                if any(w in answer.lower() for w in refusals):
                    verdict = "FAIL"
                    note = "отказная фраза в ответе"
            else:
                if expected not in tools:
                    verdict = "FAIL"
                    note = f"ждал {expected}, получил {tools}"

            is_direct_call = (q.strip() == expected)
            if not think.strip():
                if not is_direct_call:
                    note += "; think пустой (предупреждение)"


            if lat_ratio(answer) > 0.25:
                verdict = "FAIL"
                note += f"; латиница {lat_ratio(answer):.0%}>25%"

            if "Traceback" in answer or "Traceback" in log_str:
                verdict = "FAIL"
                note += "; Traceback"

            results.append({
                "#": i, "q": q, "expected": expected, "tools": tools,
                "think": bool(think.strip()), "answer": answer[:120],
                "verdict": verdict, "note": note.strip("; "),
            })
            print(f"{i:2d} {verdict} | {q[:50]}")

        after = len(open(LOG_FILE, encoding="utf-8", errors="ignore").read().splitlines())
        new_tb = sum(1 for l in open(LOG_FILE, encoding="utf-8", errors="ignore").read().splitlines()[before:] if "Traceback" in l)

        try:
            fb = post("/feedback", {"token": TOKEN, "query": "qa", "think": "", "tool": "qa", "result": "qa", "ok": 1, "comment": "qa probe"})
            fb_ok = fb.get("ok") is True
        except Exception as e:
            fb_ok = False
            fb = str(e)

        try:
            sr = urllib.request.urlopen(BASE + "/status", timeout=10)
            st = json.loads(sr.read())
        except Exception as e:
            st = {"error": str(e)}

        print(f"{datetime.date.today()} {model_name_holder or 'unknown'}")
        print("\n=== SUMMARY ===")
        passed = sum(1 for r in results if r["verdict"] == "PASS")
        failed = sum(1 for r in results if r["verdict"] == "FAIL")
        print(f"PASS {passed} / FAIL {failed}")
        print(f"think: {think_count} из 16")
        print(f"Traceback in new log lines: {new_tb}")
        print(f"feedback ok: {fb_ok}")
        print(f"status: blocks={st.get('blocks')} tools={st.get('tools')}")
        print("\n=== FAIL DETAIL ===")
        for r in results:
            if r["verdict"] == "FAIL":
                print(f"  #{r['#']} {r.get('q','')[:40]} | ожидал {r.get('expected')} | получил {r.get('tools')} | {r.get('note')}")

        with open(r"D:\AI\tools\agent\qa\qa_results.json", "w", encoding="utf-8") as f:
            json.dump({"results": results, "after": {"traceback_new": new_tb, "feedback_ok": fb_ok, "status": st}}, f, ensure_ascii=False, indent=2)
        print("\nsaved D:\\AI\\tools\\agent\\qa\\qa_results.json")
    finally:
        if os.path.exists(pid_file):
            os.remove(pid_file)

if __name__ == "__main__":
    login()
    run()

