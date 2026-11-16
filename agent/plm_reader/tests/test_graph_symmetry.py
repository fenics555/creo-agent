# -*- coding: utf-8 -*-
"""Регресс-тест V197: СИММЕТРИЯ ГРАФА — любые from/to рёбер есть в graph_nodes.

Строит граф во ВРЕМЕННУЮ базу (не Z:, не боевую) и проверяет, что НЕТ рёбер,
чей конец отсутствует среди узлов. Выход: 0 — ок, 1 — провал.
"""
import os
import sqlite3
import sys
import tempfile

HERE = r"D:\AI\tools\agent\plm_reader"
sys.path.insert(0, HERE)
os.chdir(HERE)
import engine as E                 # noqa: E402
import plm_graph_build as GB       # noqa: E402

db = os.path.join(tempfile.gettempdir(), "v197_graph.db")
for suf in ("", "-wal", "-shm", "-journal"):
    try:
        os.remove(db + suf)
    except OSError:
        pass
c = sqlite3.connect(db)
c.executescript(E.SCHEMA)
c.executemany("INSERT INTO snapshots(model,path) VALUES(?,?)", [("AA-PART", "/a.prt"), ("BB-ASM", "/b.asm")])
c.executemany("INSERT INTO links(parent,child,qty,source,origin) VALUES(?,?,?,?,?)",
              [("BB-ASM", "AA-PART", 1, "asm_comp", "real"),
               ("BB-ASM", "CC-COMP", 1, "asm_comp", "real")])   # CC-COMP нет в snapshots -> должен стать узлом
c.commit()
c.close()

os.environ["PLM_DB"] = db
try:
    GB.build(engine_mod=E)
    c = sqlite3.connect(db)
    nodes = c.execute("SELECT COUNT(*) FROM graph_nodes").fetchone()[0]
    edges = c.execute("SELECT COUNT(*) FROM graph_edges").fetchone()[0]
    orphan = c.execute('SELECT COUNT(*) FROM graph_edges WHERE "from" NOT IN '
                       '(SELECT model FROM graph_nodes) OR "to" NOT IN '
                       '(SELECT model FROM graph_nodes)').fetchone()[0]
    dup = c.execute('SELECT COUNT(*) FROM (SELECT "from","to",kind FROM graph_edges '
                    'GROUP BY "from","to",kind HAVING COUNT(*)>1)').fetchone()[0]
    c.close()
finally:
    os.environ.pop("PLM_DB", None)

print("nodes            :", nodes)
print("edges            :", edges)
print("edges-сироты     :", orphan)
print("edges-дубли гр.  :", dup)

bad = orphan + dup
print("")
print("ИТОГ: " + ("ОК — граф симметричен, без дублей" if bad == 0 else "ПРОВАЛ: %d" % bad))
for suf in ("", "-wal", "-shm", "-journal"):
    try:
        os.remove(db + suf)
    except OSError:
        pass
sys.exit(1 if bad else 0)
