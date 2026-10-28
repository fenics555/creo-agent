# -*- coding: utf-8 -*-
"""ЗАМЕР ПОЛНОТЫ СКАНА против документа владельца (Full Creo Dependency Graph).

Проверяем по КАЖДОМУ типу данных из документа, читает ли их код и есть ли в базе.
Только ЧТЕНИЕ файлов и базы. Боевую базу НЕ пишем.
"""
import os
import re
import sqlite3
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import engine as E

PAIRS = [
    ("ПАПКА 1 (сборка)", r"Z:\PTC\Work\000_51 DF Держатели форм"
                         r"\23-171GR1-META 2кап черновой BDF 5 1_2''"),
    ("ПАПКА 2 (производные)", r"Z:\PTC\Work\000_03 401-LIT Литейное производство"
                              r"\000_5 401-LIT-MO Модельная оснастка для литья\171meta держатель форм"),
]

# Секции/признаки ИЗ ДОКУМЕНТА ВЛАДЕЛЬЦА:
# ГРАФ 1 (вниз): NeuAsmSld, SolidPersistTable, BasBasData
# ГРАФ 2 (вверх): FeatDefs, LargeText, Base_Part, Merge, Shrinkage; feat_id/Inheritance
DOC_MARKS = {
    "NeuAsmSld": b"NeuAsmSld",
    "SolidPersistTable": b"SolidPersistTable",
    "BasBasData": b"BasBasData",
    "FeatDefs": b"FeatDefs",
    "LargeText": b"LargeText",
    "Base_Part": b"Base_Part",
    "Merge": b"Merge",
    "Shrinkage": b"Shrinkage",
    "Inheritance": b"Inheritance",
    "feat_id": b"feat_id",
    "copy_from(from_mdl_name)": b"from_mdl_name",
    "derived(proizv/nasled)": b"proizv",
}


def s(x):
    return str(x or "").encode("ascii", "replace").decode()


def model_files(root):
    out = []
    for dp, _d, fs in os.walk(root):
        for f in fs:
            if re.search(r"\.(prt|asm|drw)\.\d+$", f, re.I) or \
               re.search(r"\.(prt|asm|drw)$", f, re.I):
                out.append(os.path.join(dp, f))
    return out


print("=" * 70)
print("ЗАМЕР: ЧИТАЕТ ЛИ СКАН ДАННЫЕ ИЗ ДОКУМЕНТА (Full Creo Dependency Graph)")
print("=" * 70)

all_files = []
for name, root in PAIRS:
    fs = model_files(root) if os.path.isdir(root) else []
    all_files += fs
    print("\n%s: %d моделей" % (name, len(fs)))
    for f in sorted(fs):
        print("   %s" % s(os.path.basename(f)))

print("\n" + "=" * 70)
print("ПРИСУТСТВИЕ СЕКЦИЙ В ФАЙЛАХ (по документу)")
print("=" * 70)
hits = {k: [] for k in DOC_MARKS}
for f in all_files:
    try:
        raw = open(f, "rb").read()
    except Exception:
        continue
    for k, pat in DOC_MARKS.items():
        if pat in raw:
            hits[k].append(os.path.basename(f))
print("%-26s %s" % ("СЕКЦИЯ/ПРИЗНАК", "НАЙДЕНО В N МОДЕЛЯХ"))
for k in DOC_MARKS:
    lst = hits[k]
    print("%-26s %3d %s" % (k, len(lst), ("(напр. %s)" % s(lst[0])) if lst else "❌ НЕ НАЙДЕНО"))

print("\n" + "=" * 70)
print("ЧТО СКАН РЕАЛЬНО ИЗВЛЕКАЕТ ИЗ ЭТИХ ФАЙЛОВ (живой разбор)")
print("=" * 70)
stems = set()
for f in all_files:
    stems.add(E.stem(os.path.basename(f)).lower())

tot_down, tot_up, tot_fam = 0, 0, 0
for f in sorted(all_files):
    if not f.lower().endswith(".1"):
        continue
    base = os.path.basename(f)
    if ".asm." not in f.lower() and ".prt." not in f.lower():
        continue
    try:
        raw = open(f, "rb").read()
    except Exception:
        continue
    st = E.stem(base)
    down = E.asm_components(raw, st, stems, path=f)
    up = E.derived_of(raw)
    fam = E.family_of(raw, st, path=f)
    cf = E.copy_from_of(raw) if hasattr(E, "copy_from_of") else ""
    tot_down += len(down)
    if up and up[0]:
        tot_up += 1
    tot_fam += len(fam)
    flags = []
    if down:
        flags.append("ВНИЗ %d" % len(down))
    if up and up[0]:
        flags.append("ВВЕРХ→%s(%s)" % (s(up[0]), s(up[1])))
    if cf:
        flags.append("КОПИЯ←%s" % s(cf))
    if fam:
        flags.append("ИСПОЛН %d" % len(fam))
    if flags:
        print("  %-46s %s" % (s(base)[:46], " · ".join(flags)))

print("\nИТОГО по полигону: связей ВНИЗ %d · моделей с ВВЕРХ %d · исполнений %d"
      % (tot_down, tot_up, tot_fam))

print("\n" + "=" * 70)
print("ЧТО ИЗ ЭТОГО ДОШЛО ДО БАЗЫ (активная база)")
print("=" * 70)
p = E.active_db()
c = sqlite3.connect("file:" + p.replace("\\", "/") + "?mode=ro", uri=True)
names = [E.stem(os.path.basename(f)) for f in all_files]
in_snap = 0
in_links = 0
in_der = 0
for m in names:
    if c.execute("SELECT 1 FROM snapshots WHERE model=? LIMIT 1", (m,)).fetchone():
        in_snap += 1
    if c.execute("SELECT 1 FROM links WHERE parent=? OR child=? LIMIT 1", (m, m)).fetchone():
        in_links += 1
    if c.execute("SELECT 1 FROM derived WHERE child=? OR base=? LIMIT 1", (m, m)).fetchone():
        in_der += 1
print("моделей полигона: %d" % len(set(names)))
print("   есть в snapshots : %d" % in_snap)
print("   есть в links    : %d" % in_links)
print("   есть в derived  : %d" % in_der)
print("\nПО ИСТОЧНИКАМ в базе:")
for r in c.execute("SELECT source, COUNT(*) FROM links GROUP BY source"):
    print("   %-12s %d" % (s(r[0]), r[1]))
c.close()
print("\nPROBE OK")
