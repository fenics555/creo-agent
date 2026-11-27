# -*- coding: utf-8 -*-
"""Проверка SKILL_MAP через ast: все kind, которые движок возвращает,
имеют ключ в карте; все имена скиллов существуют в crash/.

Устойчиво к форматированию (многострочные return) — урок 273: структурно, не позицией.
Использование: python check_skillmap_ast.py [путь_к_loop_watch.py]
"""
import ast
import glob
import os
import sys

WATCH = sys.argv[1] if len(sys.argv) > 1 else r"D:\AI\tools\agent\loop_watch\loop_watch.py"
CRASH = r"D:\AI\repo\crash"

src = open(WATCH, encoding="utf-8-sig").read()  # utf-8-sig — снимает BOM (иначе ast.parse падает U+FEFF)
tree = ast.parse(src)

# 1. SKILL_MAP: ключи (kind) -> имена скиллов
map_keys = set()
map_skills = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "SKILL_MAP" and isinstance(node.value, ast.Dict):
                for k, v in zip(node.value.keys, node.value.values):
                    if isinstance(k, ast.Constant) and isinstance(k.value, str):
                        map_keys.add(k.value)
                        if isinstance(v, ast.Constant) and isinstance(v.value, str):
                            map_skills.add(v.value)

# 2. kind: последний строковый аргумент Return, НО только из 5-элементных кортежей
# check() (kind всегда 5-й элемент: (session, repeats, call, flag, kind)).
# pattern_loop возвращает 2-элементные (kind, skill) — там 2-й элемент СКИЛЛ, не kind.
kinds = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple):
        elts = node.value.elts
        if len(elts) == 5 and isinstance(elts[-1], ast.Constant) and isinstance(elts[-1].value, str):
            kinds.add(elts[-1].value)
# плюс kind из plan-loop (2-элементный кортеж: kind, skill) — берём ПЕРВЫЙ элемент
for node in ast.walk(tree):
    if isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple):
        elts = node.value.elts
        if len(elts) == 2 and isinstance(elts[0], ast.Constant) and isinstance(elts[0].value, str):
            kinds.add(elts[0].value)

# 3. имена файлов crash/
crash_names = {os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(CRASH, "*.md"))}

print("SKILL_MAP ключей:", len(map_keys))
print("kind (AST):", len(kinds), sorted(kinds))
print("имён скиллов:", len(map_skills))
bad_kinds = sorted(k for k in kinds if k not in map_keys)
bad_skills = sorted(s for s in map_skills if s not in crash_names)
print("kind без ключа:", bad_kinds if bad_kinds else "(нет)")
print("скиллов нет в crash\\:", bad_skills if bad_skills else "(нет)")
ok = not bad_kinds and not bad_skills
print("RESULT:", "OK" if ok else "FAIL")
sys.exit(0 if ok else 1)
