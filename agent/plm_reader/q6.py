# -*- coding: utf-8 -*-
"""Какие параметры есть в базе и как ищет главное окно."""
import os, sys, sqlite3
sys.path.insert(0, r"D:\AI\tools\agent\plm_reader")
if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
os.environ.setdefault("PLM_DATA_DIR", r"Z:\PTC\CREO-START\plm_reader\db")
import engine
con = sqlite3.connect(engine.active_db()); cur = con.cursor()
print("ТАБЛИЦЫ активной базы:")
for (t,) in cur.execute("SELECT name FROM sqlite_master WHERE type=%s ORDER BY name" % chr(39)+"table"+chr(39)):
    n = cur.execute("SELECT COUNT(*) FROM [%s]" % t).fetchone()[0]
    print("   %-22s %d строк" % (t, n))
print()
print("КОЛОНКИ snapshots:")
for r in cur.execute("PRAGMA table_info(snapshots)"):
    print("   %-14s %s" % (r[1], r[2]))
print()
print("КОЛОНКИ params (если есть):")
for r in cur.execute("PRAGMA table_info(params)"):
    print("   %-14s %s" % (r[1], r[2]))
