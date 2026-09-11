# -*- coding: utf-8 -*-
"""QA regression runner for CREO-AGENT. Stdlib only."""
import urllib.request, json, re, time, os, datetime, subprocess, sys, socket

BASE = "http://127.0.0.1:8765"
TOKEN = None
LOG_FILE = r"D:\AI\tools\agent_log_%s.txt" % re.sub(r"[^A-Za-z0-9]", "", socket.gethostname()).lower()


def post(path, data):
    req = urllib.request.Request(
        BASE + path,
        json.dumps(data).encode("utf-8"),
        {"Content-Type": "application/json", "X-Token": TOKEN or ""},
    )
    r = urllib.request.urlopen(req, timeout=180)
    return json.loads(r.read().decode("utf-8"))


def login():
    global TOKEN
    r = post("/login", {"login": "qa_tester", "pw": "QaTester2_2026"})
    if r.get("ok"):
        TOKEN = r.get("token")
        return TOKEN
    post("/register", {"login": "qa_tester", "pw": "QaTester2_2026"})
    r = post("/login", {"login": "qa_tester", "pw": "QaTester2_2026"})
    TOKEN = r.get("token")
    return TOKEN


def ask(q, mode=1):
    return post("/ask", {"token": TOKEN, "q": q, "mode": mode})


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
    cleaned = re.sub(r"[A-Za-z]:\\[^ ]+|/[^ ]+|[A-Za-z0-9_-]+\.(?:prt|asm|drw|step)", "", text)
    letters = [c for c in cleaned if c.isalpha()]
    latin = [c for c in letters if c.isascii()]
    return len(latin) / len(letters) if letters else 0.0


def is_pid_running(pid):
    try:
        check = subprocess.run(["tasklist", "/FI", f"PID eq {pid}"], capture_output=True, text=True)
        return str(pid) in check.stdout
    except Exception:
        return False

def run():
    pid_file = r"D:\AI\tools\agent\data\tmp\qa_run.pid"
    os.makedirs(os.path.dirname(pid_file), exist_ok=True)
    if os.path.exists(pid_file):
        try:
            old_pid = int(open(pid_file).read().strip())
            if is_pid_running(old_pid):
                print("уже идёт")
                return
        except Exception:
            pass
    try:
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))
        before = 0
        if os.path.exists(LOG_FILE):
            before = len(open(LOG_FILE, encoding="utf-8", errors="ignore").read().splitlines())
        cases = [
            ("какая модель открыта в Creo?", "creo_get_active", 1),
            ("найди модель корпус", "models_find", 1),
            (None, "models_where", 1),
            ("сколько всего моделей в базе?", "models_stats", 1),
            (r"прочитай файл D:\AI\repo\SKILL_index.md", "read_file", 1),
            ("что в базе знаний про пружины?", "search_kb", 1),
            ("переведи 150 Нм в кгсм", "calc", 1),
            ("какие накопленные проблемы по трейлам?", "trail_problems", 1),
            ("покажи текущие настройки", "settings_show", 1),
            ("привет", "answer", 1),
            ("найди модель держатель и покажи, где она используется", "models_find", 1),
            ("посмотри деталь", "creo_get_active", 1),
            ("index_state", "index_state", 1),
            ("creo_save", "approval", 1),
            ("у тебя нет доступа к файлам?", "no_refusal", 1),
            ("разбери последний трейл", "trail_analyze", 1),
            ("привет, ты человек?", "chat", 2),
        ]
        results = []
        model_name_holder = None
        think_count = 0
        for i, (q, expected, mode) in enumerate(cases, 1):
            if q is None:
                q = f"Где используется {model_name_holder}?" if model_name_holder else "Где используется модель?"
            
            print(f"{i:2d} Testing: {q[:40]} (mode {mode})")
            r = ask(q, mode)
            answer = r.get("answer", "")
            think = r.get("think", "")
            tools = r.get("log", [])
            
            verdict = "PASS"
            note = ""

            if mode == 2:
                if expected == "chat":
                    if not answer:
                        verdict = "FAIL"
                        note = "empty answer in chat mode"
                else:
                    verdict = "FAIL"
                    note = f"unexpected mode 2, expected {expected}"
            else:
                if expected == "approval":
                    if "[Р РЋР С›Р вЂњР вЂєР С’Р РЋР С›Р вЂ™Р С’Р СњР ВР вЂў]" in answer and expected in tools:
                        pass
                    elif "не подтверждал" in answer.lower():
                        pass
                    else:
                        verdict = "FAIL"
                        note = f"Р В¶Р Т‘Р В°Р В» {expected} Р Р† Р С‘Р Р…РЎРѓРЎвЂљРЎР‚РЎС“Р СР ВµР Р…РЎвЂљР В°РЎвЂ¦ Р В [Р РЋР С›Р вЂњР вЂєР С’Р РЋР С›Р вЂ™Р С’Р СњР ВР вЂў] Р Р† Р С•РЎвЂљР Р†Р ВµРЎвЂљР Вµ"
                elif expected == "no_refusal":
                    refusals = ["нет доступа", "не могу", "как языковая модель", "не имею доступа", "у меня нет"]
                    if any(w in answer.lower() for w in refusals):
                        verdict = "FAIL"
                        note = "отказная фраза в ответе"
                else:
                    if expected != "answer" and expected not in tools:
                        verdict = "FAIL"
                        note = f"ждал {expected}, получил {tools}"
                
                is_direct_call = (q.strip() == expected)
                if not think.strip() and not is_direct_call:
                    note += "; think пустой (предупреждение)"
                if lat_ratio(answer) > 0.25:
                    verdict = "FAIL"
                    note += f"; латиница {lat_ratio(answer):.0%}>25%"
                if "Traceback" in answer:
                    verdict = "FAIL"
                    note += "; Traceback"

            results.append({
                "#": i, "q": q, "expected": expected, "tools": tools,
                "think": bool(think.strip()), "answer": answer[:120],
                "verdict": verdict, "note": note.strip("; "),
            })
            print(f"{i:2d} {verdict} | {q[:50]}")
            if mode == 1 and r.get("think"):
                think_count += 1

        after_lines = open(LOG_FILE, encoding="utf-8", errors="ignore").read().splitlines() if os.path.exists(LOG_FILE) else []
        new_tb = sum(1 for l in after_lines[before:] if "Traceback" in l)
        try:
            fb = post("/feedback", {"token": TOKEN, "query": "qa", "think": "", "tool": "qa",
                                     "result": "qa", "ok": 1, "comment": "qa probe"})
            fb_ok = fb.get("ok") is True
        except Exception as e:
            fb_ok = False
            fb = str(e)
        try:
            st = json.loads(urllib.request.urlopen(BASE + "/status", timeout=10).read())
        except Exception as e:
            st = {"error": str(e)}
        print(f"{datetime.date.today()} {model_name_holder or 'unknown'}")
        print("\n=== SUMMARY ===")
        passed = sum(1 for r in results if r["verdict"] == "PASS")
        failed = sum(1 for r in results if r["verdict"] == "FAIL")
        print(f"PASS {passed} / FAIL {failed}")
        print(f"think: {think_count} из 17")
        print(f"Traceback in new log lines: {new_tb}")
        print(f"feedback ok: {fb_ok}")
        print(f"status: blocks={st.get('blocks')} tools={st.get('tools')}")
        print("\n=== FAIL DETAIL ===")
        for r in results:
            if r["verdict"] == "FAIL":
                print(f"  #{r['#']} {r.get('q','')[:40]} | ожидал {r.get('expected')} | получил {r.get('tools')} | {r.get('note')}")
        with open(r"D:\AI\tools\agent\qa\qa_results.json", "w", encoding="utf-8") as f:
            json.dump({"results": results,
                       "after": {"traceback_new": new_tb, "feedback_ok": fb_ok, "status": st}},
                      f, ensure_ascii=False, indent=2)
        print("\nsaved D:\\AI\\tools\\agent\\qa\\qa_results.json")
    finally:
        if os.path.exists(pid_file):
            os.remove(pid_file)

if __name__ == "__main__":
    login()
    run()

