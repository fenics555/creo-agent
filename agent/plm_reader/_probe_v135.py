# -*- coding: utf-8 -*-
"""ПРОБНИК V135: тип файла в `family`/`asm_comp` + проверка правки family_of/asm_components.

Только ЧТЕНИЕ базы и файлов склада. Ничего не пишет ни в базу, ни на шару.
"""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import sqlite3

import engine as E

p = E.active_db()
print("active base =", p)
con = sqlite3.connect("file:" + p.replace("\\", "/") + "?mode=ro", uri=True)

KIND_SQL = ("CASE WHEN s.path LIKE '%.asm.%' THEN 'ASM' WHEN s.path LIKE '%.drw.%' THEN 'DRW' "
            "WHEN s.path LIKE '%.prt.%' THEN 'PRT' ELSE '???' END")


def by_kind(source):
    q = ("SELECT " + KIND_SQL + " k, COUNT(*) FROM links l LEFT JOIN snapshots s ON s.model=l.parent "
         "WHERE l.source=? GROUP BY k ORDER BY 2 DESC")
    return list(con.execute(q, (source,)))


print("\n--- family по типу файла-генерика ---")
for k, n in by_kind("family"):
    print("  %-5s %7d" % (k, n))
print("--- asm_comp по типу файла-родителя ---")
for k, n in by_kind("asm_comp"):
    print("  %-5s %7d" % (k, n))
print("--- plm_tree по типу файла-родителя ---")
for k, n in by_kind("plm_tree"):
    print("  %-5s %7d" % (k, n))
con.close()


def safe(s):
    return str(s).encode("ascii", "replace").decode()


# --- 2. ПРАВКА НА ЖИВОМ ФАЙЛЕ: family_of / asm_components с проверкой типа ---
import inspect

print("\n--- сигнатуры функций (должны принимать path) ---")
for fn in (E.family_of, E.asm_components):
    print("  %s%s" % (fn.__name__, safe(inspect.signature(fn))))

# ищем на складе живой din912.prt.1 и любой чертёж/сборку с тем же стемом
roots = ["Z:\\PTC\\CREO-START\\Libraries", "Z:\\PTC\\Work"]
found = {}

# 2а) пути берём ИЗ БАЗЫ (там те же файлы, что сканируются) — быстрее и точнее обхода склада
con = sqlite3.connect("file:" + p.replace("\\", "/") + "?mode=ro", uri=True)
rows = list(con.execute("SELECT path FROM snapshots WHERE lower(path) LIKE '%.asm.%' LIMIT 40"))
rows += list(con.execute("SELECT path FROM snapshots WHERE lower(path) LIKE '%.drw.%' LIMIT 40"))
for (pp,) in rows:
    low = os.path.basename(pp or "").lower()
    if low.endswith(".asm") or ".asm." in low:
        found.setdefault("asm", pp)
    elif low.endswith(".drw") or ".drw." in low:
        found.setdefault("drw", pp)
    if "asm" in found and "drw" in found:
        break
con.close()

# 2б) деталь-генерик DIN912 — обходом (в базе она внутри библиотеки, путь длинный)
if not found.get("prt"):
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            for f in filenames:
                if f.lower().startswith("din912.prt"):
                    found["prt"] = os.path.join(dirpath, f)
                    break
            if found.get("prt"):
                break
        if found.get("prt"):
            break

print("\n--- живые файлы ---")
for k in ("prt", "asm", "drw"):
    print("  %s: %s" % (k, safe(found.get(k, "НЕ НАЙДЕН"))))

if found.get("prt"):
    raw = open(found["prt"], "rb").read()
    fam = E.family_of(raw, "DIN912", found["prt"])
    print("  family_of(DIN912, .prt) = %d исполнений" % len(fam))
    parts = E.asm_components(raw, "DIN912")
    print("  asm_components(DIN912, .prt) = %d (ожидаем 0: деталь не содержит компонентов)" % len(parts))
if found.get("drw"):
    raw = open(found["drw"], "rb").read()
    fam = E.family_of(raw, "DIN912", found["drw"])
    print("  family_of(DIN912, .drw) = %d (ожидаем 0: у чертежа нет таблицы семейства)" % len(fam))
    parts = E.asm_components(raw, "DIN912", path=found["drw"])
    print("  asm_components(DIN912, .drw) = %d (ожидаем 0: чертёж не содержит компонентов)" % len(parts))
if found.get("asm"):
    raw = open(found["asm"], "rb").read()
    fam = E.family_of(raw, "DIN912", found["asm"])
    print("  family_of(DIN912, .asm) = %d (ожидаем 0)" % len(fam))
    parts = E.asm_components(raw, "DIN912", path=found["asm"])
    print("  asm_components(DIN912, .asm) = %d (ожидаем >0 либо 0, если деталей нет)" % len(parts))

# --- 3. ГЛАВНАЯ ПРОВЕРКА: настоящая сборка НЕ должна потерять состав ---
con = sqlite3.connect("file:" + p.replace("\\", "/") + "?mode=ro", uri=True)
row = con.execute("SELECT parent, COUNT(*) c FROM links WHERE source='asm_comp' "
                  "GROUP BY parent ORDER BY c DESC LIMIT 5").fetchall()
print("\n--- топ-5 сборок по составу (из базы) ---")
asm_probe = None
for par, cnt in row:
    pp = con.execute("SELECT path FROM snapshots WHERE model=? AND (lower(path) LIKE '%.asm.%') "
                     "LIMIT 1", (par,)).fetchone()
    print("  %s: %d детей%s" % (safe(par), cnt, "" if pp else "  (файла .asm нет в базе)"))
    if pp and not asm_probe:
        asm_probe = (par, pp[0], cnt)
con.close()

if asm_probe:
    par, pp, cnt = asm_probe
    raw = open(pp, "rb").read()
    parts = E.asm_components(raw, par, path=pp)
    print("\nЖИВАЯ СБОРКА %s" % safe(par))
    print("  в базе детей: %d · разобрано сейчас: %d  (0 = состав бы ПОТЕРЯЛСЯ)" % (cnt, len(parts)))
    for ch, role, q in parts[:8]:
        print("    %-28s %-10s x%d" % (safe(ch), safe(role), q))
    assert parts, "СБОРКА ПОТЕРЯЛА СОСТАВ — проверка типа слишком широкая"
    print("  СОСТАВ СБОРКИ ЦЕЛ ✓")

print("\nPARSER_TAG =", E.PARSER_TAG, "· VERSION =", E.VERSION)

# --- 4. HEALTH: таблица должна создаваться в connect() (была грабля «no such table: health») ---
import tempfile

tmp = tempfile.mkdtemp(prefix="plm_v135_")
tpath = os.path.join(tmp, "fresh.db")
c = E.connect(db=tpath)
names = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
print("\n--- свежая база: таблицы ---")
print("  ", ", ".join(names))
assert "health" in names, "health НЕ создаётся в connect() — грабля не закрыта"
print("  health в SCHEMA ✓")
c.close()
try:
    os.remove(tpath)
    os.rmdir(tmp)
except Exception:
    pass

print("PROBE OK")
