# -*- coding: utf-8 -*-
"""_diag_drw.py — почему у 5 263 узлов нет превью: разбор по типам файлов.

Смотрим в базе: сколько .prt/.asm/.drw; у скольких читается картинка (JPEG) и чертёж (BMP).

Запуск: python _diag_drw.py
"""
import os
import re
import sys
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import engine                      # noqa: E402
import plm_graph as G              # noqa: E402


def ext_of(path):
    low = (path or "").lower()
    for e in (".prt.", ".asm.", ".drw.", ".mfg."):
        if e in low:
            return e.strip(".")
    return "?"


def main():
    con = engine.connect()
    rows = con.execute("SELECT model, path FROM snapshots").fetchall()
    con.close()
    print("записей в базе:", len(rows))
    kinds = Counter(ext_of(p) for _, p in rows)
    print("типы файлов:", dict(kinds))

    # проверим чтение превью по 40 файлам каждого типа
    for kind in (".prt.", ".asm.", ".drw."):
        sample = [(m, p) for m, p in rows if ext_of(p) == kind.strip(".")][:40]
        jpg = bmp = none = 0
        for _m, p in sample:
            if not p or not os.path.isfile(p):
                none += 1
                continue
            try:
                raw = open(p, "rb").read()
            except OSError:
                none += 1
                continue
            d1, e1 = G.cut_preview(raw, "jpg")
            d2, e2 = G.cut_preview(raw, "bmp")
            if d1:
                jpg += 1
            elif d2:
                bmp += 1
            else:
                none += 1
        print("%-7s проверено %2d: JPEG %2d | BMP %2d | нет %2d"
              % (kind, len(sample), jpg, bmp, none))
    return 0


if __name__ == "__main__":
    sys.exit(main())
