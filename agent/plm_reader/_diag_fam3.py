# -*- coding: utf-8 -*-
"""V100-diagnostics: строки секции FamilyInf (имена исполнений family table)."""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engine as eng

con = eng.connect()
row = con.execute("SELECT path FROM snapshots WHERE model=? ORDER BY mtime DESC LIMIT 1",
                  ("25-1-G18829-2017",)).fetchone()
con.close()
p = row[0]
data = open(p, "rb").read()
sec = data[0x2435a:0x2c7420]
print("файл:", p)
print("размер секции FamilyInf:", len(sec))
strs = [(m.start(), m.group().decode("ascii")) for m in re.finditer(rb"[ -~]{3,}", sec)]
print("ASCII-строк:", len(strs))
for off, s in strs[:100]:
    print("  +%06x %s" % (off, s))
