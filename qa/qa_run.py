# -*- coding: utf-8 -*-
"""QA regression runner for CREO-AGENT. Stdlib only. Run from D:\\AI\\tools\\service."""
import urllib.request, json, re, time, os, datetime, subprocess, sys

BASE = "http://127.0.0.1:8765"
TOKEN = None
LOG_FILE = r"D:\AI\tools\agent_log_frezer4.txt"

def post(path, data):
    req = urllib.request.Request(
        BASE + path,
        json.dumps(data).encode("utf-8"),
        {"Content-Type": "application/json", "X-Token": TOKEN or ""},
    )
    r = urllib.request.urlopen(req, timeout=180)
    return json.loads(r.read().decode("utf-8"))

def login():
    print("DEBUG: starting login")
    global TOKEN
    r = post("/login", {"login": "qa_bot_admin", "pw": "QaBot2_2026"})
    print(f"DEBUG: login result ok={r.get('ok')}")
    if r.get("ok"):
        TOKEN = r.get("token")
        print("DEBUG: login success")
        return TOKEN
    
    print("DEBUG: login failed, trying register")
    post("/register", {"login": "qa_bot_admin", "pw": "QaBot2_2026"})
    print("DEBUG: register done, retrying login")
    r = post("/login", {"login": "qa_bot_admin", "pw": "QaBot2_2026"})
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
                print("СѓР¶Рµ РёРґС‘С‚")
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
            ("РєР°РєР°СЏ РјРѕРґРµР»СЊ РѕС‚РєСЂС‹С‚Р° РІ Creo?", "creo_get_active"),
            ("РЅР°Р№РґРё РјРѕРґРµР»СЊ РєРѕСЂРїСѓСЃ", "models_find"),
            (None, "models_where"),
            ("СЃРєРѕР»СЊРєРѕ РІСЃРµРіРѕ РјРѕРґРµР»РµР№ РІ Р±Р°Р·Рµ?", "models_stats"),
            (r"РїСЂРѕС‡РёС‚Р°Р№ С„Р°Р№Р» D:\AI\repo\SKILL_index.md", "read_file"),
            ("С‡С‚Рѕ РІ Р±Р°Р·Рµ Р·РЅР°РЅРёР№ РїСЂРѕ РїСЂСѓР¶РёРЅС‹?", "search_kb"),
            ("РїРµСЂРµРІРµРґРё 150 РќРј РІ РєРіСЃРј", "calc"),
            ("РєР°РєРёРµ РЅР°РєРѕРїР»РµРЅРЅС‹Рµ РїСЂРѕР±Р»РµРјС‹ РїРѕ С‚СЂРµР№Р»Р°Рј?", "trail_problems"),
            ("РїРѕРєР°Р¶Рё С‚РµРєСѓС‰РёРµ РЅР°СЃС‚СЂРѕР№РєРё", "settings_show"),
            ("РїСЂРёРІРµС‚", "answer"),
            ("РЅР°Р№РґРё РјРѕРґРµР»СЊ РґРµСЂР¶Р°С‚РµР»СЊ Рё РїРѕРєР°Р¶Рё, РіРґРµ РѕРЅР° РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ", "models_find"),
            ("РїРѕСЃРјРѕС‚СЂРё РґРµС‚Р°Р»СЊ", "creo_get_active"),
            ("index_state", "index_state"),
            ("creo_save", "approval"),
            ("Сѓ С‚РµР±СЏ РЅРµС‚ РґРѕСЃС‚СѓРїР° Рє С„Р°Р№Р»Р°Рј?", "no_refusal"),
            ("СЂР°Р·Р±РµСЂРё РїРѕСЃР»РµРґРЅРёР№ С‚СЂРµР№Р»", "trail_analyze"),
        ]

        results = []
        model_name_holder = None
        think_count = 0

        for i, (q, expected) in enumerate(cases, 1):
            if q is None:
                q = f"РіРґРµ РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ {model_name_holder}?" if model_name_holder else "РіРґРµ РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ РєРѕСЂРїСѓСЃ?"
            
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
                    note = f"Р¶РґР°Р» ANSWER, РїРѕР»СѓС‡РёР» РёРЅСЃС‚СЂСѓРјРµРЅС‚С‹: {tools}"
            elif expected == "approval":
                if "[РЎРћР“Р›РђРЎРћР’РђРќРР•]" in answer and expected in tools:
                    pass
                elif "РЅРµ РїРѕРґС‚РІРµСЂР¶РґР°Р»" in answer.lower():
                    pass
                else:
                    verdict = "FAIL"
                    note = f"Р¶РґР°Р» {expected} РІ РёРЅСЃС‚СЂСѓРјРµРЅС‚Р°С… Р [РЎРћР“Р›РђРЎРћР’РђРќРР•] РІ РѕС‚РІРµС‚Рµ"
            elif expected == "no_refusal":
                refusals = ["РЅРµС‚ РґРѕСЃС‚СѓРїР°", "РЅРµ РјРѕРіСѓ", "РєР°Рє СЏР·С‹РєРѕРІР°СЏ РјРѕРґРµР»СЊ", "РЅРµ РёРјРµСЋ РґРѕСЃС‚СѓРїР°", "Сѓ РјРµРЅСЏ РЅРµС‚"]
                if any(w in answer.lower() for w in refusals):
                    verdict = "FAIL"
                    note = "РѕС‚РєР°Р·РЅР°СЏ С„СЂР°Р·Р° РІ РѕС‚РІРµС‚Рµ"
            else:
                if expected not in tools:
                    verdict = "FAIL"
                    note = f"Р¶РґР°Р» {expected}, РїРѕР»СѓС‡РёР» {tools}"

            is_direct_call = (q.strip() == expected)
            if not think.strip():
                if not is_direct_call:
                    note += "; think РїСѓСЃС‚РѕР№ (РїСЂРµРґСѓРїСЂРµР¶РґРµРЅРёРµ)"


            if lat_ratio(answer) > 0.25:
                verdict = "FAIL"
                note += f"; Р»Р°С‚РёРЅРёС†Р° {lat_ratio(answer):.0%}>25%"

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
        print(f"think: {think_count} РёР· 16")
        print(f"Traceback in new log lines: {new_tb}")
        print(f"feedback ok: {fb_ok}")
        print(f"status: blocks={st.get('blocks')} tools={st.get('tools')}")
        print("\n=== FAIL DETAIL ===")
        for r in results:
            if r["verdict"] == "FAIL":
                print(f"  #{r['#']} {r.get('q','')[:40]} | РѕР¶РёРґР°Р» {r.get('expected')} | РїРѕР»СѓС‡РёР» {r.get('tools')} | {r.get('note')}")

        with open(r"D:\AI\tools\agent\qa\qa_results.json", "w", encoding="utf-8") as f:
            json.dump({"results": results, "after": {"traceback_new": new_tb, "feedback_ok": fb_ok, "status": st}}, f, ensure_ascii=False, indent=2)
        print("\nsaved D:\\AI\\tools\\agent\\qa\\qa_results.json")
    finally:
        if os.path.exists(pid_file):
            os.remove(pid_file)

if __name__ == "__main__":
    login()
    run()

