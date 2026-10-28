# -*- coding: utf-8 -*-
"""ТОЧЕЧНЫЙ ТЕСТ: разобрать ОДНУ сборку в ОТДЕЛЬНУЮ тестовую базу (боевую НЕ трогаем).

Вопрос владельца: 'сборка без деталей — как так?' Проверяем весь путь:
scan_item -> do_scan -> запись links. Печатаем, что происходит на каждом шаге.
"""
import os
import sqlite3
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import engine as E


def s(x):
    return str(x or "").encode("ascii", "replace").decode()


M = "23-171GR1-META"
Q = "Z:\\PTC\\Work\\000_51 DF Держатели форм\\23-171GR1-META 2кап черновой BDF 5 1_2''"
P = os.path.join(Q, "23-171gr1-meta.asm.1")

print("=== 1. ФАЙЛ ===")
print("   %s" % s(P))
print("   существует: %s · %.1f МБ" % (os.path.isfile(P), os.path.getsize(P) / 1048576.0))

print("\n=== 2. scan_item: что он ВИДИТ (без записи в базу) ===")
raw = open(P, "rb").read()
codes = E.names(raw)
stems = {c.lower() for c in codes}
it = E.scan_item("23-171gr1-meta", P, stems)
print("   model      : %s" % s(it["model"]))
print("   parts      : %d компонентов" % len(it.get("parts") or []))
for ch, role, q in (it.get("parts") or [])[:10]:
    print("       %-30s %-10s x%d" % (s(ch), s(role), q))
print("   refs       : %d имён" % len(it.get("refs") or {}))
print("   family     : %d" % len(it.get("family") or []))
print("   base/dkind : %s / %s" % (s(it.get("base")), s(it.get("dkind"))))

print("\n=== 3. ЧТО СТЕМЫ: сколько имён склада дошло ===")
print("   stems в файле   : %d" % len(stems))
print("   refs (отсев по stems): %d" % len(it.get("refs") or {}))
missing = [c for c in codes if c.lower() not in stems]
print("   имён вне stems  : %d" % len(missing))

print("\n=== 4. ПОЛНЫЙ do_scan В ТЕСТОВУЮ БАЗУ (боевая не тронута) ===")
tmp = tempfile.mkdtemp(prefix="plm_isolated_")
tdb = os.path.join(tmp, "test.db")
print("   тестовая база: %s" % tdb)
res = E.do_scan([Q], 24, 0, None, None, None, True, db=tdb)
print("   результат do_scan: %s" % {k: v for k, v in res.items() if k != "files"})

c = sqlite3.connect(tdb)
print("\n=== 5. ЧТО ЗАПИСАЛОСЬ В ТЕСТОВУЮ БАЗУ ===")
print("   snapshots: %d" % c.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0])
print("   links    : %d" % c.execute("SELECT COUNT(*) FROM links").fetchone()[0])
tgt = [s(r[0]) for r in c.execute("SELECT DISTINCT parent FROM links")]
print("   родители в links: %s" % tgt[:15])
print("   links этой сборки:")
for r in c.execute("SELECT parent,child,qty,source FROM links WHERE parent LIKE '23-171%'"):
    print("       %s -> %s x%s (%s)" % (s(r[0]), s(r[1]), r[2], s(r[3])))
print("\n=== 6. ЛОГ СКАНА (последние строки) ===")
lg = os.path.join(os.path.dirname(os.path.abspath(E.__file__)), "log")
if os.path.isdir(lg):
    fs = sorted([os.path.join(lg, f) for f in os.listdir(lg)], key=os.path.getmtime)[-1:]
    for f in fs:
        print("   --- %s ---" % os.path.basename(f))
        for line in open(f, encoding="utf-8", errors="replace").read().splitlines()[-12:]:
            print("   %s" % s(line))
c.close()

print("\nPROBE OK (тестовая база: %s)" % tdb)
