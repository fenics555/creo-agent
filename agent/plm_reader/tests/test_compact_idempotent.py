# -*- coding: utf-8 -*-
"""Регресс-тест V208: compact идемпотентен (повтор не находит длинных строк)."""
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

tmp = tempfile.mkdtemp(prefix="v208_uf_")
db = os.path.join(tmp, "plm_reader.db")
con = sqlite3.connect(db)
con.executescript(E.SCHEMA)
con.execute("INSERT INTO unknown_fields(path,model,name,count) VALUES('/a',?,'__ALL__',1)", ("x" * 2000,))
con.commit()
con.close()

os.environ["PLM_DB"] = db
try:
    r1 = DB.compact_unknown_fields(db, dry_run=False, quiet=True)
    r2 = DB.compact_unknown_fields(db, dry_run=False, quiet=True)
finally:
    os.environ.pop("PLM_DB", None)

con = sqlite3.connect(db)
n_long = con.execute("SELECT COUNT(*) FROM unknown_fields WHERE LENGTH(model) > 512").fetchone()[0]
_mark = [r[0] for r in con.execute("SELECT model FROM unknown_fields")]
con.close()
shutil.rmtree(tmp, ignore_errors=True)

print("1-й прогон обрезал:", r1.get("truncated"), "| 2-й прогон обрезал:", r2.get("truncated"))
print("строк >512 после:", n_long, "| хвост:", repr(_mark[0][-18:]))
ok = (r1.get("truncated") == 1 and r2.get("truncated") == 0 and n_long == 0)
print("")
print("ИТОГ: " + ("ОК — compact идемпотентен" if ok else "ПРОВАЛ"))
sys.exit(0 if ok else 1)
