# -*- coding: utf-8 -*-
"""ПРОБНИК-РАЗБОР: почему у сборки нет состава в связях/графе. Только чтение."""
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import sqlite3

import engine as E

c = sqlite3.connect("file:" + E.active_db().replace("\\", "/") + "?mode=ro", uri=True)


def s(x):
    return str(x or "").encode("ascii", "replace").decode()


print("=== 1. links по источникам ===")
for r in c.execute("SELECT source, COUNT(*) FROM links GROUP BY source"):
    print("   %-12s %d" % (s(r[0]), r[1]))

print("\n=== 2. СКОЛЬКО СБОРОК ВООБЩЕ ПОЛУЧИЛИ СОСТАВ ===")
n_par = c.execute("SELECT COUNT(DISTINCT parent) FROM links WHERE source='asm_comp'").fetchone()[0]
n_par_tree = c.execute("SELECT COUNT(DISTINCT parent) FROM links WHERE source='plm_tree'").fetchone()[0]
n_asm = c.execute("SELECT COUNT(*) FROM snapshots WHERE lower(path) LIKE '%.asm.%'").fetchone()[0]
n_asm_models = c.execute("SELECT COUNT(DISTINCT model) FROM snapshots WHERE lower(path) LIKE "
                         "'%.asm.%'").fetchone()[0]
print("   .asm файлов в snapshots      : %d (моделей %d)" % (n_asm, n_asm_models))
print("   родителей с asm_comp         : %d" % n_par)
print("   родителей с plm_tree         : %d" % n_par_tree)
print("   >>> БЕЗ СОСТАВА (asm_comp)   : %d моделей сборок" % (n_asm_models - n_par))

print("\n=== 3. СБОРКА ВЛАДЕЛЬЦА 23-171GR1-META ===")
M = "23-171GR1-META"
print("   пути в snapshots:")
for r in c.execute("SELECT path, role FROM snapshots WHERE model=?", (M,)):
    print("     %s  role=%s" % (s(r[0]), s(r[1])))
print("   links где parent :", c.execute("SELECT COUNT(*) FROM links WHERE parent=?", (M,)).fetchone()[0])
print("   links где child  :", c.execute("SELECT COUNT(*) FROM links WHERE child=?", (M,)).fetchone()[0])
print("   derived (child)  :")
for r in c.execute("SELECT base, kind FROM derived WHERE child=?", (M,)):
    print("     <- %s (%s)" % (s(r[0]), s(r[1])))
print("   derived (base)   :")
for r in c.execute("SELECT child, kind FROM derived WHERE base=?", (M,)):
    print("     -> %s (%s)" % (s(r[0]), s(r[1])))

print("\n=== 4. ЧТО ДАЁТ ГРАФ (plm_edges) ДЛЯ ЭТОЙ СБОРКИ ===")
try:
    import plm_graph as G
    ed = G.plm_edges()
    print("   всего рёбер в графе: %d" % len(ed))
    near = [e for e in ed if e["from"] == M or e["to"] == M]
    print("   рёбер вокруг %s: %d" % (M, len(near)))
    for e in near[:20]:
        print("     %-24s --%s/%s--> %s" % (s(e["from"]), s(e["type"]), s(e["channel"]), s(e["to"])))
except Exception as ex:
    print("   plm_edges упал: %s" % ex)

print("\n=== 5. ЖИВОЙ ФАЙЛ: разбирается ли состав сейчас ===")
row = c.execute("SELECT path FROM snapshots WHERE model=? AND lower(path) LIKE '%.asm.%' "
                "LIMIT 1", (M,)).fetchone()
if row:
    import os
    p = row[0]
    print("   файл: %s" % s(p))
    print("   существует: %s" % os.path.isfile(p))
    if os.path.isfile(p):
        raw = open(p, "rb").read()
        print("   размер: %.1f МБ" % (len(raw) / 1048576.0))
        parts = E.asm_components(raw, M, path=p)
        print("   >>> asm_components СЕЙЧАС: %d компонентов" % len(parts))
        for ch, role, q in parts[:12]:
            print("       %-30s %-10s x%d" % (s(ch), s(role), q))
        refs = E.names(raw)
        print("   имён в файле (names): %d" % len(refs))
else:
    print("   .asm файла нет в snapshots — сборка известна только по derived")

print("\nPROBE OK")
