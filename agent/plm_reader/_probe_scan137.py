# -*- coding: utf-8 -*-
"""КОНТРОЛЬНЫЙ ПРОГОН V137: скан 3 папок в ОТДЕЛЬНУЮ базу (боевую НЕ трогаем!).

Проверяем весь конвейер: файлы → scan_item → do_scan → база.
Печатаем: сколько связей наследования, кто родители, есть ли мусор, есть ли «сам на себя».
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

FOLDERS = [
    r"Z:\PTC\Work\000_03 401-LIT Литейное производство\000_5 401-LIT-MO "
    r"Модельная оснастка для литья\171meta держатель форм",
    r"Z:\PTC\Work\000_03 401-LIT Литейное производство\000_5 401-LIT-MO "
    r"Модельная оснастка для литья\170meta Держатель форм",
    r"Z:\PTC\Work\000_51 DF Держатели форм\23-171GR1-META 2кап черновой BDF 5 1_2''",
]

tmp = tempfile.mkdtemp(prefix="plm_v137_")
db = os.path.join(tmp, "test137.db")
print("ТЕСТОВАЯ БАЗА (боевая НЕ тронута): %s\n" % db)

res = E.do_scan(FOLDERS, 24, 0, None, None, None, True, db=db)
print("do_scan:", {k: v for k, v in res.items() if k != "files"})

c = sqlite3.connect(db)


def s(x):
    return str(x or "").encode("ascii", "replace").decode()


print("\n=== snapshots: %d ===" % c.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0])
print("=== links: %d ===" % c.execute("SELECT COUNT(*) FROM links").fetchone()[0])
print("=== derived: %d ===" % c.execute("SELECT COUNT(*) FROM derived").fetchone()[0])

print("\n--- derived ПО ВИДАМ ---")
for r in c.execute("SELECT kind, COUNT(*) FROM derived GROUP BY kind ORDER BY 2 DESC"):
    print("   %-16s %d" % (s(r[0]), r[1]))

print("\n--- ИСТОЧНИКИ derived ---")
for r in c.execute("SELECT source, COUNT(*) FROM derived GROUP BY source ORDER BY 2 DESC"):
    print("   %-16s %d" % (s(r[0]), r[1]))

print("\n--- САМ НА СЕБЯ (должно быть 0) ---")
n = c.execute("SELECT COUNT(*) FROM derived WHERE lower(child)=lower(base)").fetchone()[0]
print("   %d %s" % (n, "✅" if n == 0 else "🔴"))

print("\n--- МУСОР в base (PTC_*, MM_*, object_type) ---")
n = c.execute("SELECT COUNT(*) FROM derived WHERE upper(base) LIKE 'PTC[_]%' "
              "OR upper(base) LIKE 'MM[_]%' OR upper(base) LIKE 'SBORKA[_]%' "
              "OR lower(base) LIKE '%object_type%'").fetchone()[0]
print("   %d %s" % (n, "✅" if n == 0 else "🔴"))

print("\n--- КИРИЛЛИЦА в base (доказательство, что читается) ---")
n = c.execute("SELECT COUNT(*) FROM derived WHERE base GLOB '*[А-Яа-яЁё]*'").fetchone()[0]
print("   записей с русскими буквами: %d" % n)
for r in c.execute("SELECT DISTINCT base FROM derived WHERE base GLOB '*[А-Яа-яЁё]*' LIMIT 8"):
    print("      %s" % s(r[0]))

print("\n--- ТОП: у кого больше всего родителей ---")
for r in c.execute("SELECT child, COUNT(*) c FROM derived GROUP BY child "
                   "HAVING c > 2 ORDER BY c DESC LIMIT 8"):
    print("   %-42s %d родителей" % (s(r[0])[:42], r[1]))

print("\n--- ТОП-10 связей наследования (child → base) ---")
for r in c.execute("SELECT child, base, kind FROM derived ORDER BY child LIMIT 10"):
    print("   %-38s → %-34s (%s)" % (s(r[0])[:38], s(r[1])[:34], s(r[2])))

c.close()
print("\nPROBE OK · база: %s" % db)
