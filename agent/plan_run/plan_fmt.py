# -*- coding: utf-8 -*-
r"""plan_fmt.py - ЕДИНЫЙ ФОРМАТ ПЛАНА `plan.json` (волна 8, этап 6 плана). Класс Ж.

Смысл: до сих пор планы живут ВНУТРИ инструментов (`batch_params\plan.py`,
`rename_preview`, `purge_preview`). Волна 8 даёт ОДИН формат, в который любой
писающий механизм должен уметь вылиться: шаг · что · где · риск · как откатить.

ФОРМАТ (версия 1):
    {
      "plan_version": 1,
      "kind": "batch_params",          # откуда план
      "title": "...",
      "generated": "2026-10-03 21:00:00",
      "steps": [
        {"n": 1,                      # номер шага, сквозной
         "what": "set_param",         # ЧТО делаем (имя операции)
         "where": "D:\\...\\x.prt",   # ГДЕ (полный путь цели)
         "target": "x.prt",           # имя цели без папки
         "args": {"param": "GROUP", "value": "std"},   # аргументы операции
         "risk": "write",             # РИСК: write | read | destructive
         "rollback": "копия модели до записи: <путь>", # КАК ОТКАТИТЬ
         "verdict": "change",         # что показала разведка
         "old": "was",                # прежнее значение (если умеем)
         "note": ""}
      ],
      "counts": {"write": 1, "read": 0},
      "total": 1
    }

ЗАКОН ФОРМАТА (нарушение = битый план):
1. `plan_version` обязателен и равен 1 (PLAN_VERSION). Неизвестная версия - отказ.
2. `steps` - список; каждый шаг обязан иметь `what` и `where`.
3. `risk` из закрытого списка. Неизвестный риск - отказ: шаг без понятного риска
   опаснее отсутствующего шага.
4. `rollback` обязателен: шаг, который нечем откатить, писать нельзя.

ПРИЁМКА ЧУЖОГО ПЛАНА: `from_batch_params()` переводит уже построенный план
`batch_params` в единый вид. Спека волны 8 прямо называет этот план первым
носителем - изобретать второй формат нельзя.
"""
import io
import json
import sys
import time
from pathlib import Path

PLAN_VERSION = 1
RISKS = ("read", "write", "destructive")
MAX_STEPS = 5000        # предохранитель: план длиннее - это не план, а дамп


def make_step(n, what, where, args=None, risk="read", rollback="", verdict="",
              target="", old="", note=""):
    """Собрать шаг единого формата."""
    return {"n": int(n), "what": str(what), "where": str(where or "").strip(),
            "target": str(target or Path(str(where or "")).name),
            "args": dict(args or {}), "risk": str(risk),
            "rollback": str(rollback), "verdict": str(verdict or ""),
            "old": str(old), "note": str(note)}


def validate(plan):
    """Проверить план. Возвращает (ok, список ошибок)."""
    errs = []
    if not isinstance(plan, dict):
        return False, ["план - не объект (а %s)" % type(plan).__name__]
    if plan.get("plan_version") != PLAN_VERSION:
        errs.append("plan_version должен быть %d, а стоит %r"
                    % (PLAN_VERSION, plan.get("plan_version")))
    steps = plan.get("steps")
    if not isinstance(steps, list):
        errs.append("steps должен быть списком, а стоит %s" % type(steps).__name__)
        return False, errs
    if len(steps) > MAX_STEPS:
        errs.append("шагов %d больше предохранителя %d - это не план"
                    % (len(steps), MAX_STEPS))
    for i, s in enumerate(steps):
        tag = "шаг %d" % (i + 1)
        if not isinstance(s, dict):
            errs.append("%s: не объект" % tag)
            continue
        if not s.get("what"):
            errs.append("%s: нет поля what (ЧТО делать)" % tag)
        if not s.get("where"):
            errs.append("%s: нет поля where (ГДЕ)" % tag)
        if s.get("risk") not in RISKS:
            errs.append("%s: риск %r не из списка %s" % (tag, s.get("risk"), list(RISKS)))
        if not s.get("rollback"):
            errs.append("%s: нет поля rollback (КАК ОТКАТИТЬ)" % tag)
    return (not errs), errs


def from_batch_params(bp):
    r"""Перевести план `batch_params\plan.py` в единый формат.

    СООТВЕТСТВИЕ ПОЛЕЙ (живой факт волн 7-8):
        file -> where, name -> target, param/value -> args,
        verdict change/miss -> risk write, same -> read (не пишет),
        read_fail -> риск read + note (шаг всё равно НЕ пишет).
    rollback: для write - копия модели до записи (доказанный путь apply.py),
              для read - «шаг не пишет», откатывать нечего.
    """
    steps = []
    for i, s in enumerate(bp.get("steps", []), 1):
        verdict = str(s.get("verdict", ""))
        if verdict == "read_fail":
            risk, rollback = "read", "шаг не пишет (файл не читается)"
        elif verdict == "same":
            risk, rollback = "read", "шаг не пишет: значение уже совпадает"
        else:
            risk = "write"
            rollback = "копия модели до записи: %s" % str(s.get("file", "")).strip()
        steps.append(make_step(
            n=i, what="set_param", where=s.get("file"),
            args={"param": s.get("param"), "value": s.get("value")},
            risk=risk, rollback=rollback, verdict=verdict,
            target=s.get("name"), old=s.get("old"), note=s.get("note", "")))
    counts = {}
    for s in steps:
        counts[s["risk"]] = counts.get(s["risk"], 0) + 1
    return {"plan_version": PLAN_VERSION, "kind": "batch_params",
            "title": "План пакетных параметров: %s"
                     % ", ".join("%s=%s" % (k, v) for k, v in bp.get("params", [])),
            "generated": bp.get("generated") or time.strftime("%Y-%m-%d %H:%M:%S"),
            "source": bp.get("root", ""),
            "steps": steps, "counts": counts, "total": len(steps)}


def save_plan(plan, out_dir):
    """Записать `plan.json` в папку журналов планов. Возвращает путь файла."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / ("plan_%s.json" % time.strftime("%Y-%m-%d_%H%M%S"))
    p.write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    return str(p)


def load_plan(path):
    """Прочитать и ПРОВЕРИТЬ план. Возвращает (plan, ok, ошибки)."""
    p = Path(path)
    if not p.exists():
        return None, False, ["файла плана нет: %s" % p]
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        return None, False, ["план не читается как json: %s" % e]
    ok, errs = validate(data)
    return data, ok, errs


def brief(plan, limit=20):
    """Короткая сводка плана для человека: риски, сколько шагов, первые шаги."""
    counts = plan.get("counts") or {}
    steps = plan.get("steps", [])
    out = ["ПЛАН %s v%s: шагов %d (write %d · read %d · destructive %d)"
           % (plan.get("kind", "?"), plan.get("plan_version"), len(steps),
              counts.get("write", 0), counts.get("read", 0),
              counts.get("destructive", 0)),
           "заголовок: %s" % plan.get("title", "")]
    for s in steps[:limit]:
        out.append("  %3d %-10s %-12s %s %s"
                   % (s.get("n", 0), s.get("risk", "?"), s.get("what", "?"),
                      Path(s.get("where", "")).name, s.get("note", "")))
    if len(steps) > limit:
        out.append("  … ещё %d" % (len(steps) - limit))
    return "\n".join(out)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if len(sys.argv) < 2:
        print("plan_fmt.py <plan.json>  - показать и проверить план")
        sys.exit(2)
    pl, ok, errs = load_plan(sys.argv[1])
    if not ok:
        print("ПЛАН НЕ ПРОШЁЛ ПРОВЕРКУ:")
        for e in errs:
            print("  - %s" % e)
        sys.exit(2)
    print(brief(pl, limit=50))
    sys.exit(0)
