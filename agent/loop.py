import json, re, os, socket, threading, time, datetime
from concurrent.futures import ThreadPoolExecutor
import subprocess, sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import core
from core import log, trace
import settings
import pdf_tools
import urllib.request as _ur
import tools_registry as TR
import scanner
import users
import chat_tools
import panel
import vision_tools as VI

def _clean(txt):
    if not txt:
        return ""
    txt = re.sub(r"\[THINK\].*?\[/THINK\]", "", txt, flags=re.DOTALL)
    txt = re.sub(r"\[/?ANSWER\]", "", txt)
    tool_contents = []
    def tool_replacer(m):
        content = m.group(1)
        idx = len(tool_contents)
        tool_contents.append(content)
        return f"\x00{idx}\x00"
    txt = re.sub(r"\[TOOL[^\]]*\](.*?)\[/TOOL\]", tool_replacer, txt, flags=re.DOTALL)
    txt = re.sub(r"\[TOOL[^\]]*\]|\[/TOOL\]", "", txt)
    cyrillic_match = re.search(r'[а-яА-Я]', txt)
    if cyrillic_match:
        first_cyrillic_idx = cyrillic_match.start()
        reasoning_part = txt[:first_cyrillic_idx]
        answer_part = txt[first_cyrillic_idx:]
        new_answer_part = answer_part
        for i, content in enumerate(tool_contents):
            marker = f"\x00{i}\x00"
            if marker in reasoning_part:
                new_answer_part = content + new_answer_part
        txt = new_answer_part
    for i, content in enumerate(tool_contents):
        marker = f"\x00{i}\x00"
        txt = txt.replace(marker, content)
    return txt.strip()

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
    except Exception:
        p2 = dict(payload); p2["stream"] = False
        return _orig_core_post(path, p2, *ar, **kw)
    r = {"message": {"content": "".join(parts), "thinking": "".join(thparts)}}
    for _kk in ("prompt_eval_count", "eval_count", "prompt_eval_duration", "eval_duration"):
        if _kk in lastj: r[_kk] = lastj[_kk]
    return r

_post_before_think = _stream_post

def _post_think_off(path, payload, *ar, **kw):
    if path == "/api/chat" and isinstance(payload, dict):
        payload = dict(payload)
        if int(settings.get("think_mode") or 0) == 0:
            payload["think"] = False
    return _post_before_think(path, payload, *ar, **kw)

DEFAULT_PROTO = """# ПРОТОКОЛ ИНЖЕНЕРА-НАПАРНИКА
РОЛЬ: ты — старший инженер-конструктор КБ, напарник пользователя; говори кратко, по делу, только проверенными фактами.
ЯЗЫК: только русский; код, термины и имена файлов — как в оригинале.
ФОРМАТ: один блок на ход — [TOOL: имя] {...} [/TOOL] или [ANSWER] текст [/ANSWER], ничего до и после.
ЖИВЫЕ ДАННЫЕ: статусы и значения только из свежих цитат с машины через инструменты.
ДОСТУП: токены, пароли и секреты наружу не выводи.
ПРИМЕРЫ: «привет» → [ANSWER] Привет! С чем помочь? [/ANSWER]
"""

def load_skill(name):
    p = core.REPO / name
    try: return p.read_text(encoding="utf-8") if p.exists() else ""
    except Exception: return ""


_NUDGE = "[СЛУЖЕБНОЕ] Ответ не в формате. Дай ровно один блок: [TOOL: имя] {\"параметр\": \"значение\"} [/TOOL] или [ANSWER] краткий ответ по-русски [/ANSWER]. Слово «текст» само по себе — не ответ. Ничего до и после блока."
_ACCESS_NUDGE = "[СЛУЖЕБНОЕ] Неверно. Доступ к базе, файлам и Creo у тебя ЕСТЬ через инструменты (список «ТВОИ ИНСТРУМЕНТЫ» выше). Никогда не отвечай «нет доступа». Повтори ровно один блок: [TOOL: имя] {\"параметр\": \"значение\"} [/TOOL] или [ANSWER] ответ [/ANSWER]."
_REFUSAL = ("извините", "не могу", "не имею доступа", "нет доступа", "моя функциональность",
            "виртуальной среде", "не понял", "уточните", "переформулируй", "как языковая модель",
            "к сожалению, я", "буду отвечать", "какой у вас вопрос", "давайте начнём")

def _refusal(text):
    lo = (text or "").lower()
    return any(w in lo for w in _REFUSAL)

def _two(res):
    return " ".join(str(res).split()[:2]) or "пусто"

def hist_block(client):
    c = core.db()
    rows = c.execute("SELECT q,a FROM history WHERE client=? ORDER BY id DESC LIMIT 8", (client,)).fetchall()
    c.close()
    out = []
    for q, a in reversed(rows):
        out.append({"role": "user", "content": q[:500]})
        out.append({"role": "assistant", "content": a[:800]})
    return out

def run_loop(messages, client, has_link=False, on_step=None, opts_and_steps=None):
    if opts_and_steps:
        opts, steps_max = opts_and_steps
    else:
        opts, steps_max = beh()
    LAST_META.update(p=0, r=0)

_CORE = (
    "creo_get_active", "creo_status", "creo_session", "creo_list_files",
    "models_find", "models_where", "models_stats", "usage_state",
    "search_kb", "read_file", "trail_predict", "trail_problems",
    "settings_show", "help", "tools_help",
)
_SYS_CACHE = {}

def build_system(mode=1):
    if mode == 2:
        return """Ты — собеседник и помощник по любым темам. Язык ответа — русский; код, термины и формулы — как принято в теме.
В этом режиме нет доступа к Creo, файлам и базам: если вопрос требует живых данных, скажи «в режиме инженера я достану это из Creo или базы — переключи режим» и не выдумывай.
Формат: свободный текст; код внутри блоков с языком; служебных тегов нет."""
    _SYS_CACHE.clear()
    p = ((load_skill("MANIFEST.md") or "") + "\n\n" + (load_skill("SKILL_agent_protocol.md") or DEFAULT_PROTO)).strip() + "\n"
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
        think_rule = "=== РАЗМЫШЛЕНИЯ (кратко, максимум 4 строки): 1) суть за 2) шаги 3) результат"
    else:
        think_rule = "=== РАЗМЫШЛЕНИЯ (развернуто) ==="
    return p + "\n\n" + tail + "\n\n" + think_rule

def _role_check(client, tool):
    if not client or not tool: return None
    prof = users.get_profile(client)
    if not prof: return None
    role = prof.get("role", "Инженер")
    if users.role_denied(role, tool):
        return "🛔 роль «%s» не может выполнить «%s» (запрет администратора)" % (role, tool)
    return None

PENDING = {}
LIVE = {}
LAST_META = {"p": 0, "r": 0}

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
        m = re.search(pat, text, flags=flags)
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
    for mm in re.finditer(r"^\s*([A-Za-z0-9_]+)\s*({[^\\n]+})\s*$", text, re.M):
        if TR.get(mm.group(1)):
            try: args = json.loads(mm.group(2))
            except Exception: args = {}
            return "tool", mm.group(1), args, think_text
    m = re.search(r"\[ANSWER\]\s*(.*?)\\[/ANSWER\\]", text, re.S)
    if m: return "answer", m.group(1).strip(), None, think_text
    if "[ANSWER]" in text and "[/ANSWER]" not in text:
        return "answer", text.split("[ANSWER]", 1)[1].strip(), None, think_text
    ts = text.strip()
    if TR.get(ts): return "tool", ts, {}, think_text
    return "invalid", text.strip(), None, think_text

    steps_log, last_res, sig_prev, invalid_cnt = [], "", None, 0

    def _log(line): steps_log.append(line); LIVE.setdefault(client, []).append(line)

    for step in range(steps_max):
        r = None
        # ... (Wait, I need the full run_loop body from agent.py)


DEFAULT_PROTO = """# ПРОТОКОЛ ИНЖЕНЕРА-НАПАРНИКА
РОЛЬ: ты — старший инженер-конструктор КБ, напарник пользователя; говори кратко, по делу, только проверенными фактами.
ЯЗЫК: только русский; код, термины и имена файлов — как в оригинале.
ФОРМАТ: один блок на ход — [TOOL: имя] {...} [/TOOL] или [ANSWER] текст [/ANSWER], ничего до и после.
ЖИВЫЕ ДАННЫЕ: статусы и значения только из свежих цитат с машины через инструменты.
ДОСТУП: токены, пароли и секреты наружу не выводи.
ПРИМЕРЫ: «привет» → [ANSWER] Привет! С чем помочь? [/ANSWER]
"""

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

def build_system(mode=1):
    if mode == 2:
        return """Ты — собеседник и помощник по любым темам. Язык ответа — русский; код, термины и формулы — как принято в теме.
В этом режиме нет доступа к Creo, файлам и базам: если вопрос требует живых данных, скажи «в режиме инженера я достану это из Creo или базы — переключи режим» и не выдумывай.
Формат: свободный текст; код внутри блоков с языком; служебных тегов нет."""
    _SYS_CACHE.clear()
    p = ((load_skill("MANIFEST.md") or "") + "\n\n" + (load_skill("SKILL_agent_protocol.md") or DEFAULT_PROTO)).strip() + "\n"
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
        think_rule = "=== РАЗМЫШЛЕНИЯ (кратко, максимум 4 строки): 1) суть за 2) шаги 3) результат"
    else:
        think_rule = "=== РАЗМЫШЛЕНИЯ (развернуто) ==="
    return p + "\n\n" + tail + "\n\n" + think_rule

def _role_check(client, tool):
    if not client or not tool: return None
    prof = users.get_profile(client)
    if not prof: return None
    role = prof.get("role", "Инженер")
    if users.role_denied(role, tool):
        return "🛔 роль «%s» не может выполнить «%s» (запрет администратора)" % (role, tool)
    return None

PENDING = {}
LIVE = {}
LAST_META = {"p": 0, "r": 0}

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
        m = re.search(pat, text, flags=flags)
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
    for mm in re.finditer(r"^\s*([A-Za-z0-9_]+)\s*({[^\\n]+})\s*$", text, re.M):
        if TR.get(mm.group(1)):
            try: args = json.loads(mm.group(2))
            except Exception: args = {}
            return "tool", mm.group(1), args, think_text
    m = re.search(r"\[ANSWER\]\s*(.*?)\\[/ANSWER\\]", text, re.S)
    if m: return "answer", m.group(1).strip(), None, think_text
    if "[ANSWER]" in text and "[/ANSWER]" not in text:
        return "answer", text.split("[ANSWER]", 1)[1].strip(), None, think_text
    ts = text.strip()
    if TR.get(ts): return "tool", ts, {}, think_text
    return "invalid", text.strip(), None, think_text

import json, re, os, socket, threading, time, datetime
from concurrent.futures import ThreadPoolExecutor
import subprocess, sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import core
from core import log, trace
import settings
import pdf_tools
import urllib.request as _ur
import tools_registry as TR
import scanner
import users
import chat_tools
import panel
import vision_tools as VI

def _clean(txt):
    if not txt:
        return ""
    txt = re.sub(r"\[THINK\].*?\[/THINK\]", "", txt, flags=re.DOTALL)
    txt = re.sub(r"\[/?ANSWER\]", "", txt)
    tool_contents = []
    def tool_replacer(m):
        content = m.group(1)
        idx = len(tool_contents)
        tool_contents.append(content)
        return f"\x00{idx}\x00"
    txt = re.sub(r"\[TOOL[^\]]*\](.*?)\[/TOOL\]", tool_replacer, txt, flags=re.DOTALL)
    txt = re.sub(r"\[TOOL[^\]]*\]|\[/TOOL\]", "", txt)
    cyrillic_match = re.search(r'[а-яА-Я]', txt)
    if cyrillic_match:
        first_cyrillic_idx = cyrillic_match.start()
        reasoning_part = txt[:first_cyrillic_idx]
        answer_part = txt[first_cyrillic_idx:]
        new_answer_part = answer_part
        for i, content in enumerate(tool_contents):
            marker = f"\x00{i}\x00"
            if marker in reasoning_part:
                new_answer_part = content + new_answer_part
        txt = new_answer_part
    for i, content in enumerate(tool_contents):
        marker = f"\x00{i}\x00"
        txt = txt.replace(marker, content)
    return txt.strip()

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
    except Exception:
        p2 = dict(payload); p2["stream"] = False
        return _orig_core_post(path, p2, *ar, **kw)
    r = {"message": {"content": "".join(parts), "thinking": "".join(thparts)}}
    for _kk in ("prompt_eval_count", "eval_count", "prompt_eval_duration", "eval_duration"):
        if _kk in lastj: r[_kk] = lastj[_kk]
    return r

_post_before_think = _stream_post

def _post_think_off(path, payload, *ar, **kw):
    if path == "/api/chat" and isinstance(payload, dict):
        payload = dict(payload)
        if int(settings.get("think_mode") or 0) == 0:
            payload["think"] = False
    return _post_before_think(path, payload, *ar, **kw)
