# -*- coding: utf-8 -*-
"""V96-diagnostics: почему «Река» пустая — факты журнала changes."""
import os
import sys
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engine as eng

con = eng.connect()
print("всего changes:", con.execute("SELECT COUNT(*) FROM changes").fetchone()[0])
print("диапазон ts:", con.execute("SELECT MIN(ts), MAX(ts) FROM changes").fetchone())
print("kind:", con.execute("SELECT kind, COUNT(*) FROM changes GROUP BY kind ORDER BY 2 DESC").fetchall())
print("примеры:", con.execute("SELECT ts, item, kind FROM changes ORDER BY id DESC LIMIT 3").fetchall())
rows = con.execute("SELECT ts, item FROM changes").fetchall()
models = {r[0] for r in con.execute("SELECT DISTINCT model FROM snapshots WHERE model != ''")}
con.close()

per = Counter()
bad_ts = bad_stem = miss = 0
for ts, item in rows:
    mon = (ts or "")[:7]
    if len(mon) != 7 or mon[4] != "-":
        bad_ts += 1
        continue
    try:
        m = eng.stem(os.path.basename(item or ""))
    except Exception:
        bad_stem += 1
        continue
    if m in models:
        per[(m, mon)] += 1
    else:
        miss += 1

print("битый формат ts:", bad_ts, "| ошибка stem:", bad_stem, "| модель не в snapshots:", miss)
print("моделей в потоках:", len({m for m, _ in per}))
tot = Counter()
for (m, _mo), c in per.items():
    tot[m] += c
print("топ:", tot.most_common(8))
months = Counter()
for (_m, mo), c in per.items():
    months[mo] += c
print("правок по месяцам:", sorted(months.items()))
