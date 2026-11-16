# -*- coding: utf-8 -*-
"""Регресс-тест V205: авто-обслуживание (normalize→repair→compact) работает на копии базы."""
import os
import shutil
import sqlite3
import sys
import tempfile

HERE = r"D:\AI\tools\agent\plm_reader"
sys.path.insert(0, HERE)
os.chdir(HERE)
import engine as E             # noqa: E402
import plm_database as DB      # noqa: E402

tmp = tempfile.mkdtemp(prefix="v205_auto_")
db = os.path.join(tmp, "plm_reader.db")
con = sqlite3.connect(db)
con.executescript(E.SCHEMA)
con.execute("INSERT INTO snapshots(model,path) VALUES('AA','/a')")
con.execute("INSERT INTO params(path,model,name,type,value) VALUES('/a','aa.XPR','N','str','v')")
con.execute("INSERT INTO links(parent,child,qty,source,origin) VALUES('AA','-00',1,'dwg','real')")
con.execute("INSERT INTO unknown_fields(path,model,name,count) VALUES('/a',?,'__ALL__',1)", ("x" * 2000,))
con.commit()
con.close()

os.environ["PLM_DB"] = db
try:
    r1 = DB.normalize_case(db, dry_run=False, quiet=True)
    r2 = DB.repair(db, dry_run=False, quiet=True)
    r3 = DB.compact_unknown_fields(db, dry_run=False, quiet=True)
finally:
    os.environ.pop("PLM_DB", None)

con = sqlite3.connect(db)
pm = con.execute("SELECT model FROM params").fetchone()
uf = con.execute("SELECT LENGTH(model) FROM unknown_fields").fetchone()[0]
lk = con.execute("SELECT COUNT(*) FROM links").fetchone()[0]
con.close()
shutil.rmtree(tmp, ignore_errors=True)

print("params.model:", pm, "| unknown_fields len:", uf, "| links:", lk)
ok = (pm == ("AA",) and uf <= 600 and lk == 0 and r1 and r2 and r3)
print("")
print("ИТОГ: " + ("ОК — авто-обслуживание работает" if ok else "ПРОВАЛ: %r %r %r" % (r1, r2, r3)))
sys.exit(0 if ok else 1)
