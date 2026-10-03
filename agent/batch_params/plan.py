# -*- coding: utf-8 -*-
r"""plan.py - ПЛАН ПАКЕТНЫХ ПАРАМЕТРОВ БЕЗ CREO (волна 7, этап 5 плана). Класс Ж.

Смысл: пакетная правка параметров не должна начинаться «сразу». Сначала строится ПЛАН -
список моделей и параметров, что изменится, что нет и почему - и человек его видит ДО
записи. План строится ЧИТАНИЕМ ФАЙЛОВ (creo_read, класс Р): Creo не нужен, значит план
можно построить и показать, даже когда CREOSON мёртв.

ЧТО ПЛАН НЕ ДЕЛАЕТ: ничего не пишет. Запись - отдельный шаг (apply.py) и только по явной
команде человека.

ЖИВАЯ ПРОВЕРКА 03.10.2026: модели читаются из
`Z:\PTC\CREO-START\Libraries\Библиотека_стандартных_изделий` (боевой источник, только чтение).

Запуск: plan.py [папка] --param ИМЯ=ЗНАЧЕНИЕ [--param ...]
"""
import io
import json
import os
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AGENT = _HERE.parent
for _p in (_AGENT, _HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import creo_read as CR   # noqa: E402

LOG_DIR = Path(r"D:\AI\log\batch_params")
REPORT_DIR = Path(r"D:\AI\log\reports")
SETTINGS = _AGENT / "data" / "batch_params_settings.json"

# Боевая библиотека стандартных изделий - откуда берём модели для плана (только чтение).
DEFAULT_ROOT = Path(r"Z:\PTC\CREO-START\Libraries\Библиотека_стандартных_изделий")
MODEL_EXT = (".prt", ".asm")
MAX_FILES = 300          # предохранитель: план не должен уходить в бесконечный обход


def parse_params(items):
    """['A=B', 'C=D'] -> [('A','B'), ('C','D')]. Плохое значение - исключение с текстом."""
    out = []
    for it in items or []:
        s = str(it)
        if "=" not in s:
            raise ValueError("параметр без «=»: %s (нужно ИМЯ=ЗНАЧЕНИЕ)" % s)
        k, v = s.split("=", 1)
        k, v = k.strip(), v.strip()
        if not k:
            raise ValueError("пустое имя параметра в «%s»" % s)
        out.append((k, v))
    return out


def find_models(root=None, limit=MAX_FILES):
    """Файлы моделей (.prt/.asm) под корнем.

    os.walk со сверкой вниз: в доме имена в нижнем регистре (`g11074.prt.1`), а
    `pathlib.rglob` сравнивает регистр строго - это грабля волн 3-6."""
    root = Path(root or DEFAULT_ROOT)
    if not root.exists():
        return [], str(root)
    out = []
    for dirpath, dirnames, filenames in os.walk(str(root)):
        for f in filenames:
            low = f.lower()
            if low.endswith(MODEL_EXT) or low.endswith(".prt.1") \
                    or low.endswith(".asm.1"):
                out.append(os.path.join(dirpath, f))
                if len(out) >= limit:
                    return sorted(out), None
    return sorted(out), None


def plan_for_file(path, params):
    """Что изменится в одной модели: шаги с вердиктом (change/same/miss/read_fail)."""
    steps = []
    try:
        raw = CR.read(path)
        toc = CR.parse_toc(raw)
        cur = CR.params(raw, toc) or {}
    except Exception as e:
        return [{"file": path, "name": Path(path).name, "param": k, "value": v,
                 "old": "", "verdict": "read_fail",
                 "note": "файл не читается: %s" % e} for k, v in params]
    if not cur:
        return [{"file": path, "name": Path(path).name, "param": k, "value": v,
                 "old": "", "verdict": "read_fail",
                 "note": "параметры не извлечены (нет секции NeuPrtSld)"} for k, v in params]
    for k, v in params:
        old = cur.get(k)
        if old is None:
            verdict, note = "miss", "параметра в модели нет - будет создан"
        elif str(old).strip() == v:
            verdict, note = "same", "уже равно - изменений не будет"
        else:
            verdict, note = "change", "было: %s" % str(old)[:60]
        steps.append({"file": path, "name": Path(path).name, "param": k, "value": v,
                      "old": "" if old is None else str(old),
                      "verdict": verdict, "note": note})
    return steps
def build_plan(root=None, params=None, limit=MAX_FILES, only=None):
    """План целиком: файлы × параметры. Ничего не пишет на диске модели.

    `only` — явный список файлов (живая проба волны 8 бьёт по одной копии, а папка
    пробы может лежать рядом с чужими моделями: без этого в плане появлялись лишние
    write-шаги, и щит отказывал RC 4 «активна ДРУГАЯ модель»)."""
    try:
        params = parse_params(params)
    except ValueError as e:
        return {"error": str(e), "steps": [], "files": []}
    if not params:
        return {"error": "не задано ни одного параметра (нужно --param ИМЯ=ЗНАЧЕНИЕ)",
                "steps": [], "files": []}
    files, missing = (list(only), None) if only else find_models(root, limit)
    steps = []
    for f in files:
        steps += plan_for_file(f, params)
    per = {}
    for s in steps:
        per[s["verdict"]] = per.get(s["verdict"], 0) + 1
    return {"root": str(root or DEFAULT_ROOT), "missing": missing,
            "files": files, "params": params, "steps": steps,
            "counts": per, "total": len(steps),
            "will_change": per.get("change", 0) + per.get("miss", 0),
            "generated": time.strftime("%Y-%m-%d %H:%M:%S")}


def write_plan(plan):
    """План на диск: md для человека + JSON для apply.py. Возвращает (md, json).

    Правка 03.10.2026: план-файл пишется в папку программы `log\\batch_params`, а НЕ в
    `log\\reports` — там по закону дома лежат только `REPORT_<задача>_<исполнитель>_<дата>.md`
    (проверка `dev\\culture_check.py`: «чужих файлов 17» — все были PLAN_batch_params_*.md).
    """
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    rp = LOG_DIR / ("PLAN_batch_params_%s.md" % stamp)
    jp = LOG_DIR / ("plan_batch_params_%s.json" % stamp)
    out = ["# ПЛАН ПАКЕТНЫХ ПАРАМЕТРОВ (ничего ещё НЕ записано)", "",
           "Собран: **%s** · корень: `%s` · моделей: **%d** · шагов: **%d**"
           % (plan.get("generated"), plan.get("root"), len(plan.get("files", [])),
              plan.get("total", 0)), "",
           "Параметры: %s" % ", ".join("%s=%s" % (k, v) for k, v in plan.get("params", [])),
           "", "## Сводка по вердиктам", "",
           "| Вердикт | Сколько |", "|---|---|"]
    names = {"change": "изменится", "same": "уже равно (пропуск)",
             "miss": "параметра нет (создастся)", "read_fail": "не прочитано"}
    for k in ("change", "same", "miss", "read_fail"):
        if k in plan.get("counts", {}):
            out.append("| %s | %d |" % (names[k], plan["counts"][k]))
    out += ["", "## Шаги (первые 200)", "",
            "| Модель | Параметр | Новое | Старое | Вердикт |", "|---|---|---|---|---|"]
    for s in plan.get("steps", [])[:200]:
        out.append("| %s | %s | %s | %s | %s |"
                   % (s["name"], s["param"], s["value"], s["old"][:30],
                      names.get(s["verdict"], s["verdict"])))
    if plan.get("total", 0) > 200:
        out.append("| … ещё %d | | | | |" % (plan["total"] - 200))
    out += ["", "## ЧТО ЭТО НЕ ДЕЛАЕТ",
            "План НИЧЕГО не пишет в модель. Запись - отдельной командой под щитом согласования,",
            "и только на копии. Боевые файлы не трогаются."]
    rp.write_text("\n".join(out), encoding="utf-8")
    jp.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    return str(rp), str(jp)


def main(argv):
    root = None
    params = []
    for a in argv[1:]:
        if a.startswith("--param"):
            params.append(a.split("=", 1)[1] if "=" in a else a[7:].strip())
        elif not a.startswith("-"):
            root = a
    plan = build_plan(root, params)
    if plan.get("error"):
        print("ОШИБКА ПЛАНА: %s" % plan["error"])
        return 2
    print("ПЛАН ПАКЕТНЫХ ПАРАМЕТРОВ (записи ещё нет)")
    print("  корень: %s" % plan["root"])
    print("  моделей: %d, шагов: %d" % (len(plan["files"]), plan["total"]))
    print("  параметры: %s" % ", ".join("%s=%s" % (k, v) for k, v in plan["params"]))
    print("  сводка: %s" % plan["counts"])
    print("  изменится/создастся: %d" % plan["will_change"])
    rp, jp = write_plan(plan)
    print("-" * 78)
    print("отчёт: %s" % rp)
    print("JSON:   %s" % jp)
    print("ЗАПИСЬ НЕ ВЫПОЛНЯЛАСЬ. Прогон - отдельной командой и только на копии.")
    return 0


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv))