# -*- coding: utf-8 -*-
"""V100-diagnostics: исполнения family table — что в базе, есть ли «призраки»-вхождения."""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engine as eng

con = eng.connect()

# 1) библиотечные стандартные: как лежат base и «исполнение»
print("== примеры семейств ==")
for pat in ("%g6402%", "%o-ring%", "%25-1-g18829%", "%o_ring%"):
    rows = con.execute("SELECT model, folder FROM snapshots WHERE model LIKE ? LIMIT 6",
                       (pat,)).fetchall()
    for m, f in rows:
        print("  %-40s %s" % (m, (f or "")[-60:]))

# 2) вхождения-призраки: child есть в links, файла в snapshots нет
print("== links: child без файла в snapshots (кандидаты в исполнения) ==")
n = con.execute("SELECT COUNT(DISTINCT child) FROM links WHERE child != '' AND child NOT IN "
                "(SELECT model FROM snapshots WHERE model != '')").fetchone()[0]
print("  таких child:", n)
for (c,) in con.execute(
        "SELECT DISTINCT child FROM links WHERE child != '' AND child NOT IN "
        "(SELECT model FROM snapshots WHERE model != '') LIMIT 15"):
    print("  призрак:", c)

# 3) наоборот: base-файлы, которые сами НЕ входят никуда, но из них есть исполнения-кандидаты?
print("== модели, которых НЕТ в links как child (не входят никуда), но они крупные по истории ==")
rows = con.execute(
    "SELECT s.model, COUNT(h.id) c FROM snapshots s JOIN history_rows h ON h.path LIKE '%'||s.model||'%' "
    "WHERE s.model NOT IN (SELECT DISTINCT child FROM links WHERE child != '') "
    "GROUP BY s.model ORDER BY c DESC LIMIT 10").fetchall() if False else []
# упрощённо: просто список «не входит никуда» с числом файлов истории из плм_history-таблиц?
# таблицу истории назовём по факту:
tabs = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("== таблицы базы ==")
print(" ", ", ".join(tabs))

con.close()
