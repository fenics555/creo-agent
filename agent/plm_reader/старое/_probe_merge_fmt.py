# -*- coding: utf-8 -*-
"""ТОЧНЫЙ ФОРМАТ MERGE_BASE_PART: байты до и после имени родителя.

Правило владельца: имя родителя и потомка может быть ЛЮБЫМ. Связь — только по имени
ВНУТРИ файла (из маркера). Здесь измеряем точные разделители, чтобы парсер не врал.
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
    r"Модельная оснастка для литья\500-55-500 Корпус пресс-головок",
    r"Z:\PTC\Work\000_03 401-LIT Литейное производство\000_5 401-LIT-MO "
    r"Модельная оснастка для литья\171meta держатель форм",
    r"Z:\PTC\Work\000_03 401-LIT Литейное производство\000_5 401-LIT-MO "
    r"Модельная оснастка для литья\170meta Держатель форм",
]


def models(root, limit=120):
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
for r in ROOTS:
    files += models(r)

print("файлов: %d\n" % len(files))
print("=" * 78)
print("СЫРЫЕ БАЙТЫ ВОКРУГ КАЖДОГО 'MERGE_BASE_PART' (hex + текст)")
print("=" * 78)

total = 0
multi = []
for f in files:
    try:
        raw = open(f, "rb").read()
    except Exception:
        continue
    hits = [m.start() for m in re.finditer(rb"MERGE_BASE_PART", raw)]
    if not hits:
        continue
    total += len(hits)
    if len(hits) > 1:
        multi.append((os.path.basename(f), len(hits)))
    if len(hits) > 1 and len(multi) <= 3:
        print("\n### ФАЙЛ С НЕСКОЛЬКИМИ ЗАПИСЯМИ: %s (%d записей)"
              % (os.path.basename(f), len(hits)))
    for i in hits[:2]:
        after = raw[i + len(b"MERGE_BASE_PART"): i + len(b"MERGE_BASE_PART") + 80]
        before = raw[max(0, i - 40):i]
        print("  %-34s" % os.path.basename(f)[:34])
        print("     BEFORE: %r" % before[-30:])
        print("     AFTER : %r" % after)
        # ищем имя: последовательность печатных байт длиной >=4 после маркера
        m = re.search(rb"[\x20-\x7e\xc0-\xff\xa8\xb8]{4,64}", after)
        print("     ИМЯ(1): %r" % (m.group(0) if m else None))

print("\n" + "=" * 78)
print("ИТОГО: файлов с маркером %d записей %d" % (len(multi), total))
print("ФАЙЛЫ С НЕСКОЛЬКИМИ РОДИТЕЛЯМИ (несколько вариантов наследования!):")
for n, c in multi:
    print("   %-50s %d" % (n[:50], c))
print("\nPROBE OK")
