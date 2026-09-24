# -*- coding: utf-8 -*-
"""Что есть по имени insert-nalojeniya-bdf-1 в базе дома (деталей, чертежей, PDF)."""
import sqlite3, traceback
from pathlib import Path

OUT = Path(r"D:\AI\log\reports\nalojeniya_lookup.txt")
out = []
try:
    for db, table in ((r"D:\AI\tools\agent\data\harvest.db", "models_raw"),
                      (r"D:\AI\tools\agent\data\agent.sqlite", "files")):
        try:
            c = sqlite3.connect(db, timeout=20)
            cols = [r[1] for r in c.execute("PRAGMA table_info(%s)" % table)]
            if not cols:
                out.append("=== %s: таблицы %s нет ===" % (db, table))
                c.close()
                continue
            out.append("=== %s / %s (колонки: %s) ===" % (db, table, ",".join(cols)))
            if "path" in cols:
                rows = c.execute("SELECT path, mtime FROM %s WHERE lower(path) LIKE '%%insert-nalojeniya-bdf-1%%'" % table).fetchall()
            else:
                rows = []
            for p, m in rows[:20]:
                out.append("  %s   (mtime %s)" % (p, m))
            out.append("  всего строк: %d" % len(rows))
            c.close()
        except Exception as e:
            out.append("=== %s: ошибка %s" % (db, e))
except Exception:
    out.append("ОШИБКА:\n" + traceback.format_exc())
OUT.write_text("\n".join(out), encoding="utf-8")
print("ok")
