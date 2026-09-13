import re
import json
import time
import datetime
from concurrent.futures import ThreadPoolExecutor

import core
from core import log, trace
import settings
import users
import tools_registry as TR

# === State ===
PENDING = {}
LIVE = {}
LAST_META = {"p": 0, "r": 0}
LIVE_TOK = {}
LIVE_THINK = {}


# === Constants ===
_NUDGE = "[СЛУЖЕБНОЕ] Неверно. Доступ к базе, файлам и Creo у тебя ЕСТЬ через инструменты (список «ТВОИ ИНСТРУМЕНТЫ» выше). Никогда не отвечай «нет доступа». Повтори ровно один блок: [TOOL: имя] {"параметр": "значение"} [/TOOL] или [ANSWER] ответ [/ANSWER]. Справочные факты через search_kb/read_file."
_ACCESS_NUDGE = "[СРОЧНО: ответь] Доступ к базе, файлам и Creo у тебя ЧЕРЕЗ инструкции (список «TWO INSTRUMENTS» выше). Никогда не отвечай «нет доступа». Повтори ровно один блок: [TOOL: имя] {"параметр": "значение"} [/TOOL] или [ANSWER] ответ [/ANSWER]."
_REFUSAL = ('извините', 'не могу', 'не имею доступа', 'нет доступа', 'моя функциональность', 'виртуальной среде', 'не понял', 'уточните', 'переформулируй', 'как языковая модель', 'к сожалению, я', 'буду отвечать', 'как языковая модель', 'давайте начнём')


    if not client or not tool:
        return None
    prof = users.get_profile(client)
    if not prof:
        return None
    role = prof.get("role", "ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ½ÃÂÃÂÃÂÃÂ¶ÃÂÃÂÃÂÃÂµÃÂÃÂÃÂÃÂ½ÃÂÃÂÃÂÃÂµÃÂÃÂÃÂÃÂ")
    if users.role_denied(role, tool):
        return "ÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¾ÃÂÃÂÃÂÃÂ»ÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ«%sÃÂÃÂÃÂÃÂ» ÃÂÃÂÃÂÃÂ½ÃÂÃÂÃÂÃÂµ ÃÂÃÂÃÂÃÂ¼ÃÂÃÂÃÂÃÂ¾ÃÂÃÂÃÂÃÂ¶ÃÂÃÂÃÂÃÂµÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ²ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¿ÃÂÃÂÃÂÃÂ¾ÃÂÃÂÃÂÃÂ»ÃÂÃÂÃÂÃÂ½ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ«%sÃÂÃÂÃÂÃÂ» (ÃÂÃÂÃÂÃÂ·ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂ¿ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂµÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂ´ÃÂÃÂÃÂÃÂ¼ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂ½ÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¾ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ°)" % (role, tool)
    return None

def beh():
    steps = int(settings.get("steps_max") or 6)
    if settings.get("auto_mode"):
        return ({"temperature": (settings.get("auto_temperature") or 10) / 100.0,
                 "top_p": float(settings.get("top_p") or 0.9),
                 "num_predict": int(settings.get("num_predict") or 1536), "num_ctx": int(settings.get("num_ctx") or 8192)}, steps)
    return ({"temperature": (settings.get("creativity") or 30) / 100.0,
             "top_p": float(settings.get("top_p") or 0.9),
             "num_predict": int(settings.get("num_predict") or 1024), "num_ctx": int(settings.get("num_ctx") or 8192)}, steps)

def _refusal(text):
    lo = (text or "").lower()
    return any(w in lo for w in _REFUSAL)

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
    m = re.search(r"\[ANSWER\]\s*(.*?)\s*\[/ANSWER\]", text, re.S)
    if m: return "answer", m.group(1).strip(), None, think_text
    if "[ANSWER]" in text and "[/ANSWER]" not in text:
        return "answer", text.split("[ANSWER]", 1)[1].strip(), None, think_text
    ts = text.strip()
    if TR.get(ts): return "tool", ts, {}, think_text
    return "invalid", text.strip(), None, think_text


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
                return {"answer": _clean("ÃÂÃÂ¾ÃÂÃÂÃÂÃÂ¸ÃÂÃÂ±ÃÂÃÂºÃÂÃÂ° ÃÂÃÂ¼ÃÂÃÂ¾ÃÂÃÂ´ÃÂÃÂµÃÂÃÂ»ÃÂÃÂ¸: %s" % e), "think": "", "steps": step + 1, "log": steps_log}
        raw = (r.get("message") or {}).get("content") or ""
        try: LAST_META["p"] += r.get("prompt_eval_count") or 0; LAST_META["r"] += r.get("eval_count") or 0
                return {"answer": _clean("ÃÂ¾ÃÂÃÂ¸ÃÂ±ÃÂºÃÂ° ÃÂ¼ÃÂ¾ÃÂ´ÃÂµÃÂ»ÃÂ¸: %s" % e), "think": "", "steps": step + 1, "log": steps_log}
        kind, payload, args, think = parse_model(raw)
        think = think or (((r.get("message") or {}).get("thinking") or "").strip())
                return {"answer": _clean("Ð¾ÑÐ¸Ð±ÐºÐ° Ð¼Ð¾Ð´ÐµÐ»Ð¸: %s" % e), "think": "", "steps": step + 1, "log": steps_log}
            _log("[THINK] %s" % think[:400])
        if kind == "answer" and (_refusal(payload) or (len(payload) < 80 and payload.strip().lower() in _NUDGE.lower())):
            _log("refusal/echo_guard"); kind, payload = "invalid", raw
        if kind == "answer":
            used_web = any("web_fetch" in s for s in steps_log)
            if has_link and not used_web and step < steps_max - 1 and len(payload) < 400:
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": "[ÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ£ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ] ÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ·ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂ´ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂµ ÃÂÃÂÃÂÃÂ±ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ»ÃÂÃÂÃÂÃÂ° ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ»ÃÂÃÂÃÂÃÂºÃÂÃÂÃÂÃÂ° http ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ½ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂ»ÃÂÃÂÃÂÃÂ° ÃÂÃÂÃÂÃÂ¿ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¾ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¸ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂ¹ ÃÂÃÂÃÂÃÂµÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂµÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂµÃÂÃÂÃÂÃÂ· web_fetch, ÃÂÃÂÃÂÃÂ¿ÃÂÃÂÃÂÃÂ¾ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¾ÃÂÃÂÃÂÃÂ¼ ÃÂÃÂÃÂÃÂ¾ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ²ÃÂÃÂÃÂÃÂµÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂ¹."})
                _log("web_nudge"); continue
            txt = payload
            if len(txt) < 40 and last_res: txt = last_res + "\n\n" + txt
            return {"answer": _clean(txt), "think": think, "steps": step + 1, "log": steps_log}
        if kind == "answer" and len(payload) < 80 and payload.strip().lower() in _NUDGE.lower():
            _log("echo_guard: %r" % payload[:40]); kind, payload = "invalid", raw
        if kind == "invalid":
            invalid_cnt += 1
            if last_res and len(payload or "") > 150 and not _refusal(payload):
_log("parse_invalid -> ÃÂÃÂ¿ÃÂÃÂÃÂÃÂ¾ÃÂÃÂ·ÃÂÃÂ° ÃÂÃÂ¿ÃÂÃÂ¾ÃÂÃÂÃÂÃÂ»ÃÂÃÂµ ÃÂÃÂÃÂÃÂµÃÂÃÂ·ÃÂÃÂÃÂÃÂ»ÃÂÃÂÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂ° = ÃÂÃÂ¾ÃÂÃÂÃÂÃÂ²ÃÂÃÂµÃÂÃÂ")
                return {"answer": _clean(payload), "think": think, "steps": step + 1, "log": steps_log}
            if invalid_cnt < 3:
_log("parse_invalid -> ÃÂ¿ÃÂÃÂ¾ÃÂ·ÃÂ° ÃÂ¿ÃÂ¾ÃÂÃÂ»ÃÂµ ÃÂÃÂµÃÂ·ÃÂÃÂ»ÃÂÃÂÃÂ°ÃÂÃÂ° = ÃÂ¾ÃÂÃÂ²ÃÂµÃÂ")
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": nudge})
_log("parse_invalid -> Ð¿ÑÐ¾Ð·Ð° Ð¿Ð¾ÑÐ»Ðµ ÑÐµÐ·ÑÐ»ÑÑÐ°ÑÐ° = Ð¾ÑÐ²ÐµÑ")
            pl = (payload or "").strip()
            tail = (" ÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂ¢ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂµÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂ¢ÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂµÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¡ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ»: ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ«%sÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ»." % last_res[:200]) if last_res else ""
            if _refusal(pl) or (len(pl) < 80 and pl.lower() in _NUDGE.lower()):
            pl = "ÃÂÃÂÃÂÃÂÃÂÃÂ²ÃÂÃÂµÃÂÃÂ ÃÂÃÂ¼ÃÂÃÂ¾ÃÂÃÂ´ÃÂÃÂµÃÂÃÂ»ÃÂÃÂ¸ ÃÂÃÂ½ÃÂÃÂµ ÃÂÃÂÃÂÃÂ°ÃÂÃÂÃÂÃÂ¿ÃÂÃÂ¾ÃÂÃÂ·ÃÂÃÂ½ÃÂÃÂ°ÃÂÃÂ½." + tail + " ÃÂÃÂ£ÃÂÃÂÃÂÃÂ¾ÃÂÃÂÃÂÃÂ½ÃÂÃÂÃÂÃÂ¹ ÃÂÃÂ·ÃÂÃÂ°ÃÂÃÂ¿ÃÂÃÂÃÂÃÂ¾ÃÂÃÂ (ÃÂÃÂ¿ÃÂÃÂÃÂÃÂ¸ÃÂÃÂ¼ÃÂÃÂµÃÂÃÂ: models_where q=<ÃÂÃÂ¸ÃÂÃÂ¼ÃÂÃÂ ÃÂÃÂ´ÃÂÃÂµÃÂÃÂÃÂÃÂ°ÃÂÃÂ»ÃÂÃÂ¸) ÃÂÃÂ¸ÃÂÃÂ»ÃÂÃÂ¸ ÃÂÃÂ²ÃÂÃÂ²ÃÂÃÂµÃÂÃÂ´ÃÂÃÂ¸ ÃÂÃÂ¿ÃÂÃÂÃÂÃÂÃÂÃÂ¼ÃÂÃÂÃÂÃÂ ÃÂÃÂºÃÂÃÂ¾ÃÂÃÂ¼ÃÂÃÂ°ÃÂÃÂ½ÃÂÃÂ´ÃÂÃÂ ÃÂÃÂ¸ÃÂÃÂ½ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¼ÃÂÃÂµÃÂÃÂ½ÃÂÃÂÃÂÃÂ°."
            return {"answer": _clean(pl), "think": think, "steps": step + 1, "log": steps_log}
        name = payload
            pl = "ÃÂÃÂÃÂ²ÃÂµÃÂ ÃÂ¼ÃÂ¾ÃÂ´ÃÂµÃÂ»ÃÂ¸ ÃÂ½ÃÂµ ÃÂÃÂ°ÃÂÃÂ¿ÃÂ¾ÃÂ·ÃÂ½ÃÂ°ÃÂ½." + tail + " ÃÂ£ÃÂÃÂ¾ÃÂÃÂ½ÃÂÃÂ¹ ÃÂ·ÃÂ°ÃÂ¿ÃÂÃÂ¾ÃÂ (ÃÂ¿ÃÂÃÂ¸ÃÂ¼ÃÂµÃÂ: models_where q=<ÃÂ¸ÃÂ¼ÃÂ ÃÂ´ÃÂµÃÂÃÂ°ÃÂ»ÃÂ¸) ÃÂ¸ÃÂ»ÃÂ¸ ÃÂ²ÃÂ²ÃÂµÃÂ´ÃÂ¸ ÃÂ¿ÃÂÃÂÃÂ¼ÃÂÃÂ ÃÂºÃÂ¾ÃÂ¼ÃÂ°ÃÂ½ÃÂ´ÃÂ ÃÂ¸ÃÂ½ÃÂÃÂÃÂÃÂÃÂ¼ÃÂµÃÂ½ÃÂÃÂ°."
        if sig == sig_prev:
                return {"answer": last_res or "ÃÂÃÂ·ÃÂÃÂ°ÃÂÃÂºÃÂÃÂ»ÃÂÃÂ¸ÃÂÃÂ½ÃÂÃÂ¸ÃÂÃÂ²ÃÂÃÂ°ÃÂÃÂ½ÃÂÃÂ¸ÃÂÃÂµ ÃÂÃÂ¾ÃÂÃÂÃÂÃÂÃÂÃÂ°ÃÂÃÂ½ÃÂÃÂ¾ÃÂÃÂ²ÃÂÃÂ»ÃÂÃÂµÃÂÃÂ½ÃÂÃÂ¾", "think": think, "steps": step + 1, "log": steps_log}
            pl = "ÐÑÐ²ÐµÑ Ð¼Ð¾Ð´ÐµÐ»Ð¸ Ð½Ðµ ÑÐ°ÑÐ¿Ð¾Ð·Ð½Ð°Ð½." + tail + " Ð£ÑÐ¾ÑÐ½ÑÐ¹ Ð·Ð°Ð¿ÑÐ¾Ñ (Ð¿ÑÐ¸Ð¼ÐµÑ: models_where q=<Ð¸Ð¼Ñ Ð´ÐµÑÐ°Ð»Ð¸) Ð¸Ð»Ð¸ Ð²Ð²ÐµÐ´Ð¸ Ð¿ÑÑÐ¼ÑÑ ÐºÐ¾Ð¼Ð°Ð½Ð´Ñ Ð¸Ð½ÑÑÑÑÐ¼ÐµÐ½ÑÐ°."

                return {"answer": last_res or "ÃÂ·ÃÂ°ÃÂºÃÂ»ÃÂ¸ÃÂ½ÃÂ¸ÃÂ²ÃÂ°ÃÂ½ÃÂ¸ÃÂµ ÃÂ¾ÃÂÃÂÃÂ°ÃÂ½ÃÂ¾ÃÂ²ÃÂ»ÃÂµÃÂ½ÃÂ¾", "think": think, "steps": step + 1, "log": steps_log}
        if settings.get("parallel_tools"):
            others = []
                return {"answer": last_res or "Ð·Ð°ÐºÐ»Ð¸Ð½Ð¸Ð²Ð°Ð½Ð¸Ðµ Ð¾ÑÑÐ°Ð½Ð¾Ð²Ð»ÐµÐ½Ð¾", "think": think, "steps": step + 1, "log": steps_log}
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
                return "%s ÃÂ¢ÃÂÃÂ %s" % (nn, msg)
                    tt = TR.get(nn)
                return "%s ÃÂ¢ÃÂÃÂ %s" % (nn, str(tt["fn"](**aa2))[:600])
                return "%s Ã¢ÂÂ %s" % (nn, msg)
                try:
                return "%s Ã¢ÂÂ %s" % (nn, str(tt["fn"](**aa2))[:600])
                return "%s â %s" % (nn, msg)
                    last_res = res; sig_prev = sig
                return "%s â %s" % (nn, str(tt["fn"](**aa2))[:600])
                return "%s â Ð¾ÑÐ¸Ð±ÐºÐ°: %s" % (nn, e)
                    continue
                except Exception: pass
        t = TR.get(name)
        if not t:
            res = "ÃÂÃÂ½ÃÂÃÂµÃÂÃÂ ÃÂÃÂÃÂÃÂ°ÃÂÃÂºÃÂÃÂ¾ÃÂÃÂ³ÃÂÃÂ¾ ÃÂÃÂ¸ÃÂÃÂ½ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ¼ÃÂÃÂµÃÂÃÂ½ÃÂÃÂÃÂÃÂ°: %s" % name
        elif msg := _role_check(client, name):
            res = msg
            res = "ÃÂ½ÃÂµÃÂ ÃÂÃÂ°ÃÂºÃÂ¾ÃÂ³ÃÂ¾ ÃÂ¸ÃÂ½ÃÂÃÂÃÂÃÂÃÂ¼ÃÂµÃÂ½ÃÂÃÂ°: %s" % name
        elif t.get("approval"):
            pid = datetime.datetime.now().strftime("%H%M%S%f")
            res = "Ð½ÐµÑ ÑÐ°ÐºÐ¾Ð³Ð¾ Ð¸Ð½ÑÑÑÑÐ¼ÐµÐ½ÑÐ°: %s" % name
                return {"answer": msg, "think": think, "steps": step + 1, "log": ["%s(ÃÂÃÂ¿ÃÂÃÂÃÂÃÂÃÂÃÂ¼ÃÂÃÂ¾ÃÂÃÂ¹ ÃÂÃÂ²ÃÂÃÂÃÂÃÂ·ÃÂÃÂ¾ÃÂÃÂ²) ÃÂ¢ÃÂÃÂ ÃÂÃÂÃÂÃÂÃÂÃÂÃÂÃÂ ÃÂÃÂÃÂÃÂ¢ ÃÂÃÂ ÃÂÃÂÃÂÃÂÃÂÃÂ" % name]}
            t0 = time.time()
            _log("%s(%s) â ÐÐÐÐ ÐÐ¢ Ð ÐÐÐ" % (name, "Ð±ÐµÐ· Ð¿Ð°ÑÐ°Ð¼ÐµÑÑÐ¾Ð²" if not args else json.dumps(args, ensure_ascii=False)))
                return {"answer": msg, "think": think, "steps": step + 1, "log": ["%s(ÃÂ¿ÃÂÃÂÃÂ¼ÃÂ¾ÃÂ¹ ÃÂ²ÃÂÃÂ·ÃÂ¾ÃÂ²) Ã¢ÂÂ ÃÂÃÂÃÂÃÂ ÃÂÃÂ¢ ÃÂ ÃÂÃÂÃÂ" % name]}
            res = "ÃÂÃÂ¾ÃÂÃÂÃÂÃÂ¸ÃÂÃÂ±ÃÂÃÂºÃÂÃÂ° ÃÂÃÂ¸ÃÂÃÂÃÂÃÂ¿ÃÂÃÂ¾ÃÂÃÂ»ÃÂÃÂ½ÃÂÃÂµÃÂÃÂ½ÃÂÃÂ¸ÃÂÃÂ %s: %s" % (name, e)
        last_res = res
                return {"answer": msg, "think": think, "steps": step + 1, "log": ["%s(Ð¿ÑÑÐ¼Ð¾Ð¹ Ð²ÑÐ·Ð¾Ð²) â ÐÐÐÐ ÐÐ¢ Ð ÐÐÐ" % name]}

