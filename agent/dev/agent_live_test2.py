# -*- coding: utf-8 -*-
r"""ЖИВОЙ ТЕСТ АГЕНТА, часть 2: поиск детали и сборки (по просьбе хозяина 24.09.2026).
Предел генерации теперь конечный (см. loop._npred) — зацикливание невозможно."""
import sys, os, time
sys.path.insert(0, r"D:\AI\tools\agent")
os.chdir(r"D:\AI\tools\agent")
import loop

OUT = r"D:\AI\log\urn\cline\live\agent_live_test2.txt"   # урна: вывод пробы — не отчёт (правило дома 24.09.2026)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
QUESTIONS = [
    "найди деталь расв_002_8654_040_001 — что это за деталь и есть ли она у нас? посмотри её массу, если получится",
    "найди сборку 1040-954-35 и скажи, что в неё входит",
]
res = []
res.append("предел генерации (num_predict) = %d токенов" % loop._npred())
for n, q in enumerate(QUESTIONS, 1):
    t0 = time.time()
    try:
        r = loop.ask(q, "server")
        dt = time.time() - t0
        ans = r.get("answer") or ""
        res.append("=" * 70)
        res.append("ВОПРОС %d: %s" % (n, q))
        res.append("время: %.1f с | шагов: %s | обрезано лимитом: %s" % (dt, r.get("steps"), r.get("cut")))
        res.append("МЫСЛИ: служебный %d знаков, русский блок %d знаков" % (len(r.get("think") or ""), len(r.get("think_block") or "")))
        res.append("ОТВЕТ (%d знаков): %s" % (len(ans), ans[:1500]))
        res.append("ЖУРНАЛ: " + " · ".join((r.get("log") or [])[-4:])[:400])
    except Exception:
        import traceback
        res.append("=" * 70)
        res.append("ВОПРОС %d: %s" % (n, q))
        res.append("ОШИБКА:\n" + traceback.format_exc())
    res.append("")
    open(OUT, "w", encoding="utf-8").write("\n".join(res))
print("готово")
