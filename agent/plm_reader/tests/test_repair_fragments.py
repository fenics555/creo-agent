# -*- coding: utf-8 -*-
"""Регресс-тест V202: repair снимает само-связи, дубли И строки-обрывки/пустые ключи."""
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

tmp = tempfile.mkdtemp(prefix="v202_rep_")
db = os.path.join(tmp, "plm_reader.db")
con = sqlite3.connect(db)
con.executescript(E.SCHEMA)
con.executemany("INSERT INTO links(parent,child,qty,source,origin) VALUES(?,?,?,?,?)",
                [("AA", "-00", 1, "dwg", "real"),        # обрывок -> снять
                 ("AA", "AA", 1, "dwg", "real"),         # само-связь -> снять
                 ("AA", "BB", 1, "asm_comp", "real"),    # норма
                 ("AA", "BB", 1, "asm_comp", "real"),    # дубль -> снять
                 ("", "CC", 1, "asm_comp", "real")])     # пустой ключ -> снять
con.commit()
con.close()

DB.repair(db, dry_run=False, quiet=True)

con = sqlite3.connect(db)
rows = sorted(con.execute("SELECT parent, child FROM links").fetchall())
con.close()
shutil.rmtree(tmp, ignore_errors=True)

print("осталось строк links:", rows)
ok = (rows == [("AA", "BB")])
print("")
print("ИТОГ: " + ("ОК — обрывки/пустые/дубли сняты" if ok else "ПРОВАЛ: %r" % rows))
sys.exit(0 if ok else 1)
