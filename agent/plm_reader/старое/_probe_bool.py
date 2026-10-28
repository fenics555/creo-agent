# -*- coding: utf-8 -*-
"""ИЗУЧЕНИЕ БУЛЕВЫХ ОПЕРАЦИЙ И ЗЕРКАЛ в дереве построения Creo.

Владелец: «Булевы операции находятся в дереве построения в каждом файле! Наверно просто
еще не изучены. В модельной оснастке там можно это отследить, таких связей там много.»

Ищем МАРКЕРЫ булевых операций и зеркал в байтах файлов. Только ЧТЕНИЕ.
"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOTS = [
    r"Z:\PTC\Work\000_03 401-LIT Литейное производство\000_5 401-LIT-MO "
    r"Модельная оснастка для литья\171meta держатель форм",
    r"Z:\PTC\Work\000_03 401-LIT Литейное производство\000_5 401-LIT-MO "
    r"Модельная оснастка для литья\170meta Держатель форм",
]

# Кандидаты в МАРКЕРЫ булевых операций (по опыту Creo и имени операций в дереве модели).
# PT_/Pro* — внутренние префиксы, Merge/Intersect/Subtract — имена операций,
# Cut/Union/Pattern/Mirror — операции дерева. `BASIC_MERGE`, `SHELL` и т.п.
MARKS = {
    "Merge": b"Merge",
    "MERGE": b"MERGE",
    "Intersect": b"Intersect",
    "INTERSECT": b"INTERSECT",
    "Subtract": b"Subtract",
    "SUBTRACT": b"SUBTRACT",
    "Union": b"Union",
    "Cut": b"Cut",
    "Solidify": b"Solidify",
    "Mirror": b"Mirror",
    "MIRROR": b"MIRROR",
    "ZERKALO": b"ZERKALO",
    "Copy_Geom": b"CopyGeom",
    "CopyGeom": b"CopyGeom",
    "Inherit": b"Inherit",
    "INHERIT": b"INHERIT",
    "Feature_id": b"feature_id",
    "FEAT_": b"FEAT_",
    "PT_MERGE": b"PT_MERGE",
    "ProMerge": b"ProMerge",
    "ProSolid": b"ProSolid",
    "Extrude": b"Extrude",
    "Revolve": b"Revolve",
    "Hole": b"Hole",
    "Round": b"Round",
    "Draft": b"Draft",
    "Base_Part": b"Base_Part",
    "BASE_PART": b"BASE_PART",
    "Generic": b"Generic",
    "GENERIC": b"GENERIC",
    "Shrinkage": b"Shrinkage",
    "U_sadka": "Усадка".encode("utf-8"),
    "U_sadka_cp1251": "Усадка".encode("cp1251"),
}


def s(x):
    return str(x or "").encode("ascii", "replace").decode()


def walk(root, limit=None):
    if not os.path.isdir(root):
        return []
    out = []
    for dp, _d, fs in os.walk(root, onerror=lambda e: None):
        for f in fs:
            if re.search(r"\.(prt|asm|drw)\.\d+$", f, re.I):
                out.append(os.path.join(dp, f))
                if limit and len(out) >= limit:
                    return out
    return out


allf = []
for r in ROOTS:
    fs = walk(r)
    print("%-20s моделей: %d" % (s(os.path.basename(r))[:20], len(fs)))
    allf += fs

print("\nВСЕГО моделей для разбора: %d" % len(allf))

# 1) какие маркеры вообще встречаются
cnt = {k: 0 for k in MARKS}
files_with_merge = []
for f in allf:
    try:
        raw = open(f, "rb").read()
    except Exception:
        continue
    for k, pat in MARKS.items():
        if pat in raw:
            cnt[k] += 1
    if any(p in raw for p in (b"Merge", b"MERGE", b"Intersect", b"Subtract", b"Union")):
        files_with_merge.append(os.path.basename(f))

print("\n=== МАРКЕРЫ БУЛЕВЫХ ОПЕРАЦИЙ / НАСЛЕДОВАНИЯ / ЗЕРКАЛ ===")
print("%-20s %s" % ("МАРКЕР", "ФАЙЛОВ"))
for k in sorted(MARKS, key=lambda x: -cnt[x]):
    mark = "✅" if cnt[k] else "❌"
    print("%-20s %4d %s" % (k, cnt[k], mark))

print("\n=== ФАЙЛЫ С БУЛЕВЫМИ ОПЕРАЦИЯМИ (первые 20) ===")
for f in files_with_merge[:20]:
    print("   %s" % s(f))
print("   всего таких файлов: %d" % len(files_with_merge))

# 2) КОНТЕКСТ вокруг Merge/Intersect — что за операция
print("\n=== КОНТЕКСТ ВОКРУГ 'Merge'/'Intersect' (что рядом в байтах) ===")
shown = 0
for f in allf:
    if shown >= 6:
        break
    try:
        raw = open(f, "rb").read()
    except Exception:
        continue
    for pat in (b"Merge", b"Intersect", b"Subtract", b"Union"):
        i = raw.find(pat)
        if i < 0:
            continue
        ctx = raw[max(0, i - 60):i + 90]
        txt = re.sub(rb"[^\x20-\x7e\xc0-\xff]", b".", ctx).decode("cp1251", "replace")
        print("  %-34s |%s|" % (s(os.path.basename(f))[:34], s(txt)))
        shown += 1
        break

# 3) КОНТЕКСТ вокруг Base_Part / Generic (наследование от мастера)
print("\n=== КОНТЕКСТ ВОКРУГ 'Base_Part'/'Generic' (наследование) ===")
shown = 0
for f in allf:
    if shown >= 6:
        break
    try:
        raw = open(f, "rb").read()
    except Exception:
        continue
    for pat in (b"Base_Part", b"BASE_PART", b"Generic", b"GENERIC"):
        i = raw.find(pat)
        if i < 0:
            continue
        ctx = raw[max(0, i - 60):i + 90]
        txt = re.sub(rb"[^\x20-\x7e\xc0-\xff]", b".", ctx).decode("cp1251", "replace")
        print("  %-34s |%s|" % (s(os.path.basename(f))[:34], s(txt)))
        shown += 1
        break

print("\nPROBE OK")
