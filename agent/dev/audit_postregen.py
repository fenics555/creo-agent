# -*- coding: utf-8 -*-
r"""audit_postregen.py — КАРТА ПУТЕЙ программы postregen_clean (04.10.2026).

Зачем: скилл аудита требует карту «куда пишет / откуда читает», а такой
инструмента в доме для ПРОГРАММЫ нет (audit_settings.py смотрит только
настройки агента). Здесь разбор ЧЕРЕЗ AST — не грепл по глазам, потому что
глазами пути в f-строках и склейках не видны.

Что даёт по каждому файлу:
  ПИШЕТ  — open(...,'w'/'a'), write_text, mkdir/makedirs, shutil copy/move/rmtree,
           unlink/remove, os.remove, а также сетевые вызовы CREOSON (запись в Creo);
  ЧИТАЕТ — open(...,'r'), read_text, read_bytes, listdir/glob/rglob/walk,
           json.load, os.environ, LoadSettings;
  ПУТИ   — все строковые константы вида «X:\...» или «X:/...»;
  НАСТР. — откуда берётся каждое значение настройки (по месту чтения).

Запуск: cmd /c "python -X utf8 audit_postregen.py > out 2>&1"
Вывод: agent\\postregen_clean\\audit_paths_out.txt
"""
import ast
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

AGENT = Path(__file__).resolve().parent
# ВНИМАНИЕ: скрипт лежит в dev\, поэтому программа — на уровень выше (agent\).
TOOL = AGENT.parent / "postregen_clean"
OUT = TOOL / "audit_paths_out.txt"

# Кого аудируем: программа + её библиотечные зависимости (оттуда тоже пишут).
TARGETS = [
    TOOL / "plan.py", TOOL / "apply.py", TOOL / "gui.py",
    AGENT.parent / "ui_common.py", AGENT.parent / "creo_tools.py",
]
SKIP_DIRS = {"__pycache__"}

WRITE_CALLS = {"write_text", "write_bytes", "mkdir", "makedirs", "rmdir", "removedirs",
               "copy", "copy2", "copystat", "copytree", "move", "rmtree", "unlink",
               "remove", "rename", "replace", "touch", "creo_call", "creo_raw",
               "tool_set_param", "tool_status"}
READ_CALLS = {"read_text", "read_bytes", "listdir", "scandir", "glob", "rglob",
              "walk", "load", "loads", "load_settings", "exists", "is_file", "stat",
              "environ", "getenv"}
MODE_WRITE = ("w", "a", "wb", "ab", "x", "w+", "a+")


def call_name(node):
    """Имя вызова: f(...) -> 'f'; mod.f(...) -> 'mod.f'; a.b.f -> 'a.b.f'."""
    f = node.func
    parts = []
    while isinstance(f, ast.Attribute):
        parts.append(f.attr)
        f = f.value
    if isinstance(f, ast.Name):
        parts.append(f.id)
    return ".".join(reversed(parts))


def strings_of(node, out):
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            out.add(n.value)


def audit(py):
    """(пути-константы, список записей, список чтений) по одному файлу."""
    src = py.read_text(encoding="utf-8")
    tree = ast.parse(src)
    paths, writes, reads = set(), [], []

    for n in ast.walk(tree):
        # --- строковые константы-пути (в т.ч. ВНУТРИ f-строк)
        if isinstance(n, ast.Constant) and isinstance(n.value, str):
            s = n.value
            if len(s) > 2 and s[1] == ":" and s[2] in "\\/":
                paths.add((s, n.lineno))
        if isinstance(n, ast.JoinedStr):
            strings_of(n, _tmp := set())
            for s in _tmp:
                if len(s) > 2 and s[1] == ":" and s[2] in "\\/":
                    paths.add((s, n.lineno))

        if isinstance(n, ast.Call):
            name = call_name(n).split(".")[-1]
            args = [a.value for a in n.args
                    if isinstance(a, ast.Constant) and isinstance(a.value, str)]
            where = "%s:%d" % (py.name, n.lineno)
            if name in ("open",):
                mode = ""
                if len(n.args) > 1 and isinstance(n.args[1], ast.Constant):
                    mode = str(n.args[1].value)
                elif any(k.arg == "mode" for k in n.keywords):
                    for k in n.keywords:
                        if k.arg == "mode" and isinstance(k.value, ast.Constant):
                            mode = str(k.value.value)
                line = "%s open(mode=%r) %s" % (where, mode, args[:1])
                (writes if mode in MODE_WRITE else reads).append(line)
            elif name in WRITE_CALLS:
                writes.append("%s %s %s" % (where, name, args[:2]))
            elif name in READ_CALLS:
                reads.append("%s %s %s" % (where, name, args[:2]))
        # --- доступ к переменной окружения
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) \
                and n.value.id == "os" and n.attr in ("environ", "getenv"):
            reads.append("%s os.%s" % (py.name, n.attr))
    return paths, writes, reads


def main():
    o = []
    o.append("КАРТА ПУТЕЙ: postregen_clean (04.10.2026)")
    o.append("=" * 78)
    all_paths, all_w, all_r = [], [], []
    for py in TARGETS:
        if not py.exists():
            o.append("\n### %s — НЕТ ФАЙЛА" % py)
            continue
        p, w, r = audit(py)
        o.append("\n### %s" % py)
        o.append("-- ПУТИ-КОНСТАНТЫ (%d):" % len(p))
        for s, ln in sorted(p, key=lambda x: x[1]):
            o.append("   стр.%d: %s" % (ln, s))
        o.append("-- ПИШЕТ (%d):" % len(w))
        o.extend("   " + x for x in w)
        o.append("-- ЧИТАЕТ (%d):" % len(r))
        o.extend("   " + x for x in r)
        all_paths += list(p)
        all_w += w
        all_r += r
    o.append("\n" + "=" * 78)
    o.append("ИТОГО: путей %d, записей %d, чтений %d" % (len(all_paths),
                                                         len(all_w), len(all_r)))
    OUT.write_text("\n".join(o), encoding="utf-8")
    print("\n".join(o[-1:]))
    return 0


if __name__ == "__main__":
    sys.exit(main())