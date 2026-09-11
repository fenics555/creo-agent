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
