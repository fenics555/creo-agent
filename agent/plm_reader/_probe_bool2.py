# -*- coding: utf-8 -*-
"""ТОЧНЫЙ разбор маркеров булевых операций: контекст вокруг КАЖДОГО маркера.

После первого прогона выяснилось: `Union` — служебное поле MECHANICA (`Union_userdata`),
НЕ булева операция. Значит верить счётчику нельзя — смотрим контекст по каждому маркеру.
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

# Точные маркеры (верхний регистр — как реально лежат в файлах)
EXACT = [
    b"MERGE",
    b"BASE_PART",
    b"Cut",
    b"MSM_MBR_GENERIC_NAME",
    b"MDL_GENERIC",
    b"RELCODE_TREE",
    b"relcode_tree",
]


def s(x):
    return str(x or "").encode("ascii", "replace").decode()


def models(root, limit=400):
    out = []
    for dp, _d, fs in os.walk(root, onerror=lambda e: None):
        for f in fs:
            if re.search(r"\.(prt|asm)\.\d+$", f, re.I):
                out.append(os.path.join(dp, f))
                if len(out) >= limit:
                    return out
    return out


fs = models(ROOT)
print("моделей (.prt/.asm): %d\n" % len(fs))

for mark in EXACT:
    print("=" * 78)
    print("МАРКЕР: %s" % s(mark.decode("ascii", "replace")))
    print("=" * 78)
    n = 0
    for f in fs:
        try:
            raw = open(f, "rb").read()
        except Exception:
            continue
        i = raw.find(mark)
        if i < 0:
            continue
        n += 1
        if n > 5:
            continue
        # расширенный контекст: 120 до и 160 после
        ctx = raw[max(0, i - 120):i + 160]
        txt = re.sub(rb"[^\x20-\x7e\xc0-\xff\xa8\xb8]", b".", ctx).decode("cp1251", "replace")
        print("  ФАЙЛ: %s" % s(os.path.basename(f)))
        print("    |%s|" % s(txt))
        print()
    print("  ВСЕГО файлов с этим маркером: %d\n" % n)

# Отдельно: ищем СЛОВО Merge как отдельный токен в дереве модели (не MECHANICA)
print("=" * 78)
print("ПОИСК 'MERGE' РЯДОМ С ИМЕНАМИ МОДЕЛЕЙ (признак булевой операции над деталью)")
print("=" * 78)
found = 0
for f in fs:
    try:
        raw = open(f, "rb").read()
    except Exception:
        continue
    for m in re.finditer(rb"MERGE", raw):
        i = m.start()
        ctx = raw[max(0, i - 100):i + 140]
        if b"MECHANICA" in ctx or b"MECH_" in ctx:
            continue                        # служебное — не булева операция
        txt = re.sub(rb"[^\x20-\x7e\xc0-\xff\xa8\xb8]", b".", ctx).decode("cp1251", "replace")
        print("  %-38s |%s|" % (s(os.path.basename(f))[:38], s(txt)))
        found += 1
        break
    if found >= 8:
        break
print("найдено НЕ-механических MERGE: %d показано" % found)
print("\nPROBE OK")
