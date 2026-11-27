import json, glob, os, time, sys, hashlib, re, datetime, urllib.request, urllib.error

SESS = os.path.join(os.path.expanduser("~"), ".cline", "data", "sessions")
ALERT = r"D:\AI\log\urn\cline\LOOP_ALERT.txt"
LOG = os.path.join(os.path.expanduser("~"), ".cline", "data", "logs", "code.log")
THRESHOLD = 2
ERR_SIG_THRESHOLD = 3
FAIL_THRESHOLD = 3
WINDOW = 12
TXT_WINDOW = 6
TXT_REPEAT = 3
CYCLE_PAIRS = 2
ERR_MAX_LEN = 4000
# 26.11.2026 (владелец): было 20 — сторож «бибикал» каждые 20 сек на одном и том же
# fail-loop в живой сессии. 300 сек = один сигнал на 5 минут, чтобы не спамить владельца.
COOLDOWN_SEC = 300
ERR_KEYS = ("error", "not found", "too large", "no replacement",
            "\u043d\u0435 \u043d\u0430\u0439\u0434\u0435\u043d", "\u043e\u0448\u0438\u0431\u043a")
BACKEND_PROBES = (
    ("llama.cpp", "http://127.0.0.1:8080/health", "health"),
    ("vllm", "http://127.0.0.1:8000/health", "health"),
    ("vllm_stall", "http://127.0.0.1:8000/health/decode", "stall"),
    ("ollama", "http://127.0.0.1:11434/api/ps", "ps"),
    ("lmstudio", "http://127.0.0.1:1234/v1/models", "health"),
    ("textgen", "http://127.0.0.1:5000/v1/models", "health"),
)
POLL_SEC = 4
STALL_SEC = 110
RECENT_SEC = 300
SPIKE_BYTES = 65536
PROBE_TIMEOUT = 1.5
# 23.11.2026: АВТОУДАЛЕНИЕ ПО ВРЕМЕНИ (не кнопкой). Срок — из дома: D:\AI\log\retention.json,
#   ключ "urn" (сигналы лежат в urn-папке: log\urn\cline\). По умолчанию 14 дней.
RETENTION_FILE = r"D:\AI\log\retention.json"
KEEP_DAYS_DEFAULT = 14
MAX_ALERT_BYTES = 1000000        # страховка: даже внутри срока файл не растёт больше 1 МБ


def keep_days_file():
    """Срок хранения из retention.json (ключ 'urn'); при сбое — 14 дней."""
    try:
        with open(RETENTION_FILE, encoding="utf-8") as f:
            return int(json.load(f).get("urn", KEEP_DAYS_DEFAULT))
    except Exception:
        return KEEP_DAYS_DEFAULT


def prune_alert(path, days):
    """Удаляет записи старше `days` дней. Новый формат строки — с датой 'YYYY-MM-DD HH:MM:SS'.
    Старые строки без даты судятся по дате файла (mtime) — чтобы не удалить свежий файл целиком.
    Возвращает число удалённых строк."""
    if not path or not os.path.exists(path):
        return 0
    days = int(days or KEEP_DAYS_DEFAULT)
    cutoff = datetime.date.today() - datetime.timedelta(days=days)
    try:
        legacy_date = datetime.date.fromtimestamp(os.path.getmtime(path))
    except Exception:
        legacy_date = datetime.date.today()
    kept, dropped = [], 0
    changed = False
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except Exception:
        return 0
    for ln in lines:
        m = re.match(r"^(\d{4})-(\d{2})-(\d{2}) ", ln)
        if m:
            d = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        else:
            # миграция 23.11.2026: строка без даты получает дату файла (иначе не состарится никогда)
            d = legacy_date
            ln = legacy_date.isoformat() + " " + ln
            changed = True
        if d >= cutoff:
            kept.append(ln)
        else:
            dropped += 1
    while kept and len("\n".join(kept).encode("utf-8")) > MAX_ALERT_BYTES:
        kept.pop(0)
        dropped += 1
    if dropped or changed:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(kept) + ("\n" if kept else ""))
        except Exception:
            return 0
    return dropped


def arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


SESSION_ID = arg("--session")
SESS = arg("--sess-dir", SESS)
LOG = arg("--log", LOG)
ALERT = arg("--alert", ALERT)
# 25.11.2026 (владелец): INBOX — файл-инъекция КРАХА для модели (см. emit()).
INBOX = arg("--inbox", r"D:\AI\INBOX.md")
# 26.11.2026: статистика срабатываний (ответ на «сколько раз помог»). hits++ в emit().
STATS = arg("--stats", r"D:\AI\log\urn\cline\loop_watch_stats.json")
# 23.11.2026: срок хранения записей (дней). Перебивается ключом --keep-days, иначе из retention.json.
KEEP_DAYS = int(arg("--keep-days", "0")) or keep_days_file()
WINDOW = int(arg("--window", WINDOW))
TXT_WINDOW = int(arg("--txt-window", TXT_WINDOW))
TXT_REPEAT = int(arg("--txt-repeat", TXT_REPEAT))
STALL_ENABLED = "--stall" in sys.argv
SPIKE_ENABLED = "--spike" in sys.argv
STALL_SEC = int(arg("--stall-sec", STALL_SEC))
RECENT_SEC = int(arg("--recent-sec", RECENT_SEC))
SPIKE_BYTES = int(arg("--spike-bytes", SPIKE_BYTES))
PREV_SIZE = arg("--prev-size")
PROBE_REACHABLE = arg("--probe-reachable")
PROBE_TIMEOUT = float(arg("--probe-timeout", PROBE_TIMEOUT))


def newest():
    if SESSION_ID:
        d = os.path.join(SESS, SESSION_ID)
        return d if os.path.isdir(d) else None
    ds = [d for d in glob.glob(os.path.join(SESS, "*"))
          if os.path.isdir(d) and "__agent_" not in os.path.basename(d)]
    return max(ds, key=os.path.getmtime) if ds else None


def calls_with_results(msgs):
    calls = []
    pending = None
    for m in msgs:
        role = m.get("role")
        c = m.get("content")
        if role == "assistant" and isinstance(c, list):
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    key = str(b.get("name", "")) + "|" + json.dumps(b.get("input", {}), sort_keys=True, ensure_ascii=False)
                    pending = hashlib.md5(key.encode("utf-8")).hexdigest()[:10]
        elif role == "user" and isinstance(c, list):
            rt = ""
            for b in c:
                if isinstance(b, dict) and b.get("type") == "tool_result":
                    rc = b.get("content")
                    if isinstance(rc, list):
                        rt = " ".join(str(x.get("result", "")) + " " + str(x.get("query", "")) for x in rc if isinstance(x, dict))
                    else:
                        rt = str(rc)
            if pending is not None:
                calls.append((pending, rt))
                pending = None
    return calls


def assistant_texts(msgs):
    texts = []
    for m in msgs:
        if m.get("role") != "assistant":
            continue
        c = m.get("content")
        if isinstance(c, list):
            t = " ".join(b.get("text", "") for b in c if isinstance(b, dict) and b.get("type") == "text")
        elif isinstance(c, str):
            t = c
        else:
            t = ""
        t = re.sub(r"\s+", " ", t).strip()
        if t:
            texts.append(t)
    return texts


def norm(t):
    return re.sub(r"[^0-9a-z\u0400-\u04ff]+", " ", t.lower()).strip()


def is_error_result(rt):
    """26.11.2026 (K1/K2): провал подтверждается СТРУКТУРНО, а не словом где угодно.
    Было: `any(k in low for k in ERR_KEYS)` — «error» как подстрока ловил слово
    в ЗАПРОСЕ (движок склеивает result+query), в выводе команды, в тексте файла
    при read_files → ложные fail-loop на нормальной работе.
    Стало: три формы реального провала (по замеру сессий: 43+6+1+1 из 577):
      1) код возврата:  [Command exited with code N] при N != 0;
      2) ошибки-классы: Traceback / PathNotFound / text not found / no replacement;
      3) явный префикс: строка начинается с Error:/ERROR: (после отступа).
    Слово «error» внутри текста БОЛЬШЕ НЕ считается провалом само по себе.
    """
    low = rt.lower()
    # 1) код возврата (основная форма: 43 из 577)
    for m in re.finditer(r"\[command exited with code (\d+)", low):
        if m.group(1) != "0":
            return True
    # 2) ошибки-классы (структурные маркеры инструментов)
    if any(k in low for k in ("traceback (most recent call last)",
                              "pathnotfound", "text not found",
                              "no replacement performed", "no replacement was performed")):
        return True
    # 3) явный префикс ошибки в начале строки (не где угодно)
    for line in low.splitlines():
        s = line.lstrip()
        if s.startswith("error:") or s.startswith("error "):
            return True
    return False


def err_signature(rt):
    s = re.sub(r"\d+", "", rt.lower())
    return re.sub(r"\s+", " ", s).strip()[:120]


def cycle_loop(calls):
    sigs = [h for h, _ in calls]
    n = CYCLE_PAIRS * 2
    if len(sigs) < n:
        return None
    tail = sigs[-n:]
    if tail[0] != tail[1] and tail == [tail[0], tail[1]] * CYCLE_PAIRS:
        return "%s<->%s" % (tail[0], tail[1])
    return None


# 25.11.2026 (владелец): НОВЫЕ ПРИЗНАКИ из крах-скиллов (все — только ФАКТ, без рекомендаций).
PATTERNS = {
    "edit-miss": ("text not found", "editor-mismatch"),        # SKILL_crash-editor-mismatch
    "edit-big": ("too large", "editor_too_large"),             # SKILL_editor_too_large
    "plan-loop": ("план", "plan-loop-replan-no-exec"),         # повтор плана без вызовов
    "migration": ("[migration]", "searchcodebase-migration"),  # маркер миграции
    "path-guess": ("pathnotfound", "path-guessed-by-analogy"), # путь по аналогии
    "buffer": ("(пусто)", "probe-buffer-swallows-output"),     # пустой вывод прогона
    "context-death": ("context length", "cline_longsession_context_death"),
}


def _edit_miss_streak(calls):
    """26.11.2026: считает «text not found» ПОДРЯД (между ними нет успешного editor).
    Точнее ловит «модель долбится в один якорь», отсекает ложные на разных файлах."""
    streak = 0
    best = 0
    for _h, rt in calls:
        low = (rt or "").lower()
        if "text not found" in low or "no replacement performed" in low:
            streak += 1
            best = max(best, streak)
        elif "successfully" in low or "file created" in low or "edited" in low:
            streak = 0  # успешная правка — сброс серии
    return best


def pattern_loop(calls, msgs):
    """Ищет признаки крах-скиллов в результатах вызовов и текстах. Возвращает (kind, key) или None."""
    hits = {}
    for _h, rt in calls:
        low = (rt or "").lower()
        for kind, (mark, _skill) in PATTERNS.items():
            if mark in low:
                hits[kind] = hits.get(kind, 0) + 1
    # 26.11.2026: edit-miss — серия подряд (не «2 в окне»), проверяем ПЕРВОЙ.
    if _edit_miss_streak(calls) >= 2:
        return "edit-miss", PATTERNS["edit-miss"][1]
    for kind, c in hits.items():
        if c >= 2:
            return kind, PATTERNS[kind][1]
    # plan-loop: текст-план повторён 3 раза без вызовов (уже есть text_loop, но с ключом плана)
    txts = assistant_texts(msgs)[-TXT_WINDOW:]
    plans = sum(1 for t in txts if "план" in t.lower() and "вызов" not in t.lower())
    if plans >= 3:
        return "plan-loop", "plan-loop-replan-no-exec"
    return None


def session_messages_path(s):
    p = os.path.join(s, os.path.basename(s) + ".messages.json")
    if os.path.exists(p):
        return p
    meta = os.path.join(s, os.path.basename(s) + ".json")
    try:
        d = json.load(open(meta, encoding="utf-8"))
        mp = d.get("messages_path")
        if mp:
            if not os.path.isabs(mp):
                mp = os.path.join(s, mp)
            if os.path.exists(mp):
                return mp
    except Exception:
        pass
    return None


def _http_get(url):
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as r:
            return r.status, r.read(256)
    except urllib.error.HTTPError as e:
        return e.code, b""
    except Exception:
        return None, b""


def probe_backends():
    if PROBE_REACHABLE == "yes":
        return {"alive": True, "stall": False, "active_model": "forced", "hits": []}
    if PROBE_REACHABLE == "no":
        return {"alive": False, "stall": False, "active_model": None, "hits": []}
    res = {"alive": False, "stall": False, "active_model": None, "hits": []}
    for name, url, kind in BACKEND_PROBES:
        status, body = _http_get(url)
        if status is None:
            continue
        res["alive"] = True
        res["hits"].append((name, kind, status))
        if kind == "stall" and status == 503:
            res["stall"] = True
        elif kind == "ps":
            try:
                data = json.loads(body.decode("utf-8", errors="replace"))
                models = data.get("models") or []
                if models:
                    res["active_model"] = models[0].get("name") or models[0].get("model")
            except Exception:
                pass
    return res


def text_loop(msgs):
    texts = assistant_texts(msgs)[-TXT_WINDOW:]
    norms = [n for n in (norm(t) for t in texts) if len(n) >= 20]
    if len(norms) < TXT_REPEAT:
        return None
    counts = {}
    for n in norms:
        counts[n] = counts.get(n, 0) + 1
    n, c = max(counts.items(), key=lambda kv: kv[1])
    if c >= TXT_REPEAT:
        return texts[-1][:60]
    return None


def check_log(session_id):
    if not os.path.exists(LOG):
        return None
    try:
        lines = open(LOG, encoding="utf-8", errors="replace").read().splitlines()[-5000:]
    except Exception:
        return None
    last = None
    for ln in lines:
        if "Desktop chat prompt completed" in ln and session_id in ln:
            last = ln
    if last and '"finishReason":"aborted"' in last:
        return True
    return None


def check(prev_size=None):
    s = newest()
    if not s:
        return None
    p = session_messages_path(s)
    if not p:
        return None
    if SPIKE_ENABLED and prev_size is not None:
        size = os.path.getsize(p)
        if size - prev_size >= SPIKE_BYTES:
            return (os.path.basename(s), size - prev_size, "SPIKE", True, "context-spike")
    try:
        data = json.load(open(p, encoding="utf-8"))
    except Exception:
        return None
    msgs = data.get("messages", [])
    calls = calls_with_results(msgs)[-WINDOW:]
    if len(calls) >= 2:
        err = {}
        for h, rt in calls:
            if is_error_result(rt):
                err[h] = err.get(h, 0) + 1
        for h, c in err.items():
            if c >= THRESHOLD:
                return (os.path.basename(s), c, h, True, "tool-loop")
        sigs = {}
        for h, rt in calls:
            if is_error_result(rt):
                k = err_signature(rt)
                sigs[k] = sigs.get(k, 0) + 1
        for k, c in sigs.items():
            if c >= ERR_SIG_THRESHOLD:
                return (os.path.basename(s), c, k[:40], True, "error-loop")
        fails = sum(1 for h, rt in calls if is_error_result(rt))
        if fails >= FAIL_THRESHOLD:
            return (os.path.basename(s), fails, "FAILS", True, "fail-loop")
    cyc = cycle_loop(calls)
    if cyc:
        return (os.path.basename(s), CYCLE_PAIRS * 2, "CYCLE", True, "cycle-loop")
    pl = pattern_loop(calls, msgs)
    if pl:
        return (os.path.basename(s), 2, pl[1], True, pl[0])
    tl = text_loop(msgs)
    if tl:
        return (os.path.basename(s), TXT_REPEAT, "TEXT-LOOP", True, "text-loop")
    if STALL_ENABLED:
        idle = time.time() - os.path.getmtime(p)
        if STALL_SEC <= idle < RECENT_SEC:
            pr = probe_backends()
            if pr["alive"] or pr["stall"]:
                return (os.path.basename(s), int(idle), "STALL:" + str(pr["active_model"] or "backend"), True, "generation-stall")
    if check_log(os.path.basename(s)):
        return (os.path.basename(s), 0, "ABORTED", True, "aborted")
    return None


def emit(r):
    # 23.11.2026: в строку добавлена ДАТА (для автоудаления по времени), после записи — чистка старых.
    line = "%s %s LOOP kind=%s session=%s repeats=%d call=%s\n" % (
        time.strftime("%Y-%m-%d"), time.strftime("%H:%M:%S"), r[4], r[0], r[1], r[2])
    try:
        open(ALERT, "a", encoding="utf-8").write(line)
        prune_alert(ALERT, KEEP_DAYS)
    except Exception:
        pass
    # 25.11.2026 (владелец): ИНЪЕКЦИЯ КРАХА в INBOX. Только ФАКТ + имя крах-скилла (без рекомендаций):
    # REVIVE (§5.1-5.2) сам обяжет сверить SKILL_crash_index.md и зафиксировать сбой по конституции.
    SKILL_MAP = {
        "tool-loop": "SKILL_crash_execution-loop", "error-loop": "SKILL_crash_handling",
        "fail-loop": "SKILL_crash_handling", "cycle-loop": "SKILL_crash_execution-loop",
        "text-loop": "SKILL_crash_plan-loop-replan-no-exec", "aborted": "SKILL_crash_session-interruption",
        "stall": "SKILL_crash_cline_longsession_context_death", "context-spike": "SKILL_crash_context-limit-interruption",
        # 26.11.2026 S11: детектор возвращает kind="generation-stall", а не "stall".
        # Без этого ключа .get() не находил → дефолт SKILL_crash_handling (терялся правильный скилл).
        "generation-stall": "SKILL_crash_cline_longsession_context_death",
        # 26.11.2026: маппинг для признаков из PATTERNS (были забыты — в INBOX шёл неверный скилл).
        "edit-miss": "SKILL_crash-editor-mismatch", "edit-big": "SKILL_editor_too_large",
        "plan-loop": "SKILL_crash_plan-loop-replan-no-exec", "migration": "SKILL_crash_searchcodebase-any-pattern-migration-marker",
        "path-guess": "crash_path-guessed-by-analogy", "buffer": "SKILL_crash_probe-buffer-swallows-output",
        "context-death": "SKILL_crash_cline_longsession_context_death",
    }
    skill = SKILL_MAP.get(r[4], "SKILL_crash_handling")
    # 26.11.2026: было "w" (перезапись) — второй сигнал затирал первый. Теперь append,
    # но при размере > 2 КБ файл перезаписывается (защита от роста).
    try:
        if os.path.exists(INBOX) and os.path.getsize(INBOX) > 2048:
            open(INBOX, "w", encoding="utf-8").write("")
        open(INBOX, "a", encoding="utf-8").write(
            "КРАХ — признак %s (повторов %d). Крах-скилл: %s\n" % (r[4], r[1], skill))
    except Exception:
        pass
    # 26.11.2026: счётчик срабатываний по признаку. by_session — видно «одна петля или разные»;
    # ДЕДУП между запусками (seen) — иначе при рестарте старые сигналы снова попадают в hits.
    try:
        st = {}
        if os.path.exists(STATS):
            st = json.load(open(STATS, encoding="utf-8"))
        sess = r[0]
        rec = st.setdefault(r[4], {"hits": 0, "first_ts": "", "last_ts": "",
                                   "by_session": {}, "seen": {}})
        # дедуп: ключ сигнала = сессия|повторы|вызов (не считаем один и тот же дважды)
        key = "%s|%s|%s" % (sess, r[1], r[2])
        seen = rec.setdefault("seen", {})
        if key not in seen:
            now = time.strftime("%Y-%m-%d %H:%M:%S")
            rec["hits"] = rec.get("hits", 0) + 1
            rec["last_ts"] = now
            if not rec.get("first_ts"):
                rec["first_ts"] = now
            bs = rec.setdefault("by_session", {})
            bs[sess] = bs.get(sess, 0) + 1
            seen[key] = now
            # чистим старые ключи seen (держать не больше 200 на признак)
            if len(seen) > 200:
                for k in list(seen.keys())[:100]:
                    del seen[k]
        json.dump(st, open(STATS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    except Exception:
        pass
    return line.strip()


# 23.11.2026: замок живёт РЯДОМ с файлом сигналов (тест-обвязка изолируется сама, т.к. передаёт свой --alert).
LOCK = arg("--lock", os.path.join(os.path.dirname(ALERT), "loop_watch.lock"))
NO_LOCK = "--no-lock" in sys.argv


def pid_alive(pid):
    """Жив ли процесс с таким PID (Windows: OpenProcess; иначе os.kill(pid, 0))."""
    try:
        import ctypes
        h = ctypes.windll.kernel32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
        if h:
            ctypes.windll.kernel32.CloseHandle(h)
            return True
        return False
    except Exception:
        try:
            os.kill(int(pid), 0)
            return True
        except Exception:
            return False


def pid_is_loop_watch(pid):
    """26.11.2026: замок залипал, т.к. PID переиспользован (VS Code занял PID 13248).
    Проверяем не только «жив ли PID», но и «это python/loop_watch, а не чужой процесс»."""
    try:
        import ctypes
        from ctypes import wintypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        if not h:
            return False
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if not ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                return False
            exe = buf.value.lower()
            # 26.11.2026: было `"python" in exe` — слишком широко (любой путь с «python»).
            # Проверяем ИМЯ файла-образа, а не вхождение подстроки.
            base = os.path.basename(exe)
            return base in ("python.exe", "pythonw.exe", "py.exe", "python3.exe") \
                or "loop_watch" in exe
        finally:
            ctypes.windll.kernel32.CloseHandle(h)
    except Exception:
        return False


def acquire_lock():
    """ЗАМОК ЕДИНСТВЕННОГО ЭКЗЕМПЛЯРА (23.11.2026): дом-стиль, как data\\harvest.lock.
    Второй запуск тихо выходит — иначе сигналы дублируются в LOOP_ALERT.txt.
    26.11.2026: осиротевший замок (PID переиспользован чужим процессом) теперь снимается."""
    if NO_LOCK:
        return True
    try:
        with open(LOCK, encoding="utf-8") as f:
            pid = int(json.load(f).get("pid", 0))
        if pid and pid != os.getpid() and pid_alive(pid) and pid_is_loop_watch(pid):
            print("loop_watch already running: PID", pid, "- exit (lock:", LOCK + ")")
            return False
        elif pid and pid != os.getpid() and pid_alive(pid):
            print("stale lock: PID", pid, "is not loop_watch (PID reused) - taking over")
    except Exception:
        pass
    try:
        os.makedirs(os.path.dirname(LOCK), exist_ok=True)
        with open(LOCK, "w", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(), "started": time.strftime("%Y-%m-%d %H:%M:%S")}, f, ensure_ascii=False)
    except Exception:
        pass
    return True


def release_lock():
    """Снимает замок, только если он наш (по PID)."""
    try:
        with open(LOCK, encoding="utf-8") as f:
            if int(json.load(f).get("pid", 0)) == os.getpid():
                os.remove(LOCK)
    except Exception:
        pass


if __name__ == "__main__":
    # 23.11.2026: ОДИН экземпляр сторожа (pid-lock). Второй запуск выходит с сообщением.
    if not acquire_lock():
        sys.exit(0)
    import atexit
    atexit.register(release_lock)
    # 23.11.2026: автоудаление по времени — при КАЖДОМ запуске (ручном, разовом, фоновом).
    _dropped = prune_alert(ALERT, KEEP_DAYS)
    if _dropped:
        print("pruned", _dropped, "old alert line(s), keep_days =", KEEP_DAYS)
    if "--once" in sys.argv:
        prev = int(PREV_SIZE) if PREV_SIZE is not None else None
        r = check(prev_size=prev)
        print("ALERT" if (r and r[3]) else "OK", r or "")
        if r and r[3]:
            emit(r)
    else:
        print("watching", SESS, "toolwin", WINDOW, "txtwin", TXT_WINDOW, "txtrepeat", TXT_REPEAT,
              "stall", STALL_ENABLED, "spike", SPIKE_ENABLED)
        last = {"sig": None, "ts": 0.0, "size": {}}
        while True:
            s = newest()
            name = os.path.basename(s) if s else ""
            r = check(prev_size=last["size"].get(name))
            if r and r[3]:
                sig = "%s|%s|%s" % (r[4], r[0], r[2])
                now = time.time()
                if not (sig == last["sig"] and now - last["ts"] < COOLDOWN_SEC):
                    last["sig"] = sig
                    last["ts"] = now
                    # 26.11.2026 (владелец): убран "\a" (bell) — в фоне он бесконечно
                    # бибикал. Сигнал теперь только в LOOP_ALERT.txt + INBOX.
                    print(emit(r))
            p = session_messages_path(s) if s else None
            if p:
                last["size"][name] = os.path.getsize(p)
            time.sleep(POLL_SEC)

