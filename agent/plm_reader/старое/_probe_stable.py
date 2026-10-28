# -*- coding: utf-8 -*-
"""РАЗБОР НЕСТАБИЛЬНОСТИ СКАНА: сравнить базы между собой. Только чтение."""
import glob
import os
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

D = "Z:/PTC/CREO-START/plm_reader/db"
FS = sorted(glob.glob(D + "/plm_reader_2026*.db"))


def s(x):
    return str(x or "").encode("ascii", "replace").decode()


def con(f):
    return sqlite3.connect("file:" + f + "?mode=ro", uri=True)


print("=== A. ЧЕМ ОТЛИЧАЮТСЯ СКАНЫ: по источникам ===")
for f in FS:
    c = con(f)
    src = dict(c.execute("SELECT source, COUNT(*) FROM links GROUP BY source"))
    print("  %-32s %s" % (os.path.basename(f)[12:26], {s(k): v for k, v in src.items()}))
    c.close()

print("\n=== B. ГЛАВНОЕ: сколько СБОРОК получили состав ===")
for f in FS:
    c = con(f)
    n_par = c.execute("SELECT COUNT(DISTINCT parent) FROM links WHERE source='asm_comp'").fetchone()[0]
    n_asm = c.execute("SELECT COUNT(DISTINCT model) FROM snapshots WHERE lower(path) LIKE "
                      "'%.asm.%'").fetchone()[0]
    print("  %-32s сборок %5d · с составом %5d · БЕЗ %5d (%.0f%%)"
          % (os.path.basename(f)[12:26], n_asm, n_par, n_asm - n_par,
             100.0 * (n_asm - n_par) / max(n_asm, 1)))
    c.close()

print("\n=== C. СБОРКА 23-171GR1-META во ВСЕХ базах ===")
M = "23-171GR1-META"
for f in FS:
    c = con(f)
    n = c.execute("SELECT COUNT(*) FROM links WHERE parent=?", (M,)).fetchone()[0]
    srcs = [s(r[0]) for r in c.execute("SELECT DISTINCT source FROM links WHERE parent=?", (M,))]
    print("  %-32s рёбер %3d  источники=%s" % (os.path.basename(f)[12:26], n, srcs))
    c.close()

print("\n=== D. DIN912 во ВСЕХ базах ===")
for f in FS:
    c = con(f)
    up = c.execute("SELECT COUNT(*) FROM links WHERE child=?", ("DIN912",)).fetchone()[0]
    inst = c.execute("SELECT COUNT(*) FROM links WHERE parent=? AND source='family'",
                     ("DIN912",)).fetchone()[0]
    print("  %-32s входит %2d · исполнений %5d" % (os.path.basename(f)[12:26], up, inst))
    c.close()

print("\n=== E. ЧЕГО НЕ ХВАТАЕТ в базе 08:34 (35 288) против 08:42 (40 456) ===")
a, b = None, None
for f in FS:
    if "083435" in f:
        a = f
    if "084229" in f:
        b = f
if a and b:
    ca, cb = con(a), con(b)
    # сравним по моделям-родителям
    pa = {(s(r[0]), s(r[1]), s(r[2])) for r in
          ca.execute("SELECT parent,child,source FROM links")}
    pb = {(s(r[0]), s(r[1]), s(r[2])) for r in
          cb.execute("SELECT parent,child,source FROM links")}
    only_a = pa - pb
    only_b = pb - pa
    print("  пар только в 08:34: %d" % len(only_a))
    print("  пар только в 08:42: %d" % len(only_b))
    from collections import Counter
    print("  в 08:42 ЛИШНИЕ по источнику: %s" % Counter(x[2] for x in only_b))
    print("  в 08:34 ЛИШНИЕ по источнику: %s" % Counter(x[2] for x in only_a))
    print("  примеры лишних в 08:42:")
    for x in list(only_b)[:10]:
        print("     %s -> %s (%s)" % (x[0][:30], x[1][:30], x[2]))
    ca.close()
    cb.close()

print("\nPROBE OK")
