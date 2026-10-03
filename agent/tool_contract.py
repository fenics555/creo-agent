# -*- coding: utf-8 -*-
"""tool_contract.py — КОНТРАКТ ПРОГРАММЫ (`tool.json`), волна 2 (этап 1.5 плана).

ЗАЧЕМ: программа дома описывает себя ОДНИМ файлом `tool.json` рядом с движком.
Его читают: агент (`prog_tools`), витрина, окно. Код программы не нужен, чтобы узнать,
что она умеет, какие у неё настройки и какие модули надо положить рядом при переносе.

ПРИНЦИП ВОЛНЫ 1 (перенесён): обязательны только `id`, `title`, `engine`; остальное
необязательное, и БИТЫЙ контракт не должен ронять программу — читатель возвращает
честную ошибку, а исключение.

ФОРМАТ (минимальный, см. спеку волны 2):
    {"id": "config_audit", "title": "...", "engine": "config_audit.py",
     "kind": "check", "group": "Creo", "needs_creo": false, "class": "Р",
     "gui": "gui.py", "gui_bat": "...", "readme": "README.md",
     "cli": ["--help"], "inputs": [{"name": ..., "type": ..., "default": ..., "desc": ...}],
     "outputs": {"report": "...", "log": "..."}, "settings": "...json",
     "deps": ["creo_path"], "approval": false}
"""
import json
from pathlib import Path

AGENT = Path(__file__).resolve().parent
REQUIRED = ("id", "title", "engine")          # без этих контракт неполон
KINDS = ("check", "report", "act", "read", "admin", "other")   # те же, что у инструментов

_CACHE = {}      # путь -> (contract|None, ошибка)


def validate(d):
    """Проверка контракта: список строк об ошибках (пусто = валиден)."""
    errs = []
    if not isinstance(d, dict):
        return ["контракт не объект: %s" % type(d).__name__]
    for k in REQUIRED:
        if not str(d.get(k) or "").strip():
            errs.append("нет обязательного поля «%s»" % k)
    kind = (d.get("kind") or "other").lower()
    if kind not in KINDS:
        errs.append("kind=%s не из списка %s" % (kind, ", ".join(KINDS)))
    for f in ("engine", "gui", "gui_bat", "readme", "settings"):
        v = d.get(f)
        if v and not (str(v).lstrip().endswith(".json") or "/" in str(v) or "\\" in str(v)
                      or str(v).endswith((".py", ".bat", ".md"))):
            errs.append("%s=%s не похоже на файл" % (f, v))
    dep = d.get("deps")
    if dep is not None and not isinstance(dep, list):
        errs.append("deps должен быть списком, а не %s" % type(dep).__name__)
    inp = d.get("inputs")
    if inp is not None and not isinstance(inp, list):
        errs.append("inputs должен быть списком, а не %s" % type(inp).__name__)
    return errs


def load(path):
    """Читает контракт по пути. Возвращает (контракт|None, ошибка|None)."""
    p = Path(path)
    key = str(p)
    if key in _CACHE:
        return _CACHE[key]
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        res = (None, "контракта нет: %s" % p)
    except Exception as e:
        res = (None, "контракт не читается (%s): %s" % (p, e))
    else:
        errs = validate(d)
        if errs:
            res = (d, "контракт %s неполон: %s" % (p, "; ".join(errs)))
        else:
            res = (d, None)
    _CACHE[key] = res
    return res


def load_dir(prog_dir):
    """Читает `tool.json` из папки программы. Возвращает (контракт|None, ошибка|None)."""
    return load(Path(prog_dir) / "tool.json")


def all_contracts(root=None):
    """Все контракты под программами агента: {id: (контракт, путь, ошибка)}."""
    root = Path(root or AGENT)
    out = {}
    for p in sorted(root.glob("*/tool.json")):
        c, err = load(p)
        if c is None:
            continue
        out[str(c.get("id") or p.parent.name)] = (c, p, err)
    return out


def deps_of(prog_dir):
    """Список модулей агента, которые нужны программе при переносе."""
    c, _ = load_dir(prog_dir)
    return list((c or {}).get("deps") or [])


def save(contract, path):
    """Записывает контракт. Перед записью проверяет: мусор не пишем.

    (Добавлено в волне 5 при генерации контрактов для 11 программ.)"""
    errs = validate(contract)
    if errs:
        raise ValueError("не сохранено: %s" % "; ".join(errs[:5]))
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    _CACHE.pop(str(p), None)
    return str(p)


def card(c):
    """Краткая строка контракта для витрины и журналов."""
    if not c:
        return "нет контракта"
    return "%s [%s/%s] движок=%s%s" % (
        c.get("id"), c.get("kind") or "other", c.get("group") or "общее",
        c.get("engine"), ", требует Creo" if c.get("needs_creo") else "")


if __name__ == "__main__":
    cs = all_contracts()
    print("контрактов: %d" % len(cs))
    for pid, (c, p, err) in cs.items():
        print(" %-16s %s" % (pid, card(c)))
        if err:
            print("   ВНИМАНИЕ: %s" % err)
    bad = [(k, e) for k, (c, p, e) in cs.items() if e]
    print("=== контрактов: %d, проблемных: %d ===" % (len(cs), len(bad)))