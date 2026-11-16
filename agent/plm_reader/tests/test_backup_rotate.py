# -*- coding: utf-8 -*-
"""Регресс-тест V199: ротация ВСЕХ семейств бэкапов (plm_reader_* и pre_*).

Проверяет, что `engine._rotate_backups` удаляет старые pre_repair/pre_compact/pre_normalize/pre_migrate
и plm_reader_*, оставляя ровно `keep` свежих. Работает в %TEMP%, шару не трогает.
"""
import os
import shutil
import sqlite3
import sys
import tempfile

HERE = r"D:\AI\tools\agent\plm_reader"
sys.path.insert(0, HERE)
os.chdir(HERE)
import engine as E          # noqa: E402

tmp = tempfile.mkdtemp(prefix="v199_bk_")
db = os.path.join(tmp, "plm_reader.db")
c = sqlite3.connect(db)
c.execute("CREATE TABLE t(x)")
c.commit()
c.close()
bdir = os.path.join(tmp, "backup")
os.makedirs(bdir)
names = ["plm_reader_a.db", "pre_migrate_a.db", "pre_repair_a.db",
         "pre_compact_a.db", "pre_normalize_a.db"]
for n in names:
    with open(os.path.join(bdir, n), "wb") as f:
        f.write(b"x")

os.environ["PLM_DB"] = db
try:
    removed = E._rotate_backups(keep=2)
    left = sorted(f for f in os.listdir(bdir) if f.endswith(".db"))
finally:
    os.environ.pop("PLM_DB", None)

print("удалено :", removed)
print("осталось:", left)
shutil.rmtree(tmp, ignore_errors=True)

bad = (len(left) != 2) or (removed != 3)
print("")
print("ИТОГ: " + ("ОК — ротация всех семейств работает" if not bad
                  else "ПРОВАЛ: осталось %d, удалено %d" % (len(left), removed)))
sys.exit(1 if bad else 0)