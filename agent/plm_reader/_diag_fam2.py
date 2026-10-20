# -*- coding: utf-8 -*-
"""V100-diagnostics2: TOC-секции файла семейства + FAM-метки в байтах."""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, r"D:\AI\log\creo_reverse_engineering")

import engine as eng

for name in ("G6402", "25-1-G18829-2017"):
    con = eng.connect()
    row = con.execute("SELECT path FROM snapshots WHERE model=? ORDER BY mtime DESC LIMIT 1",
                      (name,)).fetchone()
    con.close()
    path = row[0] if row else ""
    print("==", name, "->", path)
    if not path or not os.path.isfile(path):
        print("  файла нет")
        continue
    # TOC
    try:
        from creo_toc_parser import parse_creo_toc
        toc = parse_creo_toc(path)
        print("  TOC секций: %d" % len(toc))
        for k, v in toc.items():
            print("    %-24s %s" % (k, hex(v) if isinstance(v, int) else v))
    except Exception as e:
        print("  TOC ошибка:", e)
    # поиск FAM-меток в сырых байтах (ASCII)
    data = open(path, "rb").read()
    hits = {}
    for m in re.finditer(rb"FAM[A-Za-z_]{0,16}", data):
        s = m.group().decode("ascii", "replace")
        hits[s] = hits.get(s, 0) + 1
    print("  FAM-метки:", dict(list(hits.items())[:20]) if hits else "НЕТ")
