# -*- coding: utf-8 -*-
r"""Чистка unused-импортов в блоках (одноразовая). Запуск: python fix_imports.py"""
import io, os

HERE = os.path.dirname(os.path.abspath(__file__))

DROP_LINES = {
 "core.py": ["import numpy as np"],
 "diagnostic_tools.py": ["from core import log"],
 "memory_tools.py": ["from pathlib import Path", "import core"],
 "panel.py": ["from core import log", "import settings"],
 "passport_tools.py": ["from pathlib import Path", "from core import log"],
 "users.py": ["from pathlib import Path"],
 "vision_tools.py": ["from pathlib import Path"],
}
DROP_NAMES = {
 "core.py": ["os", "uuid"],
 "diagnostic_tools.py": ["re"],
}
REPLACE = {
 "trail_tools.py": [("from core import log, db", "from core import db")],
}

def clean_import_line(line, names):
    if not line.lstrip().startswith("import "): return line
    head = line[:len(line) - len(line.lstrip())]
    items = [x.strip() for x in line.strip()[len("import "):].split(",")]
    keep = [x for x in items if x not in names and x.split(" as ")[0].strip() not in names]
    if not keep: return None
    return head + "import " + ", ".join(keep) + "\n"

for fn in DROP_LINES:
    p = os.path.join(HERE, fn)
    if not os.path.exists(p): continue
    out = []
    for ln in io.open(p, encoding="utf-8").read().splitlines(keepends=True):
        if ln.strip() in DROP_LINES[fn]: continue
        if fn in DROP_NAMES:
            nl = clean_import_line(ln, DROP_NAMES[fn])
            if nl is None: continue
            ln = nl
        out.append(ln)
    io.open(p, "w", encoding="utf-8").write("".join(out))
    print("чищено:", fn)

for fn, pairs in REPLACE.items():
    p = os.path.join(HERE, fn)
    if not os.path.exists(p): continue
    s = io.open(p, encoding="utf-8").read()
    for a, b in pairs: s = s.replace(a, b)
    io.open(p, "w", encoding="utf-8").write(s)
    print("замена:", fn)

print("готово; проверь: pyflakes D:\\AI\\tools\\agent")