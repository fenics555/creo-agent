# -*- coding: utf-8 -*-
"""РАСШИФРОВКА КОДОВ feat_type/op_type — как Creo различает ВИДЫ операций.

Владелец: «наследований есть несколько вариантов в крео: как наследование, как добавление
тела... разница есть». Значит Creo хранит КОД типа операции. Смотрим сами значения рядом
с деревом построения. Только ЧТЕНИЕ.
"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Берём файлы с MERGE_BASE_PART и с деревом построения — где точно есть интересное
TESTS = [
    (r"Z:\PTC\Work\000_03 401-LIT Литейное производство\000_5 401-LIT-MO "
     r"Модельная оснастка для литья\500-55-500 Корпус пресс-головок"),
    (r"Z:\PTC\Work\000_03 401-LIT Литейное производство\000_5 401-LIT-MO "
     r"Модельная оснастка для литья\171meta держатель форм"),
]


def s(x):
    return str(x or "").encode("ascii", "replace").decode()


def models(root, limit=60):
    out = []
    if not os.path.isdir(root):
        return out
    for dp, _d, fs in os.walk(root, onerror=lambda e: None):
        for f in fs:
            if re.search(r"\.(prt|asm)\.\d+$", f, re.I):
                out.append(os.path.join(dp, f))
                if len(out) >= limit:
                    return out
    return out


files = []
for t in TESTS:
    fs = models(t)
    print("%-30s моделей: %d" % (s(os.path.basename(t))[:30], len(fs)))
    files += fs

print("\n" + "=" * 78)
print("ЗНАЧЕНИЯ РЯДОМ С feat_type (первые вхождения, сырые байты)")
print("=" * 78)
seen = 0
for f in files:
    if seen >= 8:
        break
    try:
        raw = open(f, "rb").read()
    except Exception:
        continue
    i = raw.find(b"feat_type")
    if i < 0:
        continue
    ctx = raw[i:i + 120]
    txt = re.sub(rb"[^\x20-\x7e\xc0-\xff\xa8\xb8]", b" ", ctx).decode("cp1251", "replace")
    txt = re.sub(r"\s+", " ", txt)
    print("  %-34s feat_type:%s" % (s(os.path.basename(f))[:34], s(txt[:70])))
    seen += 1

print("\n" + "=" * 78)
print("ЗНАЧЕНИЯ РЯДОМ С op_type")
print("=" * 78)
seen = 0
for f in files:
    if seen >= 8:
        break
    try:
        raw = open(f, "rb").read()
    except Exception:
        continue
    i = raw.find(b"op_type")
    if i < 0:
        continue
    ctx = raw[i:i + 120]
    txt = re.sub(rb"[^\x20-\x7e\xc0-\xff\xa8\xb8]", b" ", ctx).decode("cp1251", "replace")
    txt = re.sub(r"\s+", " ", txt)
    print("  %-34s op_type:%s" % (s(os.path.basename(f))[:34], s(txt[:70])))
    seen += 1

print("\n" + "=" * 78)
print("ФАЙЛЫ С MERGE_BASE_PART: полный разбор окружения")
print("=" * 78)
for t in TESTS:
    for f in models(t, 200):
        try:
            raw = open(f, "rb").read()
        except Exception:
            continue
        i = raw.find(b"MERGE_BASE_PART")
        if i < 0:
            continue
        # показываем ОКРУЖЕНИЕ шире: 300 до, 300 после
        ctx = raw[max(0, i - 300):i + 300]
        txt = re.sub(rb"[^\x20-\x7e\xc0-\xff\xa8\xb8]", b".", ctx).decode("cp1251", "replace")
        print("  ФАЙЛ: %s" % s(f))
        print("  |%s|" % s(txt))
        print()

print("PROBE OK")
