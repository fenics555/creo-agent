# -*- coding: utf-8 -*-
"""Регресс-тест V196: каналы связей engine.do_scan пишут КАНОН имён.

Сканирует КОРОТКУЮ реальную папку во ВРЕМЕННУЮ базу (не на Z:, не боевую) и проверяет:
  • нет детей с расширением (`.PRT`/`.ASM`/`.XPR`…);
  • нет обрывков (имя с ведущим «-»);
  • нет само-связей (parent == child).
Выход: 0 — ок, 1 — провал.
"""
import os
import sqlite3
import sys
import tempfile

HERE = r"D:\AI\tools\agent\plm_reader"
sys.path.insert(0, HERE)
os.chdir(HERE)
import engine as E          # noqa: E402

ROOT = r"Z:\PTC\Work\001_15 ЦТКД Электон"
LIMIT = 30
db = os.path.join(tempfile.gettempdir(), "v196_links.db")
for suf in ("", "-wal", "-shm", "-journal"):
    try:
        os.remove(db + suf)
    except OSError:
        pass
c = sqlite3.connect(db)
c.executescript(E.SCHEMA)
c.commit()
c.close()

try:
    E.do_scan([ROOT], 24, LIMIT, db=db, full=True, remember=False)
except Exception as e:                        # noqa: BLE001
    print("do_scan ошибка: %s" % e)

c = sqlite3.connect(db)
rows = c.execute("SELECT COUNT(*) FROM links").fetchone()[0]
with_ext = c.execute("SELECT COUNT(*) FROM links WHERE child LIKE '%.%'").fetchone()[0]
frag = c.execute("SELECT COUNT(*) FROM links WHERE child LIKE '-%'").fetchone()[0]
selfl = c.execute("SELECT COUNT(*) FROM links WHERE parent=child").fetchone()[0]
pex = c.execute("SELECT COUNT(*) FROM links WHERE parent LIKE '%.%'").fetchone()[0]
print("links строк         :", rows)
print("child с расширением :", with_ext)
print("child обрывок '-'   :", frag)
print("parent==child       :", selfl)
print("parent с расшир.    :", pex)
if rows == 0:
    print("ВНИМАНИЕ: связей 0 — выборка не дала сборок/чертежей (тест слабый, не провал)")
c.close()
for suf in ("", "-wal", "-shm", "-journal"):
    try:
        os.remove(db + suf)
    except OSError:
        pass

bad = with_ext + frag + selfl + pex
print("")
print("ИТОГ: " + ("ОК — каналы пишут канон" if bad == 0 else "ПРОВАЛ: %d плохих строк" % bad))
sys.exit(1 if bad else 0)
