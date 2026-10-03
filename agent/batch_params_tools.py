# -*- coding: utf-8 -*-
"""batch_params_tools.py - инструменты агента по пакетным параметрам (волна 7, класс Ж).

Ключевое свойство: инструмент по умолчанию НЕ пишет. `batch_params_plan` только строит
план (чтение файлов, Creo не нужен), `batch_params_apply` требует approve=1 и честно
отказывает RC 2, если CREOSON мёртв.
"""
import sys
from pathlib import Path

AGENT = Path(__file__).resolve().parent
sys.path.insert(0, str(AGENT / "batch_params"))


def tool_batch_params_plan(root="", param="", limit=300, as_json=False, **kw):
    """Построить ПЛАН пакетной правки параметров (без записи, без Creo).

    root  — папка с моделями; пусто = боевая библиотека стандартных изделий.
    param — параметры через запятую: `GROUP=std;МАССА=0.1` (несколько — `;`).
    Возвращает, что изменится, что уже равно и что параметра нет."""
    try:
        import plan as P
    except Exception as e:
        return "движок batch_params\\plan недоступен: %s" % e
    params = [x for x in str(param or "").split(";") if x.strip()]
    pl = P.build_plan(root or None, params, limit=int(limit or 300))
    if pl.get("error"):
        return "ошибка плана: %s" % pl["error"]
    if as_json:
        return pl
    lines = ["ПЛАН пакетных параметров (записи НЕ было)",
             "корень: %s" % pl["root"],
             "моделей: %d, шагов: %d" % (len(pl["files"]), pl["total"]),
             "параметры: %s" % ", ".join("%s=%s" % (k, v) for k, v in pl["params"]),
             "сводка: %s" % pl["counts"],
             "изменится/создастся: %d" % pl["will_change"]]
    for s in pl["steps"][:15]:
        if s["verdict"] != "same":
            lines.append("  %-6s %-24s %s -> %s"
                         % (s["verdict"], s["name"][:24], s["param"], s["value"]))
    lines.append("ЧТО ДАЛЬШЕ: запись только отдельной командой с approve и на копии.")
    return "\n".join(lines)


def tool_batch_params_apply(plan_json="", approve=0, dry_run=1, **kw):
    """Применить план пакетных параметров (класс Ж: пишет в Creo).

    Без approve=1 запись НЕ начинается (RC 3). При мёртвом CREOSON - честный отказ RC 2.
    По умолчанию dry_run=1: сначала показывает, что будет, без записи."""
    try:
        import apply as A
    except Exception as e:
        return "движок batch_params\\apply недоступен: %s" % e
    if not plan_json:
        return "нужен файл плана (plan_json): сначала batch_params_plan, потом apply"
    p = Path(plan_json)
    if not p.exists():
        return "файла плана нет: %s" % p
    import json
    plan = json.loads(p.read_text(encoding="utf-8"))
    res = A.apply_plan(plan, approve=bool(approve), dry_run=bool(dry_run))
    return ("ПРИМЕНЕНИЕ ПЛАНА: RC %d - %s (вышло: %s)"
            % (res.get("rc", 0), res.get("detail", ""), res.get("done", 0)))


def tool_feature_rename_plan(name="", pattern="", limit=300, as_json=False, **kw):
    """ПЛАН переименования признаков: что переименуется и во что (без записи).

    Запись идёт только через доказанный путь rename (onlysession + save) и на копии."""
    try:
        import plan as P
    except Exception as e:
        return "движок batch_params\\plan недоступен: %s" % e
    files, missing = P.find_models(name or None, int(limit or 300))
    import re
    try:
        rx = re.compile(pattern)
    except re.error as e:
        return "не разбирается маска «%s»: %s" % (pattern, e)
    hits = []
    for f in files:
        stem = P.CR.stem(Path(f).name)
        if rx.search(stem):
            hits.append({"file": f, "name": Path(f).name, "stem": stem,
                         "new": rx.sub("", stem) or stem + "_NEW"})
    if as_json:
        return {"files": len(files), "hits": hits}
    lines = ["ПЛАН переименования признаков (записи НЕ было)",
             "моделей просмотрено: %d, под маску попали: %d" % (len(files), len(hits))]
    for h in hits[:15]:
        lines.append("  %-26s -> %s" % (h["name"], h["new"]))
    lines.append("Запись - только через rename (onlysession+save) и на копии.")
    return "\n".join(lines)


TOOLS = [
    {"name": "batch_params_plan",
     "desc": "Построить план пакетной правки параметров по моделям (без записи, без Creo): "
             "что изменится, что уже равно, чего нет",
     "params": {"root": "папка с моделями", "param": "GROUP=std;МАССА=0.1",
                "limit": "сколько файлов", "as_json": "для витрины"},
     "fn": tool_batch_params_plan, "kind": "check", "group": "Creo",
     "source": "batch_params_tools", "needs_creo": False},
    {"name": "batch_params_apply",
     "desc": "Применить план пакетных параметров (класс Ж, пишет в Creo): нужен approve, "
             "при мёртвом CREOSON честный отказ",
     "params": {"plan_json": "файл плана", "approve": "0/1 - согласие на запись",
                "dry_run": "1 - без записи, показать что будет"},
     "fn": tool_batch_params_apply, "kind": "act", "group": "Creo",
     "source": "batch_params_tools", "needs_creo": True},
    {"name": "feature_rename_plan",
     "desc": "План переименования признаков по маске (без записи): что переименуется и во что",
     "params": {"name": "папка", "pattern": "регулярное выражение", "limit": "сколько файлов"},
     "fn": tool_feature_rename_plan, "kind": "check", "group": "Creo",
     "source": "batch_params_tools", "needs_creo": False},
]