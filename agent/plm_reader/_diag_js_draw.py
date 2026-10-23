# -*- coding: utf-8 -*-
"""_diag_js_draw.py — печатает функцию draw из собранной страницы (для глаза).

Запуск: python _diag_js_draw.py
"""
import os
import re
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(HERE, "CREO_GRAPH.html")


def main():
    h = open(PAGE, encoding="utf-8").read()
    js = re.search(r"<script>(.*)</script>", h, re.S).group(1)
    i = js.find("function draw")
    j = js.find("render();", i)
    block = js[i:j]
    out = open(os.path.join(HERE, "_draw_dump.txt"), "w", encoding="utf-8")
    out.write(block)
    out.close()
    print("draw: %d символов -> _draw_dump.txt" % len(block))
    # краткая сводка опасных мест
    print("N как список узлов?", "N[" in block)
    print("Object.keys(N).length:", "Object.keys(N).length" in block)
    print("строка 'rows[c].sort()':", "rows[c].sort()" in block)
    print("pos построен:", "pos[m] = [x, y]" in block)
    print("Math.max(...массив):", "Math.max(...cols" in block)
    return 0


if __name__ == "__main__":
    sys.exit(main())
