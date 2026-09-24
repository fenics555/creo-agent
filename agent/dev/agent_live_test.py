# -*- coding: utf-8 -*-
r"""ЖИВОЙ ТЕСТ АГЕНТА (по просьбе хозяина 24.09.2026): базовые вопросы, скиллы, поиск детали/сборки.
Идёт через настоящий конвейер loop.ask (тот же путь, что в окне). Пишет результат после каждого вопроса."""
import sys, os, time
sys.path.insert(0, r"D:\AI\tools\agent")
os.chdir(r"D:\AI\tools\agent")
import loop

OUT = r"D:\AI\PROBA\agent_live_test.txt"
QUESTIONS = [
    "как дела? что ты умеешь?",
    "какие у тебя есть скилы по Creo? какие скилы по CREOSON? перечисли коротко, по-русски",
    "чем ты можешь помочь инженеру-конструктору в нашей работе?",
    "найди деталь расв_002_8654_040_001 — что это и есть ли она у нас?",
    "найди сборку 1040-954-35 и скажи, что в неё входит",
]
res = []
for n, q in enumerate(QUESTIONS, 1):
    t0 = time.time()
    try:
        r = loop.ask(q, "server")
        dt = time.time() - t0
        ans = r.get("answer") or ""
        th = (r.get("think") or "") + " || " + (r.get("think_block") or "")
        res.append("=" * 70)
        res.append("ВОПРОС %d: %s" % (n, q))
        res.append("время: %.1f с | шагов: %s | обрезано лимитом: %s" % (dt, r.get("steps"), r.get("cut")))
        res.append("МЫСЛИ (%d и %d знаков): %s" % (len(r.get("think") or ""), len(r.get("think_block") or ""),
                                                   th[:400].replace("\n", " | ")))
        res.append("ОТВЕТ (%d знаков): %s" % (len(ans), ans[:1200]))
        res.append("ЖУРНАЛ: " + " · ".join((r.get("log") or [])[-3:])[:300])
    except Exception:
        import traceback
        res.append("=" * 70)
        res.append("ВОПРОС %d: %s" % (n, q))
        res.append("ОШИБКА:\n" + traceback.format_exc())
    res.append("")
    open(OUT, "w", encoding="utf-8").write("\n".join(res))
print("готово")
