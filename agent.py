# -*- coding: utf-8 -*-
"""АГЕНТ v15 — agent.py (полная сборка)
ThreadingHTTPServer + стриминг токенов + параллельные инструменты + планировщик.
Витрина живёт в data/ui/index.html; константы PAGE больше нет.
"""
import json, re, os, socket, threading, time, datetime
from concurrent.futures import ThreadPoolExecutor
import subprocess, sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import core
from core import log, trace
import settings
import pdf_tools

# === v15: стриминг токенов ===
import urllib.request as _ur
LIVE_TOK = {}
LIVE_THINK = {}
_orig_core_post = core.post


def _stream_post(path, payload, *ar, **kw):
    push = getattr(threading.current_thread(), "_tokpush", None)
    if path != "/api/chat" or not push or not settings.get("stream_tokens"):
        return _orig_core_post(path, payload, *ar, **kw)
    payload = dict(payload); payload["stream"] = True
    parts = []; state = {"buf": "", "mode": None}; lastj = {}
    thparts = []
    req = _ur.Request(core.OLL + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    try:
        with _ur.urlopen(req, timeout=600) as resp:
            for line in resp:
                line = line.strip()
                if not line: continue
                try: j = json.loads(line)
                except Exception: continue
                lastj = j
                t = (j.get("message") or {}).get("content") or ""
                tth = (j.get("message") or {}).get("thinking") or ""
                if tth:
                    thparts.append(tth)
                    _tc = getattr(threading.current_thread(), "_tokclient", None)
                    if _tc is not None:
                        LIVE_THINK.setdefault(_tc, []).append(tth)
                if tth and not t:
                    continue
                if t:
                    parts.append(t)
                    if state["mode"] != "tool":
                        state["buf"] += t
                    if state["mode"] is None:
                        if len(state["buf"]) >= 8:
                            if state["buf"].lstrip().startswith("[TOOL"):
                                state["mode"] = "tool"
                            else:
                                state["mode"] = "ans"; push(state["buf"]); state["buf"] = ""
                    elif state["mode"] == "ans":
                        push(state["buf"]); state["buf"] = ""
    except Exception:
        p2 = dict(payload); p2["stream"] = False
        return _orig_core_post(path, p2, *ar, **kw)
    r = {"message": {"content": "".join(parts), "thinking": "".join(thparts)}}
    for _kk in ("prompt_eval_count", "eval_count", "prompt_eval_duration", "eval_duration"):
        if _kk in lastj: r[_kk] = lastj[_kk]
    return r


core.post = _stream_post
_post_before_think = core.post


def _post_think_off(path, payload, *ar, **kw):
    if path == "/api/chat" and isinstance(payload, dict):
        payload = dict(payload)
        if int(settings.get("think_mode") or 0) == 0:
            payload["think"] = False
    return _post_before_think(path, payload, *ar, **kw)


core.post = _post_think_off
# === конец стриминга ===

import tools_registry as TR
import scanner
import users
import chat_tools
import panel
import vision_tools as VI


def _role_check(client, tool):
    """Вердикт: None = роль разрешает, строка = сообщение о запрете."""
    if not client or not tool:
        return None
    prof = users.get_profile(client)
    if not prof:
        return None
    role = prof.get("role", "Инженер")
    if users.role_denied(role, tool):
        return "🛔 роль «%s» не может выполнить «%s» (запрет администратора)" % (role, tool)
    return None


HOST, PORT = "0.0.0.0", 8765
HOSTNAME = socket.gethostname()
PENDING = {}
LIVE = {}
LAST_META = {"p": 0, "r": 0}
UI_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ui", "index.html")
_UI_CACHE = [0, b""]
STUB_PAGE = ("<html><head><meta charset='utf-8'><title>АГЕНТ v15</title></head>"
             "<body style='background:#1B1C1E;color:#E8E8E8;font:14px Segoe UI,sans-serif;padding:40px'>"
             "<h2>ВИТРИНА НЕ НАЙДЕНА</h2><p>Положи index.html в D:\\AI\\tools\\agent\\data\\ui\\</p></body></html>")

DEFAULT_PROTO = """# ПРОТОКОЛ ИНЖЕНЕРА-НАПАРНИКА
РОЛЬ
Ты — старший инженер-конструктор КБ, напарник пользователя. Говоришь кратко, по делу, только проверенными фактами.
Скиллы в репо — справочники; при противоречии этот протокол главный.
ЯЗЫК
Думаешь и отвечаешь ТОЛЬКО на русском. Исключение — имена файлов, переменные, команды, код.
ФОРМАТ — ОДИН БЛОК НА ХОД
После ровно ОДИН блок, ничего до и после:
[TOOL: имя_инструмента] {"параметр": "значение"} [/TOOL]
или
[ANSWER] готовый ответ [/ANSWER]
ПРОТИВ ВЫДУМЫВАНИЯ
ЖИВЫЕ ДАННЫЕ (Creo, файлы, трейлы, база, 1С, настройки, история, пружины, стандарты, масса) — ТОЛЬКО через инструмент.
Справочные факты — через search_kb/read_file. Пока нет [РЕЗУЛЬТАТ] — не называй имён, шифров, чисел.
Доступ к базе, файлам и Creo у тебя ЕСТЬ — через инструменты из списка ниже. Никогда не говори «у меня нет доступа» — просто вызывай инструмент.
ПОРЯДОК
1. Определи, каких данных не хватает. 2. Вызови инструмент, жди [РЕЗУЛЬТАТ].
Мало — следующий; достаточно — [ANSWER] только из фактов [РЕЗУЛЬТАТ].
После [РЕЗУЛЬТАТ] НИКОГДА не отвечай «не понял/уточните» — данные уже в [РЕЗУЛЬТАТ],
кратко перескажи их в [ANSWER].
ПИШУЩИЕ ОПЕРАЦИИ
[СОГЛАСОВАНИЕ] меняет данные; вызывай только по прямой просьбе.
ПРИМЕРЫ
«какая модель открыта в Creo?» → [TOOL: creo_get_active] {} [/TOOL]
после [РЕЗУЛЬТАТ] → [ANSWER] Активная модель — korpus.prt [/ANSWER]
«привет» → [ANSWER] Привет! С чем помочь по Creo? [/ANSWER]"""


def load_skill(name):
    p = core.REPO / name
    try: return p.read_text(encoding="utf-8") if p.exists() else ""
    except Exception: return ""


_CORE = (
    "creo_get_active", "creo_status", "creo_session", "creo_list_files",
    "models_find", "models_where", "models_stats", "usage_state",
    "search_kb", "read_file", "trail_predict", "trail_problems",
    "settings_show", "help", "tools_help",
)
_SYS_CACHE = {}


def build_system():
    if _SYS_CACHE.get("v"): return _SYS_CACHE["v"]
    p = load_skill("SKILL_agent_protocol.md") or DEFAULT_PROTO
    core_lines, rest = [], []
    for t in TR.TOOLS:
        ps = ", ".join(t.get("params", {}).keys()) if t.get("params") else ""
        d = (t.get("desc") or "").strip()
        if len(d) > 45: d = d[:43].rstrip(" ,.;:-") + "…"
        line = "- %s(%s) — %s%s" % (t["name"], ps, d, " [СОГЛАСОВАНИЕ]" if t.get("approval") else "")
        (core_lines if t["name"] in _CORE else rest).append(line)
    tail = "=== ТВОИ ИНСТРУМЕНТЫ — ОСНОВНЫЕ (частые, полные) ===\n" + "\n".join(core_lines)
    tail += "\n\n=== ПРОЧИЕ ИНСТРУМЕНТЫ (только имена; описание блока — tools_help block=<имя>) ===\n"
    tail += ", ".join(sorted({t["name"] for t in TR.TOOLS if t["name"] not in _CORE}))
    tm = int(settings.get("think_mode") or 0)
    if tm == 0:
        think_rule = "=== РАЗМЫШЛЕНИЯ: запрещены. Не выводи [THINK]...[/THINK]. Сразу один блок: [TOOL] или [ANSWER]."
    elif tm == 1:
        think_rule = ("=== РАЗМЫШЛЕНИЯ (кратко, максимум 4 строки):\n1) суть задачи;\n2) объект;\n3) какой инструмент;\n4) что НЕ подходит.\nБлок: [THINK]...[/THINK], затем один блок: [TOOL] или [ANSWER].")
    else:
        think_rule = ("=== РАЗМЫШЛЕНИЯ (полно, на русском, 5-8 строк):\nнормализуй запрос;\nэтапы, если задача сложная;\nпочему именно этот инструмент;\nкакие альтернативы отверг и почему.\nБлок: [THINK]...[/THINK], затем один блок: [TOOL] или [ANSWER].\nПРИМЕР:\n[THINK]\nНормализация: проверить активную модель.\nЭтапы: один.\nИнструмент: creo_get_active — читает живую сессию.\nОтверг: models_find — это поиск по базе, не сессия.\n[/THINK]\n[TOOL: creo_get_active] {} [/TOOL]")
    _SYS_CACHE["v"] = p + "\n\n" + tail + "\n\n" + think_rule
    return _SYS_CACHE["v"]


def _scheduler():
    last_day = ""
    while True:
        try:
            now = datetime.datetime.now()
            if settings.get("night_enable"):
                hh = int(settings.get("night_hour") or 2); mm = int(settings.get("night_minute") or 0)
                if now.hour == hh and now.minute == mm and now.strftime("%Y-%m-%d") != last_day:
                    last_day = now.strftime("%Y-%m-%d")
                    for t in str(settings.get("night_tasks") or "scan,index,usage").split(","):
                        t = t.strip()
                        log("night start: %s" % t)
                        try:
                            if t == "scan": scanner.scan_models()
                            elif t == "index": scanner.index_all()
                            elif t == "usage":
                                import usage_tools; usage_tools.build_usage(True)
                            elif t == "backup":
                                import backup_tools; backup_tools.tool_make()
                        except Exception as e:
                            log("night %s err: %s" % (t, e))
                        else:
                            log("night ok: %s" % t)
                    log("night run done")
        except Exception:
            pass
        time.sleep(30)


def beh():
    steps = int(settings.get("steps_max") or 6)
    if settings.get("auto_mode"):
        return ({"temperature": (settings.get("auto_temperature") or 10) / 100.0,
                 "top_p": float(settings.get("top_p") or 0.9),
                 "num_predict": int(settings.get("num_predict") or 1536), "num_ctx": int(settings.get("num_ctx") or 8192)}, steps)
    return ({"temperature": (settings.get("creativity") or 30) / 100.0,
             "top_p": float(settings.get("top_p") or 0.9),
             "num_predict": int(settings.get("num_predict") or 1024), "num_ctx": int(settings.get("num_ctx") or 8192)}, steps)


def parse_model(text):
    THINK_TAGS = [
        (r"<think>([\s\S]*?)</think>", re.S),
        (r"<\|channel\|>thought\s*([\s\S]*?)\s*<\|channel\|>", re.S),
        (r"<thought>([\s\S]*?)</thought>", re.S | re.I),
        (r"\[THINK\]\s*([\s\S]*?)\s*\[/THINK\]", re.S),
    ]
    think_text = ""
    for pat, flags in THINK_TAGS:
        if think_text: break
        m = re.search(pat, text, flags)
        if m:
            think_text = m.group(1).strip()
            text = (text[:m.start()] + text[m.end():]).strip()
    m = re.search(r"\[TOOL:\s*([A-Za-z0-9_]+)\s*\]\s*({.*?})\s*\[/TOOL\]", text, re.S)
    if m:
        try: args = json.loads(m.group(2))
        except Exception: args = {}
        if TR.get(m.group(1)): return "tool", m.group(1), args, think_text
    m = re.search(r"\[TOOL:\s*([A-Za-z0-9_]+)\s*\]", text)
    if m and TR.get(m.group(1)):
        rest = text[m.end():m.end() + 800]
        args = {}
        mj = re.search(r"\s*({.*?})", rest, re.S)
        if mj:
            try: args = json.loads(mj.group(1))
            except Exception: args = {}
        return "tool", m.group(1), args, think_text
    m = re.search(r"\[TOOL\]\s*([A-Za-z0-9_]+)\s*({.*?})?\s*(?:\[/TOOL\])?", text, re.S)
    if m and TR.get(m.group(1)):
        args = {}
        if m.group(2):
            try: args = json.loads(m.group(2))
            except Exception: args = {}
        return "tool", m.group(1), args, think_text
    for mm in re.finditer(r"^\s*([A-Za-z0-9_]+)\s*({[^\n]+})\s*$", text, re.M):
        if TR.get(mm.group(1)):
            try: args = json.loads(mm.group(2))
            except Exception: args = {}
            return "tool", mm.group(1), args, think_text
    m = re.search(r"\[ANSWER\]\s*(.*?)\[/ANSWER\]", text, re.S)
    if m: return "answer", m.group(1).strip(), None, think_text
    if "[ANSWER]" in text and "[/ANSWER]" not in text:
        return "answer", text.split("[ANSWER]", 1)[1].strip(), None, think_text
    ts = text.strip()
    if TR.get(ts): return "tool", ts, {}, think_text
    return "invalid", text.strip(), None, think_text


_NUDGE = "[СЛУЖЕБНОЕ] Ответ не в формате. Дай ровно один блок: [TOOL: имя] {\"параметр\": \"значение\"} [/TOOL] или [ANSWER] краткий ответ по-русски [/ANSWER]. Слово «текст» само по себе — не ответ. Ничего до и после блока."
_ACCESS_NUDGE = "[СЛУЖЕБНОЕ] Неверно. Доступ к базе, файлам и Creo у тебя ЕСТЬ через инструменты (список «ТВОИ ИНСТРУМЕНТЫ» выше). Никогда не отвечай «нет доступа». Повтори ровно один блок: [TOOL: имя] {\"параметр\": \"значение\"} [/TOOL] или [ANSWER] ответ [/ANSWER]."
_REFUSAL = ("извините", "не могу", "не имею доступа", "нет доступа", "моя функциональность",
            "виртуальной среде", "не понял", "уточните", "переформулируй", "как языковая модель",
            "к сожалению, я", "буду отвечать", "какой у вас вопрос", "давайте начнём")


def _refusal(text):
    lo = (text or "").lower()
    return any(w in lo for w in _REFUSAL)


def hist_block(client):
    c = core.db()
    rows = c.execute("SELECT q,a FROM history WHERE client=? ORDER BY id DESC LIMIT 8", (client,)).fetchall()
    c.close()
    out = []
    for q, a in reversed(rows):
        out.append({"role": "user", "content": q[:500]})
        out.append({"role": "assistant", "content": a[:800]})
    return out


def run_loop(messages, client, has_link=False, on_step=None):
    opts, steps_max = beh()
    LAST_META.update(p=0, r=0)
    steps_log, last_res, sig_prev, invalid_cnt = [], "", None, 0

    def _log(line): steps_log.append(line); LIVE.setdefault(client, []).append(line)

    for step in range(steps_max):
        r = None
        for attempt in (1, 2):
            try:
                use_opts = dict(opts)
                if invalid_cnt: use_opts = dict(use_opts, temperature=0)
                _thk = int(settings.get("think_mode") or 0) > 0
                r = core.post("/api/chat", {"model": settings.model_for("chat"),
                                            "stream": False, "think": _thk, "options": use_opts, "messages": messages}, t=600)
                break
            except Exception as e:
                if attempt == 1 and "500" in str(e):
                    time.sleep(2); continue
                return {"answer": "ошибка модели: %s" % e, "think": "", "steps": step + 1, "log": steps_log}
        raw = (r.get("message") or {}).get("content") or ""
        try: LAST_META["p"] += r.get("prompt_eval_count") or 0; LAST_META["r"] += r.get("eval_count") or 0
        except Exception: pass
        kind, payload, args, think = parse_model(raw)
        think = think or (((r.get("message") or {}).get("thinking") or "").strip())
        if think and (int(settings.get("think_in_log") or 0) or int(settings.get("log_mode") or 1) >= 2):
            _log("[THINK] %s" % think[:400])
        if kind == "answer" and (_refusal(payload) or (len(payload) < 80 and payload.strip().lower() in _NUDGE.lower())):
            _log("refusal/echo_guard"); kind, payload = "invalid", raw
        if kind == "answer":
            used_web = any("web_fetch" in s for s in steps_log)
            if has_link and not used_web and step < steps_max - 1 and len(payload) < 400:
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": "[СЛУЖЕБНОЕ] В задаче была ссылка http — сначала прочитай её через web_fetch, потом отвечай."})
                _log("web_nudge"); continue
            txt = payload
            if len(txt) < 40 and last_res: txt = last_res + "\n\n" + txt
            return {"answer": txt, "think": think, "steps": step + 1, "log": steps_log}
        if kind == "answer" and len(payload) < 80 and payload.strip().lower() in _NUDGE.lower():
            _log("echo_guard: %r" % payload[:40]); kind, payload = "invalid", raw
        if kind == "invalid":
            invalid_cnt += 1
            if last_res and len(payload or "") > 150 and not _refusal(payload):
                _log("parse_invalid -> проза после результата = ответ")
                return {"answer": payload, "think": think, "steps": step + 1, "log": steps_log}
            if invalid_cnt < 3:
                nudge = _ACCESS_NUDGE if _refusal(payload) else _NUDGE
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": nudge})
                _log("parse_invalid"); continue
            pl = (payload or "").strip()
            tail = (" Инструмент вернул: «%s»." % last_res[:200]) if last_res else ""
            if _refusal(pl) or (len(pl) < 80 and pl.lower() in _NUDGE.lower()):
                pl = "Ответ модели не распознан." + tail + " Уточни запрос (пример: models_where q=<имя детали>) или введи прямую команду инструмента."
            return {"answer": pl, "think": think, "steps": step + 1, "log": steps_log}
        name = payload
        sig = (name, json.dumps(args, sort_keys=True, ensure_ascii=False))
        if sig == sig_prev:
            return {"answer": last_res or "зацикливание остановлено", "think": think, "steps": step + 1, "log": steps_log}
        sig_prev = sig
        if settings.get("parallel_tools"):
            others = []
            for m in re.finditer(r"\[TOOL:\s*([A-Za-z0-9_]+)\s*\]\s*({.*?})\s*\[/TOOL\]", raw, re.S):
                try: aa = json.loads(m.group(2))
                except Exception: aa = {}
                tt = TR.get(m.group(1))
                if tt and not tt.get("approval"): others.append((m.group(1), aa))
            others = [o for o in others if (o[0], json.dumps(o[1], sort_keys=True, ensure_ascii=False)) != (name, json.dumps(args, sort_keys=True, ensure_ascii=False))]
            if len(others) > 1:
                def _one(oa):
                    nn, aa2 = oa
                    msg = _role_check(client, nn)
                    if msg:
                        return "%s → %s" % (nn, msg)
                    tt = TR.get(nn)
                    try: return "%s → %s" % (nn, str(tt["fn"](**aa2))[:600])
                    except Exception as e: return "%s → ошибка: %s" % (nn, e)
                try:
                    with ThreadPoolExecutor(max_workers=4) as ex: res = "\n".join(ex.map(_one, others))
                    _log("parallel[%d]: %s" % (len(others), ", ".join(o[0] for o in others)))
                    last_res = res; sig_prev = sig
                    messages.append({"role": "assistant", "content": raw})
                    messages.append({"role": "user", "content": "[РЕЗУЛЬТАТ parallel]: %s" % res[:4000]})
                    continue
                except Exception: pass
        t = TR.get(name)
        if not t:
            res = "нет такого инструмента: %s" % name
        elif msg := _role_check(client, name):
            res = msg
            _log("%s(%s) → ЗАПРЕТ РОЛИ" % (name, "без параметров" if not args else json.dumps(args, ensure_ascii=False)))
        elif t.get("approval"):
            pid = datetime.datetime.now().strftime("%H%M%S%f")
            PENDING[pid] = {"name": name, "args": args, "client": client, "messages": messages, "raw": raw}
            return {"answer": "[СОГЛАСОВАНИЕ] операция %s ждёт подтверждения пользователя (id %s)" % (name, pid),
                    "think": think, "steps": step + 1, "log": steps_log}
        else:
            t0 = time.time()
            try: res = str(t["fn"](**args))
            except Exception as e: res = "ошибка исполнения %s: %s" % (name, e)
            trace("AGENT %s" % name, "OK", int((time.time() - t0) * 1000))
            _log("%s(%s) → %s" % (name, "без параметров" if not args else json.dumps(args, ensure_ascii=False), res[:120]))
        last_res = res
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": "[РЕЗУЛЬТАТ %s]: %s" % (name, res[:4000])})
    return {"answer": last_res or "не уложился в шаги", "think": think, "steps": steps_max, "log": steps_log}


def ask(q, client, image=None, on_step=None):
    q2 = VI.attach(q, image, client)
    LIVE[client] = []
    name = q.strip()
    t = TR.get(name)
    if t and not image:
        if msg := _role_check(client, name):
            return {"answer": msg, "think": "", "steps": 1, "log": ["%s(прямой вызов) → ЗАПРЕТ РОЛИ" % name]}
        if t.get("approval"):
            pid = datetime.datetime.now().strftime("%H%M%S%f")
            PENDING[pid] = {"name": name, "args": {}, "client": client, "messages": [], "raw": ""}
            return {"answer": "[СОГЛАСОВАНИЕ] операция %s ждёт подтверждения пользователя (id %s)" % (name, pid), "think": "", "steps": 1, "log": ["%s(прямой вызов)" % name]}
        t0 = time.time()
        try:
            try: res = str(t["fn"]())
            except TypeError: res = str(t["fn"]({k: "" for k in t.get("params", {})}))
        except Exception as e: res = "ошибка исполнения %s: %s" % (name, e)
        trace("AGENT %s" % name, "OK", int((time.time() - t0) * 1000))
        c = core.db()
        c.execute("INSERT INTO history(client,q,a,ts) VALUES(?,?,?,?)", (client, q, res[:2000], datetime.datetime.now().isoformat()))
        c.commit(); c.close()
        return {"answer": res, "think": "", "steps": 1, "log": ["%s(прямой вызов) → %s" % (name, res[:120])]}
    q2 = q2 + "\n\n[СЛУЖЕБНОЕ: отвечай только по-русски. Один ход = один [TOOL] или один [ANSWER]. Никакого текста до и после блока.]"
    messages = [{"role": "system", "content": build_system()}] + hist_block(client) + [{"role": "user", "content": q2}]
    _ta = time.time()
    LIVE_TOK[client] = []
    LIVE_THINK[client] = []

    def _push(t): LIVE_TOK.setdefault(client, []).append(t)
    threading.current_thread()._tokpush = _push
    threading.current_thread()._tokclient = client
    r = run_loop(messages, client, has_link=("http" in q), on_step=on_step)
    if int(settings.get("log_mode") or 1) >= 1:
        r.setdefault("log", []).append("⏱ %dмс · 🔢 %d ток (промт %d + ответ %d) · шагов: %d" % (int((time.time() - _ta) * 1000), LAST_META["p"] + LAST_META["r"], LAST_META["p"], LAST_META["r"], r.get("steps", 1)))
    c = core.db()
    c.execute("INSERT INTO history(client,q,a,ts) VALUES(?,?,?,?)", (client, q, r["answer"][:2000], datetime.datetime.now().isoformat()))
    c.commit(); c.close()
    return r


def do_approve(pid, okf):
    p = PENDING.pop(pid, None)
    if not p: return {"res": "заявка не найдена"}
    if not okf: return {"res": "отменено пользователем"}
    t = TR.get(p["name"])
    if msg := _role_check(p.get("client"), p["name"]):
        return {"res": msg}
    try: res = str(t["fn"](**p["args"]))
    except Exception as e: return {"res": "ошибка исполнения: %s" % e}
    msgs = p.get("messages")
    if msgs:
        msgs.append({"role": "assistant", "content": p.get("raw", "")})
        msgs.append({"role": "user", "content": "[РЕЗУЛЬТАТ %s]: %s" % (p["name"], res[:4000])})
        r = run_loop(msgs, p.get("client"), has_link=False)
        return {"res": res, "answer": r["answer"], "think": r.get("think", ""), "log": r.get("log", [])}
    return {"res": res}


def _serve_ui(handler):
    try:
        mt = int(os.path.getmtime(UI_FILE))
        if _UI_CACHE[0] != mt:
            _UI_CACHE[0] = mt
            _UI_CACHE[1] = open(UI_FILE, "rb").read()
        b = _UI_CACHE[1]
    except Exception:
        b = STUB_PAGE.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Content-Length", str(len(b)))
    handler.end_headers()
    handler.wfile.write(b)


class Hd(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _j(self, d, code=200):
        b = json.dumps(d, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) or b"{}"
        try: return json.loads(raw)
        except Exception:
            s = raw.decode("utf-8-sig", "ignore")
            if s.lstrip().startswith("{"):
                try: return json.loads(s.replace('\\"', '"'))
                except Exception: return {}
            return {}

    def _client(self, b):
        u = users.token_info(b.get("token") or self.headers.get("X-Token") or "")
        return u["login"] if u else None

    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/status":
            token = self.headers.get("X-Token") or ""
            cl2 = users.token_info(token)
            prof = users.get_profile(cl2["login"]) if cl2 else None
            tail = ""
            try:
                jf = core.REPO / "Трейлы" / "TRAIL_JOURNAL.md"
                if jf.exists():
                    tail = "\n".join(jf.read_text(encoding="utf-8", errors="ignore").splitlines()[-8:])
            except Exception:
                tail = ""
            self._j({"host": HOSTNAME, "model": settings.get("llm_model"), "blocks": len(TR.BLOCKS),
                     "tools": len(TR.TOOLS), "user": prof,
                     "is_manager": users.can_manage_users(prof["login"]) if prof else False,
                     "trails": tail})
            return
        elif p == "/pdfpages":
            if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"})
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get("name", [""])[0]
            if not name: return self._j({"error": "no name"})
            self._j(pdf_tools.pdf_pages(name))
            return
        elif p == "/pdfimg":
            if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"})
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get("name", [""])[0]
            page = qs.get("page", ["1"])[0]
            if not name: return self._j({"error": "no name"})
            self._j(pdf_tools.pdf_img(name, page))
            return
        elif p == "/pdfstatus":
            if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"})
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get("name", [""])[0]
            if not name: return self._j({"error": "no name"})
            self._j(pdf_tools.pdf_status(name))
            return
        elif p == "/children":
            if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"})
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get("name", [""])[0]
            if not name: return self._j({"error": "no name"})
            out = []
            try:
                c = core.db()
                for tbl in ("usage", "bom", "links"):
                    try:
                        rows = c.execute("SELECT child FROM %s WHERE parent LIKE ?" % tbl, ("%" + name + "%",)).fetchall()
                        out = [r[0] for r in rows]
                        if out: break
                    except Exception:
                        continue
                c.close()
            except Exception as e:
                self._j({"error": str(e)}); return
            self._j({"name": name, "children": out[:200]})
            return
        elif p == "/pdfregistry":
            if not users.token_info(self.headers.get("X-Token") or ""): return self._j({"error": "no token"})
            try:
                c = core.db()
                rows = c.execute("SELECT path, mtime FROM files").fetchall()
                c.close()
            except Exception as e:
                self._j({"error": str(e)}); return
            bydir = {}
            for path, mt in rows:
                bydir.setdefault(os.path.dirname(path), {})[os.path.basename(path).lower()] = (path, mt)
            pairs = []
            for d, fs in bydir.items():
                for nm, (path, mt) in fs.items():
                    if not nm.endswith(".drw"): continue
                    stem = nm[:-4]
                    pdf = fs.get(stem + ".pdf")
                    verdict = "нет pdf" if not pdf else ("актуален" if pdf[1] >= mt else "УСТАРЕЛ")
                    pairs.append({"name": stem, "dir": d, "drw": path, "pdf": pdf[0] if pdf else "",
                                  "drw_mtime": mt, "pdf_mtime": pdf[1] if pdf else 0, "verdict": verdict})
                    if len(pairs) >= 500: break
            pairs.sort(key=lambda r: (r["verdict"] != "УСТАРЕЛ", r["name"]))
            self._j({"pairs": pairs, "total": len(pairs)})
            return
        elif p == "/panel":
            d = panel.build()
            _ui = users.token_info(self.headers.get("X-Token") or "")
            if not (_ui and users.is_admin(_ui["login"])):
                d["groups"] = [g for g in d.get("groups", []) if "НАСТРОЙКИ" not in str(g.get("title", "")).upper()]
                d.pop("settings", None)
            self._j(d)
            return
        elif p == "/log":
            _tk = users.token_info(self.headers.get("X-Token") or "")
            if _tk and not users.is_admin(_tk["login"]):
                c = core.db()
                rows = c.execute("SELECT q,a,ts FROM history WHERE client=? ORDER BY id DESC LIMIT 40", (_tk["login"],)).fetchall()
                c.close()
                self._j({"log": "\n".join("%s · %s → %s" % (ts[:16], q, a[:80]) for q, a, ts in reversed(rows)) or "история пуста"})
                return
            else:
                try:
                    txt = core.LOGF.read_text(encoding="utf-8", errors="ignore").splitlines()
                    self._j({"log": "\n".join(txt[-80:])})
                    return
                except Exception:
                    self._j({"log": "лога нет"})
                    return
        elif p == "/settings":
            self._j({"items": settings.list_ui()})
            return
        elif p == "/livetoks":
            _cl6 = users.token_info(self.headers.get("X-Token") or "")
            qs = parse_qs(urlparse(self.path).query)
            last = int((qs.get("last") or ["0"])[0])
            toks = LIVE_TOK.get(_cl6["login"] if _cl6 else "", [])
            self._j({"toks": toks[last:], "last": len(toks)})
            return
        elif p == "/livethink":
            _cl7 = users.token_info(self.headers.get("X-Token") or "")
            qs7 = parse_qs(urlparse(self.path).query)
            last7 = int((qs7.get("last") or ["0"])[0])
            ths = LIVE_THINK.get(_cl7["login"] if _cl7 else "", [])
            self._j({"toks": ths[last7:], "last": len(ths)})
            return
        elif p == "/livesteps":
            _cl4 = users.token_info(self.headers.get("X-Token") or "")
            qs = parse_qs(urlparse(self.path).query)
            last = int((qs.get("last") or ["0"])[0])
            lines = LIVE.get(_cl4["login"] if _cl4 else "", [])
            self._j({"lines": lines[last:], "last": len(lines)})
            return
        elif p == "/fleet/info":
            tail = ""
            try:
                jf = core.REPO / "Трейлы" / "TRAIL_JOURNAL.md"
                if jf.exists():
                    tail = "\n".join(jf.read_text(encoding="utf-8", errors="ignore").splitlines()[-10:])
            except Exception: pass
            self._j({"tail": tail})
            return
        else:
            _serve_ui(self)

    def do_POST(self):
        p = urlparse(self.path).path
        b = self._body()
        if p == "/login":
            r = users.check_login(b.get("login"), b.get("pw") or b.get("password"))
            self._j(r or {"ok": False}); return
        if p == "/register":
            okf = users.add_user(b.get("login"), b.get("pw") or b.get("password"))
            self._j({"msg": "пользователь создан" if okf else "логин занят или пустой"}); return
        cl = self._client(b)
        if not cl:
            self._j({"error": "нужен вход"}, 401); return
        if p == "/ask":
            self._j(ask(b.get("q") or "", cl, b.get("image")))
        elif p == "/ask_stream":
            import queue as _q
            qq = _q.Queue(); holder = {}

            def _cb(line): qq.put(line)

            def _run():
                try: holder["r"] = ask(b.get("q") or "", cl, b.get("image"), on_step=_cb)
                except Exception as e: holder["r"] = {"answer": "ошибка: %s" % e, "log": []}
                finally: qq.put(None)
            threading.Thread(target=_run, daemon=True).start()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            while True:
                item = qq.get()
                if item is None: break
                self.wfile.write(("data: %s\n\n" % json.dumps({"step": item}, ensure_ascii=False)).encode()); self.wfile.flush()
            self.wfile.write(("data: %s\n\n" % json.dumps({"done": holder.get("r", {})}, ensure_ascii=False)).encode()); self.wfile.flush()
            return
        elif p == "/approve":
            self._j(do_approve(b.get("pid"), b.get("ok")))
        elif p == "/setmodel":
            settings.set_val("llm_model", b.get("model")); self._j({"ok": True})
        elif p == "/setauto":
            settings.set_val("auto_mode", 1 if b.get("on") else 0); self._j({"ok": True})
        elif p == "/feedback":
            try:
                c = core.db()
                c.execute("CREATE TABLE IF NOT EXISTS feedback(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, client TEXT, query TEXT, think TEXT, tool TEXT, result TEXT, ok INTEGER, comment TEXT)")
                c.execute("INSERT INTO feedback(ts,client,query,think,tool,result,ok,comment) VALUES(?,?,?,?,?,?,?,?)",
                          (datetime.datetime.now().isoformat(), cl, (b.get("query") or "")[:2000], (b.get("think") or "")[:2000],
                           (b.get("tool") or "")[:120], (b.get("result") or "")[:2000], 1 if b.get("ok") else 0, (b.get("comment") or "")[:500]))
                c.commit(); c.close()
            except Exception as e:
                self._j({"ok": False, "msg": "оценка не сохранена: %s" % e}, 500); return
            self._j({"ok": True, "msg": "оценка сохранена"})
        elif p == "/setcfg":
            if (b.get("key") or "") in settings.PERSONAL_KEYS:
                settings.set_for(cl, b.get("key"), b.get("value")); self._j({"ok": True}); return
            if not users.is_admin(cl):
                self._j({"error": "настройки — только админ"}, 403); return
            settings.set_val(b.get("key"), b.get("value")); _SYS_CACHE.clear(); self._j({"ok": True})
        elif p == "/snap":
            self._j({"msg": "скриншот принимается через Ctrl+V в поле ввода"})
        elif p == "/rescan":
            subprocess.Popen([sys.executable, "-c", "import scanner; scanner.index_all()"], cwd=r"D:\AI\tools\agent")
            self._j({"msg": "переиндексация запущена"})
        elif p == "/scan":
            subprocess.Popen([sys.executable, "-c", "import scanner; scanner.scan_models()"], cwd=r"D:\AI\tools\agent")
            self._j({"msg": "скан моделей запущен"})
        elif p == "/profile":
            __prof = users.get_profile(cl)
            if __prof:
                __prof = dict(__prof)
                __prof["can_manage"] = users.can_manage_users(cl)
            self._j(__prof or {"error": "нет профиля"})
        elif p == "/setname":
            okf, msg = users.update_display_name(cl, b.get("name"))
            self._j({"ok": okf, "msg": msg})
        elif p == "/setpw":
            okf, msg = users.change_password(cl, b.get("old") or "", b.get("new") or "")
            self._j({"ok": okf, "msg": msg})
        elif p == "/chat/send":
            self._j(chat_tools.chat_send(cl, b.get("text")))
        elif p == "/chat/poll":
            self._j({"msgs": chat_tools.chat_poll(b.get("last") or 0)})
        elif p == "/admin/users":
            if not users.can_manage_users(cl):
                self._j({"error": "нет прав"}, 403); return
            op = b.get("op")
            if op == "list":
                self._j({"users": users.list_users(), "roles": users.ROLES})
            elif op == "role":
                okf, msg = users.admin_set_role(b.get("login") or "", b.get("role") or "")
                self._j({"ok": okf, "msg": msg})
            elif op == "add":
                okf = users.add_user(b.get("login") or "", b.get("pw") or b.get("password") or "", b.get("role") or "Инженер")
                self._j({"ok": okf, "msg": "создан" if okf else "логин занят или пустой"})
            elif op == "delete":
                lg = (b.get("login") or "").strip()
                if not lg:
                    self._j({"ok": False, "msg": "логин пустой"}, 400); return
                if lg == cl:
                    self._j({"ok": False, "msg": "нельзя удалить самого себя"}, 400); return
                us = users.list_users()
                tgt = [x for x in us if x.get("login") == lg]
                if not tgt:
                    self._j({"ok": False, "msg": "логин %s не найден" % lg}, 404); return
                adm = [x for x in us if x.get("role") == "Администратор" and x.get("login") != lg]
                if tgt[0].get("role") == "Администратор" and not adm:
                    self._j({"ok": False, "msg": "нельзя удалить последнего администратора"}, 400); return
                okf = users.admin_delete_user(lg)
                self._j({"ok": okf, "msg": ("пользователь %s удалён" % lg) if okf else "ошибка удаления"})
            elif op == "resetpw":
                okf, msg = users.admin_reset_password(b.get("login") or "", b.get("pw") or b.get("password") or "")
                self._j({"ok": okf, "msg": msg})
            else:
                self._j({"error": "неизвестная op"}, 400)
        else:
            self._j({"error": "не знаю"}, 404)


if __name__ == "__main__":
    import atexit
    log("=== старт АГЕНТ v15 на %s ===" % HOSTNAME)
    pidfile = core.BASE / "agent.pid"
    pidfile.write_text(str(os.getpid()), encoding="ascii")
    atexit.register(lambda: pidfile.unlink(missing_ok=True))
    threading.Thread(target=_scheduler, daemon=True).start()
    try:
        ThreadingHTTPServer((HOST, PORT), Hd).serve_forever()
    finally:
        try: pidfile.unlink(missing_ok=True)
        except Exception: pass