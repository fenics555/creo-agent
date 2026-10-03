# -*- coding: utf-8 -*-
r"""dev\drw_probe.py - РАЗВЕДКА: где в доме лежат чертежи .drw (волна 6, этап 4).

Ничего не меняет, только ищет и показывает. Если файлов нет - честно пишет НЕТ ДАННЫХ
с перечнем проверенных корней, а не выдумывает путь.
"""
import io
import os
import sys
import time

ROOTS = [r"Z:\PTC\CREO-START\Libraries", r"Z:\PTC\Work", r"Z:\PTC", r"D:\AI"]
LIMIT = 40


def walk_drw(root, limit=LIMIT):
    hits = []
    t0 = time.time()
    for dirpath, dirnames, filenames in os.walk(root):
        for f in filenames:
            if f.lower().endswith(".drw"):
                hits.append(os.path.join(dirpath, f))
                if len(hits) >= limit:
                    return hits, time.time() - t0
    return hits, time.time() - t0


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print("ПОИСК ЧЕРТЕЖЕЙ .drw")
    for r in ROOTS:
        if not os.path.exists(r):
            print("  корня нет: %s" % r)
            continue
        hits, secs = walk_drw(r)
        print("  %-32s найдено %d за %.1f с" % (r, len(hits), secs))
        for h in hits[:8]:
            print("      %s  (%d Б)" % (h, os.path.getsize(h)))
        if hits and len(hits) == LIMIT:
            print("      ... ограничение поиска достигнуто")
    return 0


if __name__ == "__main__":
    sys.exit(main())