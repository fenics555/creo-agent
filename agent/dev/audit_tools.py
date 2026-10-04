# -*- coding: utf-8 -*-
"""audit_tools.py (Cline, 04.10.2026) — ЧЕСТНЫЙ аудит ИНСТРУМЕНТОВ реестра.

Вопрос владельца после прогона: часть инструментов падает с
«missing 1 required positional argument: 'name'». Проверяем это ЖЁСТКО, без прогона
через LLM: сопоставляем объявленные параметры (`params` в TOOLS) с реальной сигнатурой `fn`.

Вердикты:
  OK        — у fn есть **kw или все объявленные параметры есть в сигнатуре;
  NO_KW     — у fn НЕТ **kwargs и есть обязательные позиционные, которых нет в params;
  PARAM_LIE — объявленный параметр не существует в сигнатуре fn;
  NO_PARAMS — у fn обязательные позиционные, но в params НЕ объявлены (модель их не пришлёт).

Запуск: cmd /c "python -X utf8 dev\audit_tools.py > out 2>&1"
"""
import ast
import inspect
import io
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))
import tools_registry as TR  # noqa: E402


def sig_of(fn):
    """(обязательные позиционные без дефолта, есть ли **kwargs) по исходнику ast."""
    try:
        src = inspect.getsource(fn)
        tree = ast.parse(src.strip())
        fndef = tree.body[0]
    except Exception as e:
        return None, None, "исходник не читается: %s" % str(e)[:40]
    if not isinstance(fndef, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return None, None, "не функция"
    a = fndef.args
    names = [x.arg for x in a.posonlyargs] + [x.arg for x in a.args]
    defaults = a.defaults
    n_no_default = len(names) - len(defaults)
    required = names[:n_no_default]
    has_kw = a.kwarg is not None
    return required, has_kw, None


def main():
    rows = []
    for t in TR.TOOLS:
        name = t.get("name", "?")
        fn = t.get("fn")
        params = t.get("params") or {}
        if not callable(fn):
            rows.append((name, "NO_FN", "в реестре нет вызываемой функции", ""))
            continue
        req, has_kw, err = sig_of(fn)
        if err:
            rows.append((name, "UNKNOWN", err, ""))
            continue
        req = [r for r in req if r not in ("self", "kw")]
        declared = set(params.keys())
        lie = sorted(declared - set(req) - {"_", "kw"})
        missing_decl = sorted(set(req) - declared)
        if not req and not missing_decl:
            verdict = "OK"
        elif has_kw:
            verdict = "OK (**kw спасает)"
        elif missing_decl:
            verdict = "NO_PARAMS: обязательные %s не объявлены" % ",".join(missing_decl)
        elif lie:
            verdict = "PARAM_LIE: в params есть %s, в сигнатуре нет" % ",".join(lie)
        else:
            verdict = "OK"
        note = ""
        if not has_kw and req:
            note = "обязательные: %s" % ",".join(req)
        rows.append((name, verdict, note, ",".join(declared)))

    bad = [r for r in rows if not r[1].startswith("OK")]
    print("=" * 100)
    print("АУДИТ ИНСТРУМЕНТОВ: %d всего, дефектных: %d" % (len(rows), len(bad)))
    print("=" * 100)
    for name, verdict, note, decl in sorted(rows, key=lambda r: (r[1].startswith("OK"), r[0])):
        mark = "  " if verdict.startswith("OK") else "!!"
        print("%s %-26s %s" % (mark, name, verdict))
        if note:
            print("      %s" % note)
        if decl:
            print("      params: %s" % decl)
    return 0


if __name__ == "__main__":
    sys.exit(main())