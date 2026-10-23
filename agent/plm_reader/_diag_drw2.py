# -*- coding: utf-8 -*-
"""_diag_drw2.py — где реально есть превью: разбор по ПАПКАМ (не по первым записям).

Берём по 25 файлов из РАЗНЫХ папок и смотрим, читается ли JPEG/BMP.
Запуск: python _diag_drw2.py
"""
import os
import random
import sys
from collections import Counter, defaultdict

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import engine                      # noqa: E402
import plm_graph as G              # noqa: E402


def main():
    con = engine.connect()
    rows = con.execute("SELECT path FROM snapshots").fetchall()
    con.close()
    paths = [r[0] for r in rows if r[0] and os.path.isfile(r[0])]
    print("живых путей:", len(paths), "из", len(rows))

    by_dir = defaultdict(list)
    for p in paths:
        by_dir[os.path.dirname(p)].append(p)
    print("папок:", len(by_dir))

    random.seed(42)                     # воспроизводимость (§М.2е)
    dirs = random.sample(sorted(by_dir), min(12, len(by_dir)))
    tot = Counter()
    for d in dirs:
        smp = by_dir[d][:12]
        c = Counter()
        for p in smp:
            try:
                raw = open(p, "rb").read()
            except OSError:
                c["нет доступа"] += 1
                continue
            d1, _ = G.cut_preview(raw, "jpg")
            d2, _ = G.cut_preview(raw, "bmp")
            c["JPEG" if d1 else ("BMP" if d2 else "пусто")] += 1
        tot.update(c)
        print("  %-70s %s" % (d[-70:], dict(c)))
    print("\nИТОГО по выборке:", dict(tot))
    return 0


if __name__ == "__main__":
    sys.exit(main())
