# -*- coding: utf-8 -*-
r"""ПОИСК ПЕРЕКРЫТИЯ ИМЁН МОДУЛЕЙ ВНУТРИ ФУНКЦИЙ (dev-класс ошибки 24.09.2026).

Живой случай: в `http_handlers.do_GET` строка `core, ext, suffix = m.groups()` делала `core`
локальной переменной — и любое `core.REPO` внутри метода падало `UnboundLocalError`
(спасал только `try/except`, поэтому баг жил незамеченным).
Скрипт разбирает файл через ast и показывает функции, где локальные имена совпадают с
именами импортированных модулей.
"""
import ast
import sys
from pathlib import Path

TARGETS = sys.argv[1:] or [r"D:\AI\tools\agent\http_handlers.py"]
bad = 0
for path in TARGETS:
    src = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(src)
    mods = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for a in node.names:
                mods.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                mods.add(a.asname or a.name)
    print("=== %s (модульных имён: %d) ===" % (Path(path).name, len(mods)))
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            assigned = set()
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and isinstance(sub.ctx, ast.Store):
                    assigned.add(sub.id)
                elif isinstance(sub, ast.alias) and isinstance(sub.parent if hasattr(sub, "parent") else None, ast.Import):
                    pass
            assigned.discard("self")
            clash = sorted(assigned & mods)
            if clash:
                bad += 1
                print("  %s(): локальные имена перекрывают модули: %s" % (node.name, ", ".join(clash)))
    if not bad:
        print("  перекрытий нет")
print("ИТОГО функций с перекрытием:", bad)
