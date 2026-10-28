# -*- coding: utf-8 -*-
"""ВСЕ ВАРИАНТЫ НАСЛЕДОВАНИЯ в Creo: ищем маркеры в файлах (не по именам!).

Владелец: «наследований тоже есть несколько вариантов в самом крео: как наследование,
как добавление тела... разница есть». Ищем РАЗНЫЕ маркеры операции, чтобы понять виды.
Связь — ТОЛЬКО по бинарным маркерам, НЕ по именам моделей.
"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = (r"Z:\PTC\Work\000_03 401-LIT Литейное производство\000_5 401-LIT-MO "
        r"Модельная оснастка для литья")
ROOT2 = r"Z:\PTC\Work\000_51 DF Держатели форм"

# Кандидаты маркеров (все регистры) — ищем ИМЕНА ОПЕРАЦИЙ, а не имена моделей
CANDS = [
    b"MERGE_BASE_PART", b"MERGE", b"BASE_PART",
    b"INHERIT", b"Inherit", b"inherit",
    b"COPY_GEOM", b"CopyGeom", b"COPYGEOM",
    b"ADD_BODY", b"ADD_SOLID", b"ADD_GEOM",
    b"FULL_MERGE", b"PARTIAL_MERGE",
    b"MATERIAL_REMOVE", b"REMOVE_MATERIAL",
    b"BOOL", b"BOOLEAN",
    b"UNIFY", b"UNITE",
    b"SHRINK", b"SHRINKAGE",
    b"MERGE_BY", b"MERGE_REF", b"MERGE_TYPE",
    b"ref_type", b"REF_TYPE",
    b"merge_type", b"op_type", b"OP_TYPE",
    b"CUT", b"CUTSOLID", b"SUBTRACT_BODY",
    b"Mirror", b"MIRROR", b"ZERKALO", b"ZERKAL",
    b"relset_code_tree", b"relcode_tree_child",
    b"FeatDefs", b"feat_type", b"FEAT_TYPE", b"feature_type",
]


def s(x):
    return str(x or "").encode("ascii", "replace").decode()


def models(root, limit=400):
    out = []
    if not os.path.isdir(root):
        return out
    for dp, _d, fs in os.walk(root, onerror=lambda e: None):
        for f in fs:
            if re.search(r"\.(prt|asm|drw)\.\d+$", f, re.I):
                out.append(os.path.join(dp, f))
                if len(out) >= limit:
                    return out
    return out


files = models(ROOT) + models(ROOT2, 200)
print("моделей для разбора: %d\n" % len(files))
raws = {}
for f in files:
    try:
        raws[f] = open(f, "rb").read()
    except Exception:
        pass

print("%-24s %6s  %s" % ("МАРКЕР", "ФАЙЛОВ", "ВЕРДИКТ"))
print("-" * 70)
for c in CANDS:
    n = sum(1 for r in raws.values() if c in r)
    if not n:
        continue
    note = ""
    # проверяем на служебное (MECHANICA у Union_userdata)
    if c in (b"BOOL", b"UNIFY", b"UNITE"):
        note = "проверить контекст"
    print("%-24s %6d  %s" % (s(c.decode("ascii", "replace")), n, note))

print("\n" + "=" * 78)
print("КОНТЕКСТ КЛЮЧЕВЫХ МАРКЕРОВ НАСЛЕДОВАНИЯ (что рядом с маркером)")
print("=" * 78)
for key in (b"MERGE_BASE_PART", b"MERGE", b"INHERIT", b"COPY_GEOM", b"ADD_BODY",
            b"ref_type", b"merge_type", b"feature_type"):
    shown = 0
    print("\n--- %s ---" % s(key.decode("ascii", "replace")))
    for f, raw in raws.items():
        if shown >= 3:
            break
        i = raw.find(key)
        if i < 0:
            continue
        if b"MECHANICA" in raw[max(0, i - 80):i + 80]:
            continue
        ctx = raw[max(0, i - 70):i + 130]
        txt = re.sub(rb"[^\x20-\x7e\xc0-\xff\xa8\xb8]", b".", ctx).decode("cp1251", "replace")
        print("  %-36s |%s|" % (s(os.path.basename(f))[:36], s(txt)))
        shown += 1
    if not shown:
        print("   (не найдено вне служебных)")

print("\nPROBE OK")
