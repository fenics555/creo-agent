# -*- coding: utf-8 -*-
"""АГЕНТ v14 — agent.py (полная сборка)
ThreadingHTTPServer + стриминг токенов + параллельные инструменты + планировщик.
"""
import json, re, socket, threading, time, datetime
from concurrent.futures import ThreadPoolExecutor
import subprocess, sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import core
from core import log, trace
import settings
import pdf_tools


# === v14: стриминг токенов ===
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
        return "⛔ роль «%s» не может выполнить «%s» (запрет администратора)" % (role, tool)
    return None

HOST, PORT = "0.0.0.0", 8765
HOSTNAME = socket.gethostname()
PENDING = {}
LIVE = {}
LAST_META = {"p": 0, "r": 0}

DEFAULT_PROTO = """# ПРОТОКОЛ ИНЖЕНЕРА-НАПАРНИКА
1. РОЛЬ
Ты — старший инженер-конструктор КБ, напарник пользователя. Говоришь кратко, по делу, только проверенными фактами.
Скиллы в репо — справочники; при противоречии этот протокол главный.

2. ЯЗЫК
Думаешь и отвечаешь ТОЛЬКО на русском. Исключение — имена файлов, переменные, команды, код.

3. ФОРМАТ — ОДИН БЛОК НА ХОД
После ровно ОДИН блок, ничего до и после:
[TOOL: имя_инструмента] {"параметр": "значение"} [/TOOL]
или
[ANSWER] готовый ответ [/ANSWER]

4. ПРОТИВ ВЫДУМЫВАНИЯ
ЖИВЫЕ ДАННЫЕ (Creo, файлы, трейлы, база, 1С, настройки, история, пружины, стандарты, масса) — ТОЛЬКО через инструмент.
Справочные факты — через search_kb/read_file. Пока нет [РЕЗУЛЬТАТ] — не называй имён, шифров, чисел.
Доступ к базе, файлам и Creo у тебя ЕСТЬ — через инструменты из списка ниже. Никогда не говори «у меня нет доступа» — просто вызывай инструмент.

5. ПОРЯДОК
Определи, каких данных не хватает. 2. Вызови инструмент, жди [РЕЗУЛЬТАТ].
Мало — следующий; достаточно — [ANSWER] только из фактов [РЕЗУЛЬТАТ].
После [РЕЗУЛЬТАТ] НИКОГДА не отвечай «не понял/уточните» — данные уже в [РЕЗУЛЬТАТ],
кратко перескажи их в [ANSWER].

6. ПИШУЩИЕ ОПЕРАЦИИ
[СОГЛАСОВАНИЕ] меняет данные; вызывай только по прямой просьбе.

7. ПРИМЕРЫ
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
        (core_lines if t["name"] in _CORE else rest).append(t["name"] and line)
    tail = "=== ТВОИ ИНСТРУМЕНТЫ — ОСНОВНЫЕ (частые, полные) ===\n" + "\n".join(core_lines)
    tail += "\n\n=== ПРОЧИЕ ИНСТРУМЕНТЫ (только имена; описание блока — tools_help block=<имя>) ===\n"
    tail += ", ".join(sorted({t["name"] for t in TR.TOOLS if t["name"] not in _CORE}))
    tm = int(settings.get("think_mode") or 0)
    if tm == 0:
        think_rule = "=== РАЗМЫШЛЕНИЯ: запрещены. Не выводи [THINK]...[/THINK]. Сразу один блок: [TOOL] или [ANSWER]."
    elif tm == 1:
        think_rule = "=== РАЗМЫШЛЕНИЯ (кратко, максимум 4 строки):\n1) суть задачи;\n2) объект;\n3) какой инструмент;\n4) что НЕ подходит.\nБлок: [THINK]...[/THINK], затем один блок: [TOOL] или [ANSWER]."
    else:
        think_rule = "=== РАЗМЫШЛЕНИЯ (полно, на русском, 5-8 строк):\nнормализуй запрос;\nэтапы, если задача сложная;\nпочему именно этот инструмент;\nкакие альтернативы отверг и почему.\nБлок: [THINK]...[/THINK], затем один блок: [TOOL] или [ANSWER].\nПРИМЕР:\n[THINK]\nНормализация: проверить активную модель.\nЭтапы: один.\nИнструмент: creo_get_active — читает живую сессию.\nОтверг: models_find — это поиск по базе, не сессия.\n[/THINK]\n[TOOL: creo_get_active] {} [/TOOL]"
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
    m = re.search(r"\[TOOL:\s*([A-Za-z0-9_]+)\s*\]\s*(\{.*?\})\s*\[/TOOL\]", text, re.S)
    if m:
        try: args = json.loads(m.group(2))
        except Exception: args = {}
        if TR.get(m.group(1)): return "tool", m.group(1), args, think_text
    m = re.search(r"\[TOOL:\s*([A-Za-z0-9_]+)\s*\]", text)
    if m and TR.get(m.group(1)):
        rest = text[m.end():m.end() + 800]
        args = {}
        mj = re.search(r"\s*(\{.*?\})", rest, re.S)
        if mj:
            try: args = json.loads(mj.group(1))
            except Exception: args = {}
        return "tool", m.group(1), args, think_text
    m = re.search(r"\[TOOL\]\s*([A-Za-z0-9_]+)\s*(\{.*?\})?\s*(?:\[/TOOL\])?", text, re.S)
    if m and TR.get(m.group(1)):
        args = {}
        if m.group(2):
            try: args = json.loads(m.group(2))
            except Exception: args = {}
        return "tool", m.group(1), args, think_text
    for mm in re.finditer(r"^\s*([A-Za-z0-9_]+)\s*(\{[^\n]+\})\s*$", text, re.M):
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
_REFUSAL = ("извините", "не могу", "не имею доступа", "нет доступа", "моя функциональность", "виртуальной среде", "не поня", "уточните", "переформулир", "как языковая модель", "к сожалению, я", "буду отвечать", "какой у вас вопрос", "давайте начнём")

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
            for m in re.finditer(r"\[TOOL:\s*([A-Za-z0-9_]+)\s*\]\s*(\{.*?\})\s*\[/TOOL\]", raw, re.S):
                try: aa = json.loads(m.group(2))
                except Exception: aa = {}
                tt = TR.get(m.group(1))
                if tt and not tt.get("approval"): others.append((m.group(1), aa))
            others = [o for o in others if (o[0], json.dumps(o[1], sort_keys=True, ensure_ascii=False)) != (name, json.dumps(args, sort_keys=True, ensure_ascii=False))]
            if len(others) > 1:
                def _one(oa):
                    nn, aa2 = oa
                    if msg := _role_check(client, nn):
                        return "%s → %s" % (nn, msg)
                    try: return "%s → %s" % (nn, str(TR.get(nn)["fn"](**aa2))[:600])
                    except Exception as e: return "%s → ошибка: %s" % (nn, e)
                try:
                    with ThreadPoolExecutor(max_workers=4) as ex: res = "\n".join(ex.map(_one, others))
                    _log("parallel[%d]: %s" % (len(others), ", ".join(o[0] for o in others)))
                    last_res = res; sig_prev = sig
                    messages.append({"role": "assistant", "content": raw}); messages.append({"role": "user", "content": "[РЕЗУЛЬТАТ parallel]: %s" % res[:4000]})
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
    return {"answer": last_res or "не уложился в шаги", "think": think, "steps": step + 1, "log": steps_log}

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


PAGE = r"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>АГЕНТ v14</title>
<style>body{margin:0;background:#1B1C1E;color:#E8E8E8;font:14px/1.5 Segoe UI,sans-serif}
#top{position:fixed;top:0;left:0;right:0;background:linear-gradient(180deg,#2A2B2E,#232427);border-bottom:2px solid #1273EB;padding:8px 14px;display:flex;gap:10px;align-items:center;z-index:5}
#top b{color:#6db3f2}#chat{margin:52px 300px 70px 12px;padding:8px;overflow-y:auto}
#panel{position:fixed;top:44px;right:0;bottom:0;width:292px;background:#242527;overflow-y:auto;padding:8px;border-left:1px solid #3E4043}
.msg{max-width:760px;margin:10px 0;padding:10px 14px;border-radius:10px;background:#2C2D30;white-space:pre-wrap}
.msg.me{margin-left:auto;background:#0E5FC2}
.think{background:#242527;border:1px solid #3E4043;border-radius:8px;padding:6px 10px;margin-bottom:4px;color:#A6A8AB;cursor:pointer}
.thinkbody{background:#242527;border:1px solid #3E4043;border-radius:8px;padding:6px 10px;margin-bottom:8px;color:#A6A8AB;white-space:pre-wrap}
.log{color:#A6A8AB;font-size:12px;margin:6px 0;white-space:pre-wrap}
#inp{position:fixed;bottom:0;left:0;right:292px;background:#242527;padding:8px;display:flex;gap:8px;border-top:1px solid #3E4043}
#q{flex:1;background:#2C2D30;color:#E8E8E8;border:1px solid #3E4043;border-radius:8px;padding:10px}
button{background:#1273EB;color:#fff;border:0;border-radius:8px;padding:8px 14px;cursor:pointer}
button:hover{background:#0E5FC2}
.spin{display:inline-block;width:16px;height:16px;border:2px solid #6db3f2;border-top-color:transparent;border-radius:50%;animation:rot .8s linear infinite;vertical-align:middle;margin-left:8px}
@keyframes rot{to{transform:rotate(360deg)}}
.grp{border:1px solid #3E4043;border-radius:8px;margin:6px 0;padding:6px;background:#242527}
.grp h4{margin:2px 0 6px;color:#6db3f2;cursor:pointer;-webkit-user-select:none;user-select:none;font-size:13px;display:flex;align-items:center;gap:6px}
.grp h4 .ar{font-size:10px;transition:transform .15s}
.grp h4 .ar.o{transform:rotate(90deg)}
.grp h4 .cnt{background:#1273EB;color:#fff;border-radius:10px;padding:1px 7px;font-size:11px}
.tool{display:flex;align-items:center;gap:8px;background:#2C2D30;border-radius:6px;padding:6px;margin:4px 0;cursor:pointer;border-left:2px solid transparent}
.tool:hover{background:#333;border-left:2px solid #1273EB}
.tool .ic{width:28px;height:28px;flex-shrink:0;font-size:20px;display:flex;align-items:center;justify-content:center}
.tool b{font-size:13px;color:#E8E8E8;flex:1;font-weight:normal}
.tool b small{display:block;color:#A6A8AB;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tool .lk{color:#C64E4E;font-size:14px}
#psrc{width:100%;box-sizing:border-box;background:#2C2D30;color:#E8E8E8;border:1px solid #3E4043;border-radius:8px;padding:6px;margin-bottom:6px}
#pcnt{font-size:11px;color:#A6A8AB;margin:4px 0}
.pin{display:inline-flex;align-items:center;gap:4px;background:#2C2D30;border:1px solid #3E4043;border-radius:6px;padding:3px 8px;margin:2px;cursor:pointer;font-size:12px}
.pin:hover{border-color:#1273EB}
#login{position:fixed;inset:0;background:#0009;display:none;align-items:center;justify-content:center;z-index:9}
#login div{background:#242527;padding:24px;border-radius:12px;display:flex;flex-direction:column;gap:10px;border:1px solid #3E4043}
#login input{background:#2C2D30;color:#E8E8E8;border:1px solid #3E4043;border-radius:8px;padding:10px}
<body>
<div id="top"><b>АГЕНТ v14</b><span id="hdr"></span><span style="flex:1"></span>
<button data-act="chip" data-val="guide">❓</button><button data-act="wizard">🧙</button><button data-act="showlog">Лог</button><button data-act="panel">Панель</button><button data-act="showpro">👤</button><button data-act="showchat">💬</button><button data-act="logout">Выйти</button></div>
<div id="chat"></div><div id="panel"></div>
<div id="inp"><input id="q" placeholder="Задача для АГЕНТА... (Enter) | Ctrl+V — вставить скриншот"><button data-act="snap">📷</button><button data-act="send">Спросить</button><span id="spin" class="spin" style="display:none"></span></div>
<div id="login"><div style="position:relative"><button data-act="closelogin" style="position:absolute;top:6px;right:6px;background:#3E4043;color:#fff;border:0;border-radius:6px;padding:2px 8px;cursor:pointer">✕</button>
<input id="lg" placeholder="логин"><input id="pw" type="password" placeholder="пароль"><button data-act="login">Войти</button><button data-act="reg">Регистрация</button></div></div>
<div id="wiz" style="display:none;position:fixed;inset:0;background:#0009;align-items:center;justify-content:center;z-index:11">
<div style="background:#242527;padding:20px;border-radius:12px;width:430px;display:flex;flex-direction:column;gap:9px;border:1px solid #3E4043">
<b>🧙 МАСТЕР ОПЕРАЦИЙ</b>
<small style="color:#A6A8AB">Копия сборки (сначала план)</small>
<input id="w_old" placeholder="старое имя (old)" style="background:#2C2D30;color:#E8E8E8;border:1px solid #3E4043;border-radius:8px;padding:10px">
<input id="w_new" placeholder="новое имя (new)" style="background:#2C2D30;color:#E8E8E8;border:1px solid #3E4043;border-radius:8px;padding:10px">
<small style="color:#A6A8AB">Куда копировать</small>
<input id="w_dir" value="Z:\PTC\Work\" style="background:#2C2D30;color:#E8E8E8;border:1px solid #3E4043;border-radius:8px;padding:10px">
<label style="display:flex;align-items:center;gap:6px;color:#A6A8AB;font-size:12px"><input type="checkbox" id="w_dry"> только план (dry_run)</label>
<button data-act="wizgo">📋 Сделать копию</button><button data-act="wizclose" style="background:#3E4043">Закрыть</button><div id="wizout" style="font-size:12px;color:#A6A8AB;white-space:pre-wrap"></div></div></div>
<div id="chatbox" style="display:none;position:fixed;top:44px;left:0;right:292px;bottom:60px;background:#1B1C1E;flex-direction:column;border-right:1px solid #3E4043">
<div style="display:flex;align-items:center;gap:8px;padding:8px;border-bottom:1px solid #3E4043"><b style="color:#6db3f2;flex:1">💬 ЧАТ</b><button data-act="chatclose" style="background:#3E4043;padding:4px 10px">✕</button></div>
<div id="cmsgs" style="flex:1;overflow-y:auto;padding:8px"></div>
<div style="padding:8px;display:flex;gap:8px;border-top:1px solid #3E4043"><input id="cin" placeholder="сообщение..." style="flex:1;background:#2C2D30;color:#E8E8E8;border:1px solid #3E4043;border-radius:8px;padding:8px"><button data-act="chatsend" style="padding:6px 12px">➤</button></div></div>
<div id="logbox" style="display:none;position:fixed;top:44px;left:0;right:292px;bottom:60px;background:#1B1C1E;flex-direction:column;border-right:1px solid #3E4043">
<div style="display:flex;align-items:center;gap:8px;padding:8px;border-bottom:1px solid #3E4043"><b style="color:#6db3f2;flex:1">ЛОГ</b><button data-act="logclose" style="background:#3E4043;padding:4px 10px">✕</button></div>
<div id="lbox" style="flex:1;overflow-y:auto;padding:8px"></div></div>
<div id="probox" style="display:none;position:fixed;top:44px;left:0;right:292px;bottom:60px;background:#1B1C1E;flex-direction:column;border-right:1px solid #3E4043">
<div style="display:flex;align-items:center;gap:8px;padding:8px;border-bottom:1px solid #3E4043"><b style="color:#6db3f2;flex:1">ПРОФИЛЬ</b><button data-act="proclose" style="background:#3E4043;padding:4px 10px">✕</button></div>
<div id="pbox" style="flex:1;overflow-y:auto;padding:8px"></div></div>
<script>
.sgrp{border:1px solid #3E4043;border-radius:8px;margin:8px 0;padding:8px}
.sgrp h5{margin:0 0 8px;color:#6db3f2;font-size:13px;cursor:pointer}
.row{display:flex;align-items:center;justify-content:space-between;margin:6px 0;gap:8px}
.row label{font-size:12px;color:#A6A8AB;flex:1}
.row select{background:#2C2D30;color:#E8E8E8;border:1px solid #3E4043;border-radius:6px;padding:4px;font-size:12px;min-width:140px}
.row input[type=text]{background:#2C2D30;color:#E8E8E8;border:1px solid #3E4043;border-radius:6px;padding:4px 6px;font-size:12px;min-width:140px}
.row input[type=range]{flex:1;accent-color:#1273EB}
.row input[type=checkbox]{accent-color:#1273EB}
.flash{animation:flash 1s}
@keyframes flash{0%{background:#1273EB}100%{background:#2C2D30}}
.op-ok{color:#86BC43}.op-err{color:#C64E4E}.op-info{color:#4C8FD6}.op-warn{color:#E8912D}</style></head>function esc(s){return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function J(u,d){return fetch(u,{method:d?'POST':'GET',headers:d?{'Content-Type':'application/json','X-Token':window.TK||''}:{},body:d?JSON.stringify(d):undefined}).then(function(r){return r.json()})}
var TK=null,Q=null,qinp=null,hdr=null,CURM='';
var PINS=['creo_get_active','models_find','search_kb','trail_problems','calc','creo_session'];
function panelPin(key){J('/ask',{token:TK,task:key}).then(function(r){addMsg('>> '+key+': '+JSON.stringify(r).slice(0,120),true)})}
function buildPanel(p){
  p=p||{actions:[],models:[],chips:[],groups:[]};
  window.MODELS=p.models||[];
  var h='<input id="psrc" placeholder="поиск по имени и описанию..."><div id="pcnt"></div><div>';
  PINS.forEach(function(k){
    var t=(p.groups||[]).reduce(function(a,g){return a.concat(g.tools||[])},[]).filter(function(t){return t.name===k})[0];
    h+='<span class="pin" data-pin="'+k+'">📌 '+(t?esc(t.name):k)+'</span>';
  });
  h+='</div>';
  var fold=JSON.parse(localStorage.getItem('panel_fold')||'{}');
  (p.groups||[]).forEach(function(g,gi){
    var gn=esc(g.title||'пространство');
    var cnt=(g.tools||[]).length;
    var ic=g.icon||'📁';
    var open=fold[gi]?true:false;
    h+='<div class="grp"><h4 data-gi="'+gi+'"><span class="ar'+(open?' o':'')+'">▸</span>'+ic+' '+gn+' <span class="cnt">'+cnt+'</span></h4>';
    if(open){
      (g.tools||[]).forEach(function(t){
        var lk=t.approval?' <span class="lk">🔒</span>':'';
        h+='<div class="tool" data-name="'+esc(t.name)+'"><span class="ic">'+(t.icon||'🔧')+'</span><b>'+esc(t.name)+'<small>'+esc(t.desc||'')+'</small></b>'+lk+'</div>';
      });
    }
    h+='</div>';
  });
  var box=document.getElementById('panel');box.innerHTML=h;
  box.querySelectorAll('h4[data-gi]').forEach(function(e){e.onclick=function(){var gi=e.getAttribute('data-gi');fold[gi]=!fold[gi];localStorage.setItem('panel_fold',JSON.stringify(fold));renderPanel()}});
  box.querySelectorAll('.tool').forEach(function(e){e.onclick=function(){var n=e.getAttribute('data-name');if(qinp){qinp.value=n;send()}}});
  box.querySelectorAll('.pin').forEach(function(e){e.onclick=function(){panelPin(e.getAttribute('data-pin'))}});
  var src=document.getElementById('psrc');
  function doFilter(){
    var q=(src.value||'').toLowerCase();
    var total=0,shown=0;
    box.querySelectorAll('.grp').forEach(function(g){
      var gtools=g.querySelectorAll('.tool');
      var gvis=0;
      gtools.forEach(function(t){
        total++;
        var name=t.querySelector('b');var desc=name?name.textContent:'';
        if(!q||desc.toLowerCase().indexOf(q)>=0){t.style.display='flex';shown++;gvis++}else{t.style.display='none'}
      });
      g.style.display=gvis>0?'block':'none';
    });
    var c=document.getElementById('pcnt');if(c)c.textContent='найдено: '+shown+' / '+total;
  }
  if(src)src.addEventListener('input',doFilter);
}
function buildSettings(s){
  var items=s.items||[];
  var groups={};
  items.forEach(function(it){(groups[it.space]=groups[it.space]||[]).push(it)});
  var h='';
  var modelKeys=['llm_model','model_fast','model_trail','model_vision','model_index'];
  Object.keys(groups).forEach(function(sp){
    var gitems=groups[sp];
document.addEventListener('click',function(e){var el=e.target.closest('[data-act]');if(!el)return;var a=el.getAttribute('data-act');
if(a=='think'){var n=el.nextElementSibling;n.style.display=n.style.display=='none'?'block':'none'}
else if(a=='fold'){var b=el.nextElementSibling;var hid=b.style.display=='none';b.style.display=hid?'block':'none';el.textContent=(hid?'▾':'▸')+el.textContent.slice(1)}
else if(a=='send')send();
else if(a=='wizard'){document.getElementById('wiz').style.display='flex'}
else if(a=='wizclose'){document.getElementById('wiz').style.display='none'}
else if(a=='wizgo'){var o=document.getElementById('w_old').value,n=document.getElementById('w_new').value;if(!o||!n){alert('заполни old и new');return}document.getElementById('wiz').style.display='none';qinp.value='copy_model old='+o+' new='+n+' dry_run='+(document.getElementById('w_dry').checked?1:0);send()}
else if(a=='snap')J('/snap',{token:TK}).then(function(r){addMsg(esc(r.msg||'ок'))});
else if(a=='showlog')J('/log').then(function(r){addMsg('<div class="log">'+esc(r.log)+'</div>')});
else if(a=='panel')panel.style.display=panel.style.display=='none'?'block':'none';
else if(a=='logout'){localStorage.removeItem('tk');localStorage.removeItem('usr');TK='';showLogin()}
else if(a=='showpro'){J('/profile',{token:TK}).then(function(u){document.getElementById('proinfo').textContent=(u.display_name||'')+' · '+(u.role||'')+' · '+u.login;document.getElementById('pname').value=u.display_name||'';document.getElementById('probox').style.display='flex'})}
else if(a=='proclose'){document.getElementById('probox').style.display='none'}
else if(a=='savename'){var v=document.getElementById('pname').value;J('/setname',{token:TK,name:v}).then(function(r){alert(r.msg||'ок');if(r.ok){document.getElementById('probox').style.display='none';init()}})}
else if(a=='savepw'){J('/setpw',{token:TK,old:document.getElementById('pold').value,'new':document.getElementById('pnew').value}).then(function(r){alert(r.msg||'ок');if(r.ok){document.getElementById('pold').value='';document.getElementById('pnew').value=''}})}
else if(a=='showchat'){document.getElementById('chatbox').style.display='flex';NEWMSG=0;chatBadge();chatPoll()}
else if(a=='chatclose'){document.getElementById('chatbox').style.display='none'}
else if(a=='chatsend'){var v=document.getElementById('cin').value;if(!v)return;J('/chat/send',{token:TK,text:v}).then(function(){document.getElementById('cin').value='';chatPoll()})}
else if(a=='login'){J('/login',{login:document.getElementById('lg').value,pw:document.getElementById('pw').value}).then(function(r){if(r.token){TK=r.token;localStorage.setItem('tk',r.token);document.getElementById('login').style.display='none';init()}else{alert(r.msg||'ошибка')}})}
else if(a=='reg'){J('/register',{login:document.getElementById('lg').value,pw:document.getElementById('pw').value}).then(function(r){alert(r.msg||'ок')})}
else if(a=='chip'){var v=el.getAttribute('data-val')||'';if(qinp){qinp.value=v;send()}}
else if(a=='closelogin'){document.getElementById('login').style.display='none'}})
function addMsg(txt,me){var d=document.createElement('div');d.className='msg'+(me?' me':'');d.innerHTML=txt;document.getElementById('chat').appendChild(d);document.getElementById('chat').scrollTop=document.getElementById('chat').scrollHeight}
function send(){var v=qinp.value;if(!v)return;addMsg(esc(v),true);qinp.value='';J('/ask',{token:TK,task:v}).then(function(r){if(r.error){addMsg('<b style="color:#C64E4E">ошибка:</b> '+esc(r.error),false)}else{addMsg(esc(r.answer||r.msg||''),false)}}).catch(function(e){addMsg('<b style="color:#C64E4E">сбой:</b> '+esc(e),false)})}
function showLogin(){document.getElementById('login').style.display='flex'}
function chatPoll(){J('/chat/poll',{token:TK,last:CLAST}).then(function(r){chatRender(r.msgs||[])})}
function chatRender(msgs){var box=document.getElementById('cmsgs');msgs.forEach(function(m){if(m.id<=CLAST)return;CLAST=m.id;var d=document.createElement('div');d.style.cssText='background:#2C2D30;border-radius:6px;padding:6px 8px';d.innerHTML='<b style="color:#7cc0f4">'+esc(m.name)+'</b> <small style="color:#A6A8AB">'+esc(m.ts)+'</small><br>'+esc(m.text);box.appendChild(d)});box.scrollTop=box.scrollHeight}
var NEWMSG=0;
function chatBadge(){var b=document.querySelector('[data-act="showchat"]');if(b)b.textContent=NEWMSG>0?'💬'+NEWMSG:'💬'}
    h+='<div class="sgrp"><h5 data-act="fold">▸ '+esc(sp)+'</h5><div class="gbody">';
    gitems.forEach(function(it){
      (window.CFG=window.CFG||{})[it.key]=it.value;
      if(sp=='ИИ-роли'&&modelKeys.indexOf(it.key)>=0){
        h+='<div class="row"><label>'+esc(it.name)+'</label><select data-cfg="'+esc(it.key)+'">';
        h+='<option value="">— как чат —</option>';
        (window.MODELS||[]).forEach(function(m){h+='<option value="'+esc(m)+'"'+(m==it.value?' selected="selected"':"")+'>'+esc(m)+'</option>'});
        h+='</select></div>';
      }else if(it.kind=='range'){
        h+='<div class="row"><label>'+esc(it.name)+'</label><input type="range" data-cfg="'+esc(it.key)+'" min="'+it.min+'" max="'+it.max+'" step="'+it.step+'" value="'+it.value+'"><b data-v="'+esc(it.key)+'">'+it.value+'</b></div>';
      }else if(it.kind=='check'){
        h+='<div class="row"><label>'+esc(it.name)+'</label><input type="checkbox" data-cfg="'+esc(it.key)+'" '+(it.value?'checked="checked"':"")+'></div>';
      }else{
        h+='<div class="row"><label>'+esc(it.name)+'</label><input type="text" data-cfg="'+esc(it.key)+'" value="'+esc(String(it.value))+'"></div>';
      }
    });
    h+='</div></div>';
  });
  panel.innerHTML+=h;
}
var PANEL_DATA=null;
function renderPanel(){if(PANEL_DATA)buildPanel(PANEL_DATA)}
function renderSettings(){J('/settings').then(buildSettings)}
function init(){J('/status').then(function(s){CURM=s.model;hdr.textContent=s.host+(s.user?' | '+(s.user.display_name||s.user.login):'')+' | '+s.model+' | блоков: '+s.blocks;J('/panel').then(function(p){PANEL_DATA=p;buildPanel(p);J('/settings').then(buildSettings)})})}(function(){var sp=document.getElementById('spin');if(!sp)return;var of=window.fetch;window.fetch=function(u){var url=String(u);var bg=url.indexOf('/chat/poll')>=0||url.indexOf('/status')>=0||url.indexOf('/ask')>=0;if(!bg)sp.style.display='inline-block';var p=of.apply(this,arguments);var t=new Promise(function(r,j){setTimeout(function(){j(new Error('таймаут 900с: '+url))},900000)});return Promise.race([p,t]).finally(function(){if(!bg)sp.style.display='none';});};})();
(function(){if(window.__slfix)return;window.__slfix=1;
var busy=false;
function sync(r){var lab=r.parentNode.querySelector('[data-v]')||r.nextElementSibling;if(lab&&String(lab.textContent)!==String(r.value))lab.textContent=r.value;}
document.addEventListener('input',function(e){var r=e.target;if(r&&r.type=='range'&&r.getAttribute('data-cfg'))sync(r);});
function cfgSuccess(el){if(!el)return;el.classList.add('flash');setTimeout(function(){el.classList.remove('flash')},1000)}
document.addEventListener('change',function(e){var r=e.target;var k=r.getAttribute&&r.getAttribute('data-cfg');if(!k)return;if(r.type=='range'||r.type=='checkbox'){var v=(r.type=='checkbox')?(r.checked?1:0):r.value;fetch('/setcfg',{method:'POST',headers:{'Content-Type':'application/json','X-Token':window.TK||''},body:JSON.stringify({key:k,value:v})}).then(function(){cfgSuccess(r)});}});
document.addEventListener('change',function(e){var r=e.target;if(r.tagName=='SELECT'&&r.getAttribute('data-cfg')){var k=r.getAttribute('data-cfg');fetch('/setcfg',{method:'POST',headers:{'Content-Type':'application/json','X-Token':window.TK||''},body:JSON.stringify({key:k,value:r.value})}).then(function(){cfgSuccess(r)});}});
document.addEventListener('focusout',function(e){var r=e.target;if(r.tagName=='INPUT'&&r.type=='text'&&r.getAttribute('data-cfg')){var k=r.getAttribute('data-cfg');fetch('/setcfg',{method:'POST',headers:{'Content-Type':'application/json','X-Token':window.TK||''},body:JSON.stringify({key:k,value:r.value})}).then(function(){cfgSuccess(r)});}});
var mo=new MutationObserver(function(){if(busy)return;busy=true;try{document.querySelectorAll('input[type=range][data-cfg]').forEach(function(r){var want=parseFloat(r.getAttribute('data-val')||r.value);if(!isNaN(want)){if(parseFloat(r.max)<want)r.max=want;if(String(r.value)!==String(want))r.value=want;sync(r);}});}finally{busy=false;}});
mo.observe(document.body,{childList:true,subtree:true});
window.addEventListener('unhandledrejection',function(){var sp=document.getElementById('spin');if(sp)sp.style.display='none';});})();
/*lm-deco*/(function(){var N=['авто','авто+токены','отладка','полный'];function dec(){var b=document.querySelector('[data-v="log_mode"]');if(!b)return;var v=parseInt(b.textContent,10);var w=v+' · '+(N[v]||'');if(b.textContent!=w)b.textContent=w;}document.addEventListener('input',function(e){var t=e.target;if(t&&t.getAttribute&&t.getAttribute('data-cfg')=='log_mode')setTimeout(dec,0);});setInterval(dec,1000);dec();})();
qinp=document.getElementById('q');
document.addEventListener('paste',function(e){var it=null,items=e.clipboardData.items;for(var i=0;i<items.length;i++){if(items[i].type.indexOf('image')==0){it=items[i];break}}if(!it)return;var f=it.getAsFile();var rd=new FileReader();rd.onload=function(){addMsg('скриншот прикреплён',true)};rd.readAsDataURL(f)});
var lg=document.getElementById('lg'),pw=document.getElementById('pw');
lg.addEventListener('keydown',function(e){if(e.key=='Enter')document.querySelector('[data-act="login"]').click()});
pw.addEventListener('keydown',function(e){if(e.key=='Enter')document.querySelector('[data-act="login"]').click()});
document.getElementById('cin').addEventListener('keydown',function(e){if(e.key=='Enter')document.querySelector('[data-act="chatsend"]').click()});
var ttk=localStorage.getItem('tk');if(ttk){TK=ttk;Promise.resolve().then(init).catch(function(e){addMsg('ошибка инициализации: '+e,true)})}else showLogin();
</script></body></html>"""
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
            if s.lstrip().startswith("{\\"):
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
            _trails = ""
            try:
                _jf = core.REPO / "Трейлы" / "TRAIL_JOURNAL.md"
                if _jf.exists():
                    _trails = "\n".join(_jf.read_text(encoding="utf-8", errors="ignore").splitlines()[-10:])
            except Exception:
                pass
            self._j({"host": HOSTNAME, "model": settings.get("llm_model"), "blocks": len(TR.BLOCKS), "tools": len(TR.TOOLS), "user": prof, "is_manager": users.can_manage_users(prof["login"]) if prof else False, "trails": _trails})
            return
        elif p == "/pdfpages":
            token = self.headers.get("X-Token") or ""
            if not users.token_info(token): return self._j({"error": "no token"})
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get("name", [""])[0]
            if not name: return self._j({"error": "no name"})
            self._j(pdf_tools.pdf_pages(name))
            return
        elif p == "/pdfimg":
            token = self.headers.get("X-Token") or ""
            if not users.token_info(token): return self._j({"error": "no token"})
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get("name", [""])[0]
            page = qs.get("page", ["1"])[0]
            if not name: return self._j({"error": "no name"})
            self._j(pdf_tools.pdf_img(name, page))
            return
        elif p == "/pdfstatus":
            token = self.headers.get("X-Token") or ""
            if not users.token_info(token): return self._j({"error": "no token"})
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get("name", [""])[0]
            if not name: return self._j({"error": "no name"})
            self._j(pdf_tools.pdf_status(name))
            return
        elif p == "/children":
            token = self.headers.get("X-Token") or ""
            if not users.token_info(token): return self._j({"error": "no token"})
            qs = parse_qs(urlparse(self.path).query)
            name = qs.get("name", [""])[0]
            if not name: return self._j({"error": "no name"})
            import plm_tools
            try:
                c = plm_tools._db()
                rows = c.execute("SELECT child FROM bom WHERE parent LIKE ?", ("%"+name.lower()+"%",)).fetchall()
                c.close()
                children = [r[0] for r in rows]
            except Exception as e:
                children = []
            self._j({"name": name, "children": children})
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
            import os as _os
            tail = ""
            try:
                jf = core.REPO / "Трейлы" / "TRAIL_JOURNAL.md"
                if jf.exists():
                    tail = "\n".join(jf.read_text(encoding="utf-8", errors="ignore").splitlines()[-10:])
            except Exception: pass
            self._j({"tail": tail})
            return
        else:
            b = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(b)))
            self.end_headers()
            self.wfile.write(b)
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
    import os, atexit
    log("=== старт АГЕНТ v14 на %s ===" % HOSTNAME)
    pidfile = core.BASE / "agent.pid"
    pidfile.write_text(str(os.getpid()), encoding="ascii")
    atexit.register(lambda: pidfile.unlink(missing_ok=True))
    threading.Thread(target=_scheduler, daemon=True).start()
    try:
        ThreadingHTTPServer((HOST, PORT), Hd).serve_forever()
    finally:
        try: pidfile.unlink(missing_ok=True)
        except Exception: pass
