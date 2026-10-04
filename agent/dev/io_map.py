# -*- coding: utf-8 -*-
r"""io_map.py (Cline, 04.10.2026) — КАРТА ДАННЫХ ДОМА: что куда пишет и что откуда читает.

Вопрос владельца: «что куда пишет, что откуда читает». Ответ машиной, а не на глаз:
для каждого файла данных (БД, JSON, логи, настройки, бекапы) — кто пишет (файл:строка)
и кто читает. Ничего не выдумывается: всё из кода через ast.

Запуск: cmd /c "python -X utf8 dev\io_map.py > out 2>&1"
"""
import ast
import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))

SKIP_DIRS = {"__pycache__", "_legacy", "_disabled", "node_modules", ".git", "data", "log"}
SKIP_FILES = {"io_map.py"}
# Признаки ЗАПИСИ в коде: open(..., 'w'/'a'), write_text, write_bytes, os.remove,
# shutil.rmtree/copy/move, sqlite INSERT/UPDATE/DELETE/CREATE, json.dump.
# Признаки записи/чтения в коде проверяются НЕ регуляркой по всему файлу, а разбором ast:
# регулярка по тексту тела даёт ложные срабатывания (строка в комментарии, текст в справке).
# WRITE_RE/READ_RE оставлены как памятка для grep-поиска глазами, в разборе они не участвуют.
WRITE_RE = re.compile(r"\.write_text\(|\.write_bytes\(|open\([^)]*['\"][wax]|"
                      r"shutil\.(rmtree|copy|move)\(|\.unlink\(|os\.remove\(|"
                      r"INSERT INTO|UPDATE |DELETE FROM|CREATE TABLE|json\.dump\(", re.I)
READ_RE = re.compile(r"\.read_text\(|\.read_bytes\(|open\([^)]*['\"]r|SELECT .* FROM|"
                     r"json\.load\(|os\.listdir\(|iterdir\(|glob\(", re.I)


def norm_file(path_txt):
    """Приводит кусок пути к «данные дома» — чтобы группировать по фактическому хранилищу."""
    t = path_txt.replace("/", "\\")
    t = re.sub(r"[A-Za-z]:\\", "", t)
    for root, name in (("AI\\repo", "REPO (скиллы, карты, планы)"),
                       ("AI\\tools", "TOOLS (код агента)"),
                       ("AI\\log", "LOG (логи и отчёты)"),
                       ("AI\\tools\\agent\\data", "AGENT DATA (база, конфиг, кэш)")):
        if t.lower().startswith(root.lower()):
            return name
    if t.lower().startswith("ai\\"):
        return "ДОМ\\AI (прочее)"
    return t


def line_of(tree, node):
    try:
        return node.lineno
    except Exception:
        return 0


def scan(py):
    rel = py.relative_to(AGENT)
    try:
        src = py.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(src)
    except Exception:
        return []
    out = []
    # SQL-запросы: CREATE/INSERT — запись, SELECT — чтение. Имя таблицы = хранилище.
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            v = node.value
            mode = None
            if re.search(r"^\s*(INSERT INTO|UPDATE |DELETE FROM|CREATE TABLE|DROP TABLE)", v, re.I):
                mode = "W"
            elif re.search(r"^\s*SELECT\b", v, re.I):
                mode = "R"
            if mode:
                # ЖИВАЯ НАХОДКА 04.10.2026: регулярка брала слово ПОСЛЕ INTO/FROM/TABLE и
                # «CREATE TABLE IF NOT EXISTS history» давало хранилище «SQL:IF» — мусор.
                # Теперь IF NOT EXISTS / IF EXISTS отбрасываются как служебные слова.
                m = re.search(r"(?:INTO|FROM|TABLE)(?:\s+IF\s+(?:NOT\s+)?EXISTS)?\s+"
                              r"([A-Za-z_][A-Za-z0-9_]*)", v, re.I)
                if m and m.group(1).upper() not in ("IF", "NOT", "EXISTS", "SELECT", "SET"):
                    out.append((mode, "SQL:%s" % m.group(1), "%s:%d" % (rel, line_of(tree, node))))
    # Файловые операции: ищем вызовы с константным строковым аргументом.
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        nm = fn.attr if isinstance(fn, ast.Attribute) else (fn.id if isinstance(fn, ast.Name) else "")
        args = [a for a in node.args if isinstance(a, ast.Constant) and isinstance(a.value, str)]
        if not args:
            continue
        val = args[0].value
        if "\\" not in val and "/" not in val and not val.endswith((".db", ".json", ".log")):
            continue
        if nm in ("write_text", "write_bytes", "mkdir", "unlink", "rmtree", "copy", "move", "copy2"):
            out.append(("W", norm_file(val), "%s:%d" % (rel, line_of(tree, node))))
        elif nm in ("read_text", "read_bytes", "listdir", "iterdir", "glob", "rglob", "exists"):
            out.append(("R", norm_file(val), "%s:%d" % (rel, line_of(tree, node))))
    # Имена переменных-констант с путями (CONFIG_FILE, LOGF, DB, PREF_FILE…).
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name) \
                and node.targets[0].id.isupper():
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                v = node.value.value
                if "\\" in v or v.endswith((".db", ".json")):
                    out.append(("D", norm_file(v), "%s:%d %s" % (rel, line_of(tree, node), node.targets[0].id)))
    return out


def main():
    store = {}
    for py in sorted(AGENT.rglob("*.py")):
        rel = py.relative_to(AGENT)
        if any(p in SKIP_DIRS for p in rel.parts) or py.name in SKIP_FILES:
            continue
        for mode, target, where in scan(py):
            key = target
            e = store.setdefault(key, {"W": [], "R": [], "D": []})
            if len(e[mode]) < 6 and where not in e[mode]:
                e[mode].append(where)
    print("=" * 100)
    print("КАРТА ДАННЫХ ДОМА: %d хранилищ" % len(store))
    print("=" * 100)
    for key in sorted(store, key=lambda k: (-len(store[k]["W"]), k)):
        e = store[key]
        tag = "ПИШЕТСЯ" if e["W"] else ("ТОЛЬКО ЧИТАЕТСЯ" if e["R"] else "объявлено")
        print("\n■ %s   [%s]" % (key, tag))
        if e["D"]:
            print("   константы: %s" % ", ".join(sorted(set(e["D"]))[:4]))
        for w in e["W"][:5]:
            print("   запись  <- %s" % w)
        for r in e["R"][:3]:
            print("   чтение -> %s" % r)
    # ПРАВКА 04.10.2026 (слово владельца «делай», нарушение культуры №1): файл уходил в
    # `log\reports`, где по закону дома лежат только `REPORT_<задача>_<исполнитель>_<дата>.md`
    # (проверка `dev\culture_check.py`). Машиночитаемый json — в папку инструмента `log\dev\`.
    out = Path(r"D:\AI\log\dev\io_map_cline.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({k: {m: v[m] for m in v} for k, v in store.items()},
                              ensure_ascii=False, indent=1), encoding="utf-8")
    print("\nJSON: %s" % out)
    return 0


if __name__ == "__main__":
    sys.exit(main())