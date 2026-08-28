# -*- coding: utf-8 -*-
# Живая проверка: следит за *.py папки агента, при каждом Ctrl+S гонит диагностику.
import time, subprocess, sys
from pathlib import Path
HERE = Path(__file__).parent
seen = {p.name: p.stat().st_mtime for p in HERE.glob("*.py")}
print("слежу за %s — сохрани файл, проверка пройдёт сама" % HERE)
while True:
    time.sleep(1)
    cur = {p.name: p.stat().st_mtime for p in HERE.glob("*.py")}
    if cur != seen:
        ch = [n for n in cur if seen.get(n) != cur[n]]
        seen = cur
        print("\n=== изменено: %s ===" % ", ".join(ch))
        subprocess.run([sys.executable, str(HERE / "diagnostic_tools.py")])