# -*- coding: utf-8 -*-
r"""runner.py - ИСПОЛНЕНИЕ ПЛАНА `plan.json` ПО ШАГАМ (волна 8, класс Ж).

ПРАВИЛА ЖЕЛЕЗА ДЛЯ ЭТОГО ФАЙЛА:
1. Согласие обязательно: без `approve=1` шаги не начинаются, RC 3.
2. СТОП проверяется ПЕРВЫМ: нажат до цикла - не начинаем ВООБЩЕ (живой факт волны 7:
   проверка СТОП внутри цикла не срабатывала при мёртвом CREOSON, кнопка выглядела
   мёртвой).
3. План проверяется ДО исполнения (`plan_fmt.validate`): битый план не исполняем.
4. Читающие шаги (risk=read) пишут в журнал и идут дальше всегда.
5. Пишущие шаги идут через ДОКАЗАННЫЕ механизмы дома (`batch_params\apply.py`).
   Своего вызова CREOSON здесь нет и не изобретается.
6. Нет CREOSON - честный отказ RC 2, а НЕ «прогон успешен».
7. Щит `ensure_active` (перенос из apply.py) сверяет активную модель ПО ПОЛНОМУ
   ПУТИ - по имени не годится (инцидент 03.10.2026).

Запуск: runner.py <plan.json> [--approve] [--dry_run]
"""
import io
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AGENT = _HERE.parent
for _p in (_AGENT, _HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import plan_fmt as F   # noqa: E402

LOG_DIR = Path(r"D:\AI\log\plans")
REPORT_DIR = Path(r"D:\AI\log\reports")

STOP = {"flag": False}      # кнопка СТОП в окне ставит True


def log_line(text):
    r"""Строка журнала шагов: на диск и наружу. Журнал - в log\plans\, как требует спека."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with (LOG_DIR / "plan_run.log").open("a", encoding="utf-8") as f:
        f.write("%s  %s\n" % (stamp, text))
    return text


def _steps_to_write(plan):
    """Только пишущие шаги: read-шаги нечего выполнять, они для отчёта."""
    return [s for s in plan.get("steps", []) if s.get("risk") == "write"]


def run_plan(plan, approve=False, dry_run=False, on_log=None):
    """Исполнить план. Возвращает словарь с rc/detail/results.

    RC: 0 — выполнено (или проба) · 1 — часть шагов не вышла · 2 — нет CREOSON/битый
        план · 3 — нет согласия · 4 — щит: активна не та модель.
    """
    log = on_log or (lambda s: None)

    # 1. СТОП первым — до всего.
    if STOP["flag"]:
        return {"rc": 0, "detail": "СТОП нажат до начала: шаги не начинались",
                "done": 0, "stopped": True}

    # 2. План проверяем ДО исполнения.
    ok, errs = F.validate(plan)
    if not ok:
        return {"rc": 2, "detail": "план не прошёл проверку: %s" % "; ".join(errs[:3]),
                "done": 0, "stopped": False}

    writes = _steps_to_write(plan)
    reads = [s for s in plan.get("steps", []) if s.get("risk") == "read"]
    if not writes:
        return {"rc": 0, "detail": "нечего выполнять: в плане нет пишущих шагов "
                                   "(read %d)" % len(reads), "done": 0}

    # 3. Согласие.
    if not approve:
        return {"rc": 3, "detail": "НЕ СОГЛАСОВАНО: нужен approve=1 (шаги не начались)",
                "planned": len(writes), "planned_reads": len(reads)}

    # 4. Проба без записи.
    if dry_run:
        log_line("ПРОБА plan_run: %d write-шагов, записи не было" % len(writes))
        return {"rc": 0, "detail": "пробный прогон (dry_run): записи не было",
                "planned": len(writes), "done": 0, "dry_run": True}

    # 5. Стек нужен для записи — честно проверяем ДО цикла.
    try:
        if str(_AGENT / "batch_params") not in sys.path:
            sys.path.insert(0, str(_AGENT / "batch_params"))
        import apply as BA   # доказанный путь: creoson_ready + ensure_active + set_param
    except Exception as e:
        return {"rc": 2, "detail": "движок batch_params\\apply недоступен: %s" % e,
                "planned": len(writes), "done": 0}

    ready, why = BA.creoson_ready()
    if not ready:
        log_line("ОТКАЗ: %s" % why)
        return {"rc": 2, "detail": "%s - запись НЕ выполнена" % why,
                "planned": len(writes), "stack_ready": False, "done": 0}

    # 6. Цикл по пишущим шагам.
    results = []
    for i, s in enumerate(writes):
        if STOP["flag"]:
            log_line("СТОП на шаге %d из %d" % (i, len(writes)))
            return {"rc": 0, "detail": "остановлено СТОП на шаге %d" % i,
                    "done": sum(1 for r in results if r["ok"]), "results": results,
                    "stopped": True}
        # ЩИТ «ТОЛЬКО КОПИЯ»: активная модель обязана совпадать по ПОЛНОМУ ПУТИ.
        same, why_active = BA.ensure_active(s.get("where", ""))
        if not same:
            log_line("СТОП-ЩИТ: %s" % why_active)
            results.append({"n": s.get("n"), "file": s.get("target"),
                            "ok": False, "note": why_active})
            return {"rc": 4, "detail": why_active,
                    "done": sum(1 for r in results if r["ok"]), "results": results,
                    "stopped": True, "shield": "wrong_active_model"}
        # Шаг kind=batch_params: what=set_param, args={param, value}.
        args = s.get("args", {}) or {}
        ok_step, note = BA.set_param(Path(s.get("where", "")).stem,
                                     args.get("param"), args.get("value"))
        results.append({"n": s.get("n"), "file": s.get("target"),
                        "param": args.get("param"), "ok": ok_step, "note": note})
        log_line("%s шаг %s %s %s=%s" % ("OK" if ok_step else "FAIL", s.get("n"),
                                         s.get("target"), args.get("param"),
                                         args.get("value")))
        time.sleep(0.05)   # не долбим CREOSON

    done = sum(1 for r in results if r["ok"])
    return {"rc": 0 if done == len(results) else 1,
            "detail": "вышло: %d из %d" % (done, len(results)),
            "done": done, "results": results, "stopped": False}


def write_report(res, plan=None):
    """Журнал шагов в отчёт: где вышло, где нет, где остановились."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    rp = REPORT_DIR / ("REPORT_plan_run_%s.md" % time.strftime("%Y-%m-%d_%H%M%S"))
    out = ["# ОТЧЁТ ИСПОЛНЕНИЯ ПЛАНА (plan_run)", "",
           "Итог: **%s** (RC %s) · %s" % ("ОК" if res.get("rc") == 0 else "НЕ ОК",
                                          res.get("rc", "?"), res.get("detail", "")), ""]
    if plan:
        out += ["План: %s v%s · шагов %d" % (plan.get("kind"), plan.get("plan_version"),
                                             plan.get("total", 0)), ""]
    if res.get("results"):
        out += ["| Шаг | Модель | Параметр | Вердикт | Что |", "|---|---|---|---|---|"]
        for r in res["results"]:
            out.append("| %s | %s | %s | %s | %s |"
                       % (r.get("n", ""), r.get("file", ""), r.get("param", ""),
                          "ОК" if r.get("ok") else "ПРОВАЛ",
                          str(r.get("note", "")).replace("|", "/")))
    out += ["", "Журнал шагов: %s" % (LOG_DIR / "plan_run.log"),
            "Боевые файлы не трогаются: write-шаг идёт только на цель плана,",
            "щит сверяет активную модель по полному пути."]
    rp.write_text("\n".join(out), encoding="utf-8")
    return str(rp)


def main(argv):
    approve = "--approve" in argv or "--approve=1" in argv
    dry = "--dry_run" in argv
    json_path = next((a for a in argv[1:] if a.endswith(".json")), None)
    if not json_path:
        print("нужен файл плана: plan_run\\runner.py <plan.json> [--approve] [--dry_run]")
        return 2
    plan, ok, errs = F.load_plan(json_path)
    if not ok:
        print("ПЛАН НЕ ПРОШЁЛ ПРОВЕРКУ:")
        for e in errs:
            print("  - %s" % e)
        return 2
    print(F.brief(plan, limit=15))
    res = run_plan(plan, approve=approve, dry_run=dry, on_log=lambda s: print("  " + s))
    print("ИСПОЛНЕНИЕ ПЛАНА: RC %s - %s" % (res.get("rc"), res.get("detail", "")))
    if res.get("results"):
        print("отчёт: %s" % write_report(res, plan))
    return res.get("rc", 0)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv))
