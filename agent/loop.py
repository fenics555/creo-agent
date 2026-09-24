# -*- coding: utf-8 -*-
"""АГЕНТ v15 — loop.py: очистка, стриминг, протокол, системный промт, ходовый цикл."""
import json, re, os, socket, threading, time, datetime
from concurrent.futures import ThreadPoolExecutor
import core
from core import log, trace
import settings
import tools_registry as TR
import users
import vision_tools as VI

def _clean(txt):
    """Очистка ответа модели перед показом и записью в историю.

    ЖИВАЯ НАХОДКА 24.09.2026: здесь жил хак «всё до первой кириллической буквы — это размышления,
    отрезать». Из-за него ответы, начинающиеся латиницей (путь, имя параметра, код, число),
    теряли начало, а куски «слеплялись». Теперь убираем ТОЛЬКО служебные теги, текст не трогаем."""
    if not txt:
        return ""
    out = re.sub(r"\[THINK\].*?\[/THINK\]", "", txt, flags=re.DOTALL)
    out = re.sub(r"<(?:think|thinking)>.*?</(?:think|thinking)>", "", out, flags=re.DOTALL | re.I)
    out = re.sub(r"\[/?ANSWER\]", "", out)
    out = re.sub(r"\[/?TOOL[^\]]*\]", "", out)
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip()


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
        with _ur.urlopen(req, timeout=_llm_t()) as resp:
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


import users


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


HOSTNAME = socket.gethostname()
PENDING = {}
LIVE = {}
LAST_META = {"p": 0, "r": 0, "think_block": "", "think_native": "", "cut": False}
UI_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "index.html")
_UI_CACHE = [0, b""]
STUB_PAGE = ("<html><head><meta charset='utf-8'><title>АГЕНТ v15</title></head>"
             "<body style='background:#1B1C1E;color:#E8E8E8;font:14px Segoe UI,sans-serif;padding:40px'>"
             "<h2>ВИТРИНА НЕ НАЙДЕНА</h2><p>Положи index.html в D:\\AI\\tools\\agent\\data\\ui\\</p></body></html>")


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


CREO_HINTS = ("creo", "крео", "creoson", "креосон", "jlink", "pfc", "модел", "детал", "сборк", "чертеж", "чертёж",
              "drw", "prt", "asm", "параметр", "отношен", "pdf", "plm", "специфик", "bom", "состав", "масса",
              "материал", "стандарт", "гост", "склад", "верси", "excel", "трейл", "ошибк", "инструмент", "база")


def _domain_question(q):
    """Домовый ли вопрос (Creo/чертежи/базы/программы).
    Живая находка 24.09.2026: заряд знаний (~25 тыс. токенов) грузился на ЛЮБОЙ вопрос — «привет» стоил
    42 секунды. Теперь заряд подаётся только когда вопрос действительно про дом."""
    q = (q or "").lower()
    return (not q) or any(h in q for h in CREO_HINTS)


def build_system(mode=1, question=""):
    if mode == 2:
        return """Ты — собеседник и помощник по любым темам. Язык ответа — русский; код, термины и формулы — как принято в теме.
В этом режиме нет доступа к Creo, файлам и базам: если вопрос требует живых данных, скажи «в режиме инженера я достану это из Creo или базы — переключи режим» и не выдумывай.
Формат: свободный текст; код внутри блоков с языком; служебных тегов нет.
Краткость ценится, но полнота решения важнее."""
    _SYS_CACHE.clear()  # надёжность: промпт всегда собирается свежим с диска
    p = ((load_skill("MANIFEST.md") or "") + "\n\n" + (load_skill("SKILL_agent_protocol.md") or DEFAULT_PROTO)).strip() + "\n"
    # ЗАРЯД ЗНАНИЙ (решение дома 24.09.2026). Раньше база знаний лежала в РАМ целиком (16 ГБ) и агент
    # «уже знал» скиллы; теперь память — FTS5-поиск, поэтому карта скиллов и стартовый набор Creo/CREOSON
    # подаются прямо в промпт (собирает dev\skills_charge.py). Главное направление дома — CREO.
    try:
        _ncx = int(settings.get("num_ctx") or 8192)
    except Exception:
        _ncx = 8192
    _charge = load_skill("SKILL_CHARGE.md")
    _start = load_skill("SKILL_CHARGE_START.md")
    _heavy = _domain_question(question)
    if _ncx >= 60000 and _start and _heavy:
        p += ("\n=== ЗАРЯД ЗНАНИЙ: СТАРТОВЫЙ НАБОР (это уже прочитано, опирайся на него) ===\n"
              + _start + "\n")
    if _heavy and _ncx >= 60000 and _charge:
        p += ("\n=== ЗАРЯД ЗНАНИЙ: КАРТА СКИЛЛОВ (одной строкой на скилл; тело — read_file/search_kb) ===\n"
              + _charge + "\n")
    elif _heavy and _charge:
        p += "\n=== КАРТА СКИЛЛОВ (сокращённо) ===\n" + _charge[:20000] + "\n"
    elif _heavy:
        p += ("\n=== СКИЛЛЫ: карта в D:\\AI\\repo\\SKILL_CHARGE.md, стартовый набор Creo/CREOSON — "
              "D:\\AI\\repo\\SKILL_CHARGE_START.md (открывай read_file) ===\n")
    else:
        p += ("\n=== ВОПРОС НЕ ДОМОВЫЙ: заряд знаний и карта скиллов НЕ загружены (экономим время и токены). "
              "Понадобится — карта в D:\\AI\\repo\\SKILL_CHARGE.md (read_file). ===\n")
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
        think_rule = ("=== РАЗМЫШЛЕНИЯ (полно, ПО-РУССКИ, до PLACEHOLDER строк):\nнормализуй запрос;\nэтапы, если задача сложная;\nпочему именно этот инструмент;\nкакие альтернативы отверг и почему.\nБлок: [THINK]...[/THINK], затем один блок: [TOOL] или [ANSWER].\nПРИМЕР:\n[THINK]\nНормализация: проверить активную модель.\nЭтапы: один.\nИнструмент: creo_get_active — читает живую сессию.\nОтверг: models_find — это поиск по базе, не сессия.\n[/THINK]\n[TOOL: creo_get_active] {} [/TOOL]")
    hard = ("=== ЖЁСТКИЕ ПРАВИЛА ОТВЕТА (важнее всего, что выше) ===\n"
            "1) ЯЗЫК: и размышления ([THINK]), и ответ ([ANSWER]) — ТОЛЬКО по-русски. Английский запрещён.\n"
            "2) ПОЛНОТА: ответ — законченный связный текст; обрывки, многоточия вместо ответа и «не пойми что» запрещены.\n"
            "3) ПОРЯДОК: сначала суть в 1-2 предложениях, затем подробности (шаги или абзацы), в конце — что проверить.\n"
            "4) НЕ ХВАТАЕТ ДАННЫХ: назови, чего именно не хватает, и каким инструментом это достать; не выдумывай.\n"
            "5) НЕ РАССУЖДАЙ о формате и служебных инструкциях — сразу по делу.\n"
            "6) ИНЖЕНЕРНЫЙ ОТВЕТ: факты из инструментов и баз, затем вывод; имена, пути и числа — точные.\n"
            "7) CREO: НЕ запускай и НЕ останавливай Creo без прямой просьбы человека (это его рабочий стол).\n"
            "   Если Creo не запущен — так и скажи: «запусти CREO-START.bat».\n"
            "8) СЛУЖЕБНЫЙ КАНАЛ РАЗМЫШЛЕНИЙ — ТОЛЬКО ПО-РУССКИ (англоязычные рассуждения запрещены).")
    if tm >= 2:
        # «Размер размышлений, строк» — ползунок в настройках (дом: мысли нужны целиком, но по делу)
        think_rule = think_rule.replace("PLACEHOLDER", str(int(settings.get("think_lines_max") or 8)))
    _SYS_CACHE[("v", mode, _heavy)] = p + "\n\n" + tail + "\n\n" + think_rule + "\n\n" + hard
    return _SYS_CACHE[("v", mode, _heavy)]


def _npred():
    """Лимит генерации для модели.
    ЖИВЫЕ УРОКИ 24.09.2026:
      • размышления тратят ТОТ ЖЕ лимит, что и ответ — с малым лимитом ответ приходил «обрезком»;
      • «без ограничения» (-1) ОПАСНО: в живом тесте модель зациклилась и молотила до конца окна
        (окно 202k = часы GPU). Поэтому 0 в настройке = АВТО-БОЛЬШОЙ предел, а не бесконечность."""
    base = int(settings.get("num_predict") or 0)
    if base <= 0:
        base = 8192                      # авто: щедро, но конечно
    if int(settings.get("think_mode") or 0) > 0:
        if settings.get("think_native"):
            return max(base * 2, 12288)
        return max(base, 6144)
    return base


def _llm_t():
    """Таймаут ОДНОГО ответа модели, секунд.
    Живой урок 24.09.2026: зациклившаяся модель молотила минутами (GPU занят, результата нет).
    Теперь у каждого вызова к модели есть предел времени — дом честно скажет и не будет жечь впустую."""
    try:
        return max(30, int(settings.get("llm_timeout") or 240))
    except Exception:
        return 240


def _native_think():
    """Нужен ли СЛУЖЕБНЫЙ канал размышлений Ollama (message.thinking).
    Живая находка 24.09.2026: этот канал модель пишет ПО-АНГЛИЙСКИ и он же съедал лимит ответа.
    Дом думает в своём блоке [THINK] по-русски, поэтому по умолчанию канал выключен."""
    return bool(settings.get("think_mode")) and bool(settings.get("think_native"))


def beh():
    """Опции запроса к модели. Окно (num_ctx) задаём ТОЛЬКО если человек вписал число:
    0/пусто = не трогаем — Ollama возьмёт окно самой модели (ничего не «схлопнется»)."""
    steps = int(settings.get("steps_max") or 6)
    temp = (settings.get("auto_temperature") if settings.get("auto_mode") else settings.get("creativity")) or 10
    opts = {"temperature": temp / 100.0,
            "top_p": float(settings.get("top_p") or 0.9),
            "num_predict": _npred()}
    try:
        ncx = int(settings.get("num_ctx") or 0)
    except Exception:
        ncx = 0
    if ncx <= 0:
        # «0 = как в модели»: ВАЖНО — Ollama по умолчанию даёт всего 4096 токенов (её FAQ),
        # поэтому окно модели спрашиваем у неё самой (/api/show) и подставляем.
        try:
            import settings_tools as _st37
            ncx = int(_st37._model_info(settings.model_for("chat")).get("ctx") or 0)
        except Exception:
            ncx = 0
    if ncx > 0:
        opts["num_ctx"] = ncx
    return opts, steps


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
    # ТЕРПИМОСТЬ К ФОРМАТУ (у моделей разный стиль вывода — ловим все встречавшиеся варианты):
    #  <ANSWER>…</ANSWER>, строка «ОТВЕТ: …», а также ответ/вызов инструмента внутри ```json.
    m = re.search(r"<ANSWER>\s*(.*?)\s*</ANSWER>", text, re.S)
    if m: return "answer", m.group(1).strip(), None, think_text
    m = re.search(r"^\s*(?:ОТВЕТ|ANSWER)\s*[:：]\s*(.+)$", text, re.S | re.M)
    if m: return "answer", m.group(1).strip(), None, think_text
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    if m:
        try:
            _j = json.loads(m.group(1))
            if isinstance(_j, dict):
                _nm = str(_j.get("tool") or _j.get("name") or "")
                if _nm and TR.get(_nm):
                    return "tool", _nm, {k: v for k, v in _j.items() if k not in ("tool", "name")}, think_text
                if _j.get("answer"):
                    return "answer", str(_j["answer"]), None, think_text
        except Exception:
            pass
    m = re.search(r"\[ANSWER\]\s*(.*?)\[/ANSWER\]", text, re.S)
    if m: return "answer", m.group(1).strip(), None, think_text
    if "[ANSWER]" in text and "[/ANSWER]" not in text:
        return "answer", text.split("[ANSWER]", 1)[1].strip(), None, think_text
    ts = text.strip()
    if TR.get(ts): return "tool", ts, {}, think_text
    return "invalid", text.strip(), None, think_text


_NUDGE = "[СЛУЖЕБНОЕ] Ответ не в формате. Дай ровно один блок: [TOOL: имя] {\"параметр\": \"значение\"} [/TOOL] или [ANSWER] полный ответ по-русски [/ANSWER]. Слово «текст» само по себе — не ответ. Ответ не обрывай. Ничего до и после блока."
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
    """Хвост диалога в контекст модели. Размеры — из настроек (ползунки «История: вопрос/ответ»)."""
    c = core.db()
    rows = c.execute("SELECT q,a FROM history WHERE client=? ORDER BY id DESC LIMIT 8", (client,)).fetchall()
    c.close()
    qn = int(settings.get("hist_q_chars") or 1000)
    an = int(settings.get("hist_a_chars") or 1500)
    out = []
    for q, a in reversed(rows):
        out.append({"role": "user", "content": q[:qn]})
        out.append({"role": "assistant", "content": a[:an]})
    return out


def run_loop(messages, client, has_link=False, on_step=None, opts_and_steps=None):
    if opts_and_steps:
        opts, steps_max = opts_and_steps
    else:
        opts, steps_max = beh()
    LAST_META.update(p=0, r=0, think_block="", think_native="", cut=False)
    steps_log, last_res, sig_prev, invalid_cnt = [], "", None, 0

    def _log(line): steps_log.append(line); LIVE.setdefault(client, []).append(line)

    for step in range(steps_max):
        r = None
        for attempt in (1, 2):
            try:
                use_opts = dict(opts)
                if invalid_cnt: use_opts = dict(use_opts, temperature=0)
                _thk = _native_think()
                r = core.post("/api/chat", {"model": settings.model_for("chat"),
                                            "stream": False, "think": _thk, "options": use_opts, "messages": messages}, t=_llm_t())
                break
            except Exception as e:
                if attempt == 1 and "500" in str(e):
                    time.sleep(2); continue
                _em = str(e)
                if "timed out" in _em.lower() or "timeout" in _em.lower():
                    _em = ("модель не уложилась в отведённое время (%d с) — похоже, зациклилась. "
                           "Уменьши «Длина ответа (токенов)» или выбери модель попроще." % _llm_t())
                return {"answer": _clean("ошибка модели: %s" % _em), "think": "", "steps": step + 1, "log": steps_log}
        raw = (r.get("message") or {}).get("content") or ""
        try: LAST_META["p"] += r.get("prompt_eval_count") or 0; LAST_META["r"] += r.get("eval_count") or 0
        except Exception: pass
        if (r.get("done_reason") or "") == "length":
            # ЖИВАЯ НАХОДКА 24.09.2026: модель упиралась в лимит, а в окне это выглядело просто «обрезком».
            LAST_META["cut"] = True
            _log("⚠ упёрлись в лимит генерации — подними «Макс токенов ответа» (настройки, только админ)")
        kind, payload, args, think = parse_model(raw)
        # Мысли собираем из ДВУХ источников и ничего не выбрасываем:
        #  блок [THINK] из ответа (русский план) и служебный канал модели (message.thinking).
        if think:
            LAST_META["think_block"] = think
        native = ((r.get("message") or {}).get("thinking") or "").strip()
        if native:
            LAST_META["think_native"] = native
        think = think or native
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
            return {"answer": _clean(txt), "think": think, "steps": step + 1, "log": steps_log}
        if kind == "answer" and len(payload) < 80 and payload.strip().lower() in _NUDGE.lower():
            _log("echo_guard: %r" % payload[:40]); kind, payload = "invalid", raw
        if kind == "invalid":
            invalid_cnt += 1
            if last_res and len(payload or "") > 150 and not _refusal(payload):
                _log("parse_invalid -> проза после результата = ответ")
                return {"answer": _clean(payload), "think": think, "steps": step + 1, "log": steps_log}
            if invalid_cnt < 3:
                nudge = _ACCESS_NUDGE if _refusal(payload) else _NUDGE
                messages.append({"role": "assistant", "content": raw})
                messages.append({"role": "user", "content": nudge})
                _log("parse_invalid"); continue
            pl = (payload or "").strip()
            tail = (" Инструмент вернул: «%s»." % last_res[:200]) if last_res else ""
            if _refusal(pl) or (len(pl) < 80 and pl.lower() in _NUDGE.lower()):
                pl = "Ответ модели не распознан." + tail + " Уточни запрос (пример: models_where q=<имя детали>) или введи прямую команду инструмента."
            return {"answer": _clean(pl), "think": think, "steps": step + 1, "log": steps_log}
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
            _log("%s(%s) → %s" % (name, "без параметров" if not args else json.dumps(args, ensure_ascii=False), _two(res)))
        last_res = res
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": "[РЕЗУЛЬТАТ %s]: %s" % (name, res[:4000])})
    return {"answer": last_res or "не уложился в шаги", "think": think, "steps": steps_max, "log": steps_log}


def ask(q, client, image=None, on_step=None, mode=None):
    # 1. Determine mode
    eff_mode = 1
    if mode in (1, 2):
        eff_mode = mode
    elif q.strip().startswith("chat "):
        eff_mode = 2
        q = q.strip()[5:]
    elif q.strip().startswith("agent "):
        eff_mode = 1
        q = q.strip()[6:]
    else:
        eff_mode = settings.get_for(client, "chat_mode", 1)
        if not isinstance(eff_mode, int) or eff_mode not in (1, 2):
            eff_mode = 1

    # Check for engineering mode (doc mode)
    doc_keywords = ["спека", "документ", "пиши полностью", "развёрнуто", "подробный отчёт"]
    doc = any(kw in q.lower() for kw in doc_keywords)


    # 2. Check for direct tool call (works in both modes)
    name = q.strip()
    t = TR.get(name)
    if t and not image:
        if msg := _role_check(client, name):
            return {"answer": msg, "think": "", "steps": 1, "log": ["%s(прямой вызов) → ЗАПРЕТ РОЛИ" % name]}
        if t.get("approval") and eff_mode != 2:
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
        return {"answer": res, "think": "", "steps": 1, "log": ["%s(прямой вызов) → %s" % (name, _two(res))]}

    # 2.5 Fast router for special commands
    if q.strip().lower().startswith("угол "):
        import calc_tools
        rest = q.strip()[5:].strip()
        res = calc_tools.tool_angle(text=rest)
        return {"answer": res, "think": "", "steps": 1, "log": ["fast_router(угол)"]}

    # 3. If mode 2, handle it immediately
    if eff_mode == 2:
        q2 = VI.attach(q, image, client)
        messages = [{"role": "system", "content": build_system(mode=2)}] + hist_block(client) + [{"role": "user", "content": q2}]
        opts, _ = beh()
        if doc:
            opts["num_predict"] = max(4096, _npred())
            messages[0]["content"] += "\n=== ДОКУМЕНТ: краткость отменена. Пиши полный текст внутри [ANSWER], без обрыва."
        r = core.post("/api/chat", {
            "model": settings.model_for("chat"),
            "stream": False,
            "think": _native_think(),
            "options": opts,
            "messages": messages,
        }, t=_llm_t())
        return {
            "answer": _clean(r.get("message", {}).get("content", "")),
            "think": r.get("message", {}).get("thinking", ""),
            "steps": 1,
            "log": ["chat_mode"]
        }

    # 4. Else mode 1 (existing logic)
    q2 = VI.attach(q, image, client)
    LIVE[client] = []
    m2 = re.match(r"^([A-Za-z0-9_]+)\s+([A-Za-z0-9_]+)=(\S+)$", q.strip())
    if m2 and not image:
        t2 = TR.get(m2.group(1))
        if t2 and m2.group(2) in (t2.get("params") or {}):
            if msg := _role_check(client, m2.group(1)):
                return {"answer": msg, "think": "", "steps": 1, "log": [m2.group(1) + "(прямой вызов)"]}
            if t2.get("approval"):
                pid = datetime.datetime.now().strftime("%H%M%S%f")
                PENDING[pid] = {"name": m2.group(1), "args": {m2.group(2): m2.group(3)},
                                "client": client, "messages": [], "raw": ""}
                return {"answer": "[СОГЛАСОВАНИЕ] операция %s ждёт подтверждения (id %s)" % (m2.group(1), pid),
                        "think": "", "steps": 1, "log": [m2.group(1) + "(прямой вызов)"]}
            try:
                res = str(t2["fn"](**{m2.group(2): m2.group(3)}))
            except Exception as e:
                res = "ошибка исполнения %s: %s" % (m2.group(1), e)
            return {"answer": res, "think": "", "steps": 1, "log": [m2.group(1) + "(прямой вызов) → " + _two(res)]}
    q2 = q2 + ("\n\n[СЛУЖЕБНОЕ: думай и отвечай ТОЛЬКО по-русски. Один ход = один блок: [TOOL] или [ANSWER]. "
               "Никакого текста до и после блока. Ответ — законченный и полный, без обрывов и многоточий.]")
    messages = [{"role": "system", "content": build_system(mode=eff_mode, question=q2)}] + hist_block(client) + [{"role": "user", "content": q2}]
    _ta = time.time()
    LIVE_TOK[client] = []
    LIVE_THINK[client] = []

    def _push(t): LIVE_TOK.setdefault(client, []).append(t)
    threading.current_thread()._tokpush = _push
    threading.current_thread()._tokclient = client
    r = run_loop(messages, client, has_link=("http" in q), on_step=on_step)
    try:
        _tools_chain = []
        for _ln in r.get("log", []):
            _m = re.match(r"^([A-Za-z0-9_]+)\(", _ln)
            if _m and _m.group(1) not in _tools_chain:
                _tools_chain.append(_m.group(1))
        _ok = (not _refusal(r.get("answer", ""))) and len(r.get("answer", "")) > 200
        with open(core.DATA_DIR / "chains.jsonl", "a", encoding="utf-8") as _f:
            _f.write(json.dumps({"ts": datetime.datetime.now().isoformat(), "client": client,
                                 "q": q[:300], "tools": _tools_chain, "ok": bool(_ok)},
                                ensure_ascii=False) + "\n")
    except Exception:
        pass
    if int(settings.get("log_mode") or 1) >= 1:
        r.setdefault("log", []).append("⏱ %dмс · 🔢 %d ток (промт %d + ответ %d) · шагов: %d" % (int((time.time() - _ta) * 1000), LAST_META["p"] + LAST_META["r"], LAST_META["p"], LAST_META["r"], r.get("steps", 1)))
    if LAST_META.get("cut"):
        r.setdefault("log", []).append("⚠ ОБРЕЗАНО лимитом токенов — увеличь «Макс токенов ответа» в настройках (только админ)")
    # Мысли отдаём в окно ДВУМЯ полями, чтобы ничего не терялось:
    #  think       — служебный канал модели (как правило, по-английски),
    #  think_block — блок [THINK] из ответа (по-русски, по нашим правилам).
    r["think_block"] = LAST_META.get("think_block") or ""
    if not r.get("think"):
        r["think"] = LAST_META.get("think_native") or ""
    r["think_native"] = LAST_META.get("think_native") or ""
    r["cut"] = bool(LAST_META.get("cut"))
    c = core.db()
    c.execute("INSERT INTO history(client,q,a,ts) VALUES(?,?,?,?)", (client, q, r["answer"][:2000], datetime.datetime.now().isoformat()))
    c.commit(); c.close()
    return r


def do_approve(pid, okf):
    pid = str(pid)
    p = PENDING.pop(pid, None)
    if not p: return {"res": "согласование устарело или уже выполнено, повтори команду"}
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
        return {"res": res, "answer": _clean(r["answer"]), "think": r.get("think", ""), "log": r.get("log", [])}
    return {"res": res}

