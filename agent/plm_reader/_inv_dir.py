# -*- coding: utf-8 -*-
"""ИНВЕНТАРЬ КАТАЛОГА PLM Reader: что оставить, что в 'старое', что мертво.

Задание владельца (28.10.2026): «нужна ОДНА функция сканера: полный скан и скан только нового,
построитель отдельно, граф отдельно. И на пути окна: ОСНОВНОЕ ОКНО ПЛМ-ридера и ХТМЛ. Всё
остальное — в отдельную папку "старое" с возможностью удалить! И свести всё».

Считает ФАКТОМ, без догадок:
  * размер каждого файла;
  * кто кого импортирует (AST — по-настоящему, а не поиском строк);
  * какие файлы НИКЕМ не импортируются (кандидаты в «старое»);
  * какие модули обязательны (входят в поставку version.json).
"""
import ast
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = os.path.join(HERE, "_inventory_report.txt")
L = []


def say(*a):
    L.append(" ".join(str(x) for x in a))


# 1) поставка (что реально нужно на шаре) — из манифеста
try:
    with open(os.path.join(HERE, "version.json"), encoding="utf-8") as f:
        ship = set(json.load(f).get("files", {}).keys())
except Exception as e:
    ship = set()
    say("НЕ ПРОЧИТАЛ version.json:", e)

py = sorted(f for f in os.listdir(HERE) if f.endswith(".py"))
other = sorted(f for f in os.listdir(HERE)
               if not f.endswith(".py") and os.path.isfile(os.path.join(HERE, f)))

say("=== ФАЙЛЫ .py (%d) ===" % len(py))
say("%-28s %7s %7s %s" % ("файл", "строк", "байт", "в поставке"))
for f in py:
    p = os.path.join(HERE, f)
    lines = sum(1 for _ in open(p, encoding="utf-8", errors="replace"))
    say("%-28s %7d %7d %s" % (f, lines, os.path.getsize(p), "ДА" if f in ship else "—"))

say()
say("=== НЕ-.py ФАЙЛЫ (%d) ===" % len(other))
for f in other:
    p = os.path.join(HERE, f)
    say("%-28s %9d %s" % (f, os.path.getsize(p), "ДА" if f in ship else "—"))

# 2) ИМПОРТЫ (AST)
say()
say("=== КТО КОГО ИМПОРТИРУЕТ (по AST) ===")
imports = {}
for f in py:
    try:
        tree = ast.parse(open(os.path.join(HERE, f), encoding="utf-8", errors="replace").read())
    except Exception as e:
        say("  %s: НЕ РАЗОБРАЛ (%s)" % (f, e))
        continue
    got = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                got.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                got.add(node.module.split(".")[0])
    imports[f] = {m for m in got if (m + ".py") in py}
    if imports[f]:
        say("  %-28s -> %s" % (f, ", ".join(sorted(imports[f]))))

# 3) ОБРАТНЫЕ: кто нужен
needed = set()
for f, mods in imports.items():
    needed |= mods
say()
say("=== НИКЕМ НЕ ИМПОРТИРУЕТСЯ (кандидаты в 'старое') ===")
orphans = []
for f in py:
    if f == "__init__.py":
        continue
    if f not in needed and f not in ship:
        orphans.append(f)
        say("  %-28s (%d байт)" % (f, os.path.getsize(os.path.join(HERE, f))))

say()
say("=== НУЖНЫ ВСЕГДА (в поставке version.json) ===")
for f in sorted(ship):
    if f.endswith(".py"):
        say("  %-28s импортируют: %s" % (f, ", ".join(sorted(k for k, v in imports.items() if f[:-3] in v)) or "—"))

say()
say("ИТОГ: всего .py %d · в поставке %d · кандидатов в 'старое' %d"
    % (len(py), len([f for f in py if f in ship]), len(orphans)))

with open(OUT, "w", encoding="utf-8") as fh:
    fh.write("\n".join(L))
print("ОТЧЁТ:", OUT, "· строк:", len(L))
