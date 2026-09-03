# -*- coding: utf-8 -*-
import sys, sqlite3, importlib, traceback
from pathlib import Path
AG = Path(r"D:\AI\tools\agent"); sys.path.insert(0, str(AG))
import core
print("core.BASE =", getattr(core, "BASE", "?"))
print("core.DB   =", getattr(core, "DB", "?"))

# 1) навсегда форсируем db() в scanner.py на локальную базу
sp = AG / "scanner.py"; s = sp.read_text(encoding="utf-8")
if "# v14-fix-db" not in s:
    s += '''
# v14-fix-db: БД всегда рядом с этим файлом, независимо от core.BASE
import sqlite3 as _sq
from pathlib import Path as _P
def db():
    return _sq.connect(str(_P(__file__).resolve().parent / "data" / "agent.sqlite"), timeout=10)
'''
    sp.write_text(s, encoding="utf-8")
    print("[+] scanner.py: db() форсирован на data/agent.sqlite")

# 2) перезагружаем и гоним скан синхронно
import scanner; importlib.reload(scanner)
REAL = AG / "data" / "agent.sqlite"
def cnt():
    c = sqlite3.connect(str(REAL), timeout=10)
    n = c.execute("SELECT COUNT(*) FROM models").fetchone()[0]; c.close(); return n
print("models до:", cnt())
try:
    scanner.scan_models()
except Exception:
    print(traceback.format_exc())
print("models после:", cnt())
c = sqlite3.connect(str(REAL), timeout=10)
for (n, e) in c.execute("SELECT name, ext FROM models LIMIT 5").fetchall():
    print("  пример:", n, "[%s]" % e)
c.close()
print("ДАЛЬШЕ: .\\AI_RESTART.bat -> index_run -> usage_build full=1")