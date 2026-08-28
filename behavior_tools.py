# -*- coding: utf-8 -*-
r"""АГЕНТ v12 — ПРОТОКОЛ ПОВЕДЕНИЯ ИИ: формат, язык, против выдумывания."""
import time
import core
from core import log
import settings
import tools_registry as TR

REPORT = core.BASE / "behavior_report.txt"
TESTS = [
    ("какая модель открыта в Creo?", "tool"), ("статус Creo", "tool"),
    ("найди модель korpus", "tool"), ("сколько файлов в базе знаний?", "tool"),
    ("кто залогинен?", "tool"), ("разбери последний трейл", "tool"),
    ("текущие настройки", "tool"), ("привет", "answer"),
    ("спасибо", "answer"), ("что такое пружина сжатия?", "answer"),
]

def _lat(s):
    l = [c for c in s if c.isalpha()]
    return (sum(1 for c in l if c.isascii()) / len(l)) if l else 0.0

def run():
    import agent
    lines = ["=== ПОВЕДЕНИЕ ИИ %s | %s ===" % (time.strftime("%d.%m.%Y %H:%M"), settings.get("llm_model"))]
    ok = warn = bad = 0
    for q, want in TESTS:
        t0 = time.time()
        try:
            r = core.post("/api/chat", {"model": settings.get("llm_model") or "deepseek-r1:14b", "stream": False,
                          "options": {"temperature": 0.1, "top_p": 0.9, "num_predict": 512},
                          "messages": [{"role": "system", "content": agent.build_system()},
                                       {"role": "user", "content": q + "\n\n[СЛУЖЕБНОЕ: по-русски, один блок.]"}]}, t=300)
            raw = (r.get("message") or {}).get("content") or ""
            kind, payload, args = agent.parse_model(raw)
            ms = int((time.time() - t0) * 1000)
            if kind == "invalid": mark, note = "X", "формат не распознан"
            elif kind == "tool":
                if not TR.get(payload): mark, note = "X", "неизвестный инструмент %s" % payload
                elif want == "tool": mark, note = "OK", "[TOOL: %s]" % payload
                else: mark, note = "!!", "дал [TOOL], ждали [ANSWER]"
            else:
                ra = _lat(payload)
                if want == "tool": mark, note = "X", "выдумал [ANSWER] (лат. %.0f%%)" % (ra * 100)
                elif ra > 0.25: mark, note = "!!", "[ANSWER] лат. %.0f%%" % (ra * 100)
                else: mark, note = "OK", "[ANSWER] рус. (лат. %.0f%%)" % (ra * 100)
        except Exception as e:
            mark, note, ms = "X", "ошибка: %s" % e, int((time.time() - t0) * 1000)
        if mark == "OK": ok += 1
        elif mark == "!!": warn += 1
        else: bad += 1
        lines.append("%s %-38s -> %s (%s, %dмс)" % (mark, q, want, note, ms))
    lines.append("ИТОГО: OK %d | !! %d | X %d" % (ok, warn, bad))
    try: REPORT.write_text("\n".join(lines), encoding="utf-8")
    except Exception: pass
    log("поведение: ok %d warn %d bad %d" % (ok, warn, bad))
    return "\n".join(lines)

TOOLS = [{"name": "behavior_run", "desc": "Прогон поведения ИИ: формат, язык, против выдумывания", "params": {}, "approval": False, "fn": lambda **kw: run()}]