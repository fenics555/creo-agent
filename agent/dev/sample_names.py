# -*- coding: utf-8 -*-
"""Реальные имена деталей и сборок из индекса дома — для живого теста агента."""
import sqlite3, traceback
from pathlib import Path

OUT = Path(r"D:\AI\log\reports\sample_names.txt")
try:
    c = sqlite3.connect(r"D:\AI\tools\agent\data\harvest.db")
    cols = [r[1] for r in c.execute("PRAGMA table_info(models_raw)")]
    out = ["колонки models_raw: " + ", ".join(cols)]
    for label, pat in (("ДЕТАЛИ (.prt.1)", "%.prt.1"), ("СБОРКИ (.asm.1)", "%.asm.1")):
        out.append("\n" + label + ":")
        try:
            rows = c.execute("SELECT path FROM models_raw WHERE path LIKE ? ORDER BY mtime DESC LIMIT 6", (pat,)).fetchall()
        except Exception as e:
            rows = []
            out.append("  ошибка: %s" % e)
        for (p,) in rows:
            out.append("  " + p)
    c.close()
except Exception:
    out = ["ОШИБКА:\n" + traceback.format_exc()]
OUT.write_text("\n".join(out), encoding="utf-8")
print("ok")
