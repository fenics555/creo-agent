# -*- coding: utf-8 -*-
r"""plan_run_tools.py - инструменты агента по планам задач (волна 8, класс Ж).

Три инструмента: `plan_build` строит ЕДИНЫЙ plan.json из плана batch_params,
`plan_run` исполняет его (требует согласия), `plan_report` отдаёт журнал шагов.
По умолчанию НИЧЕГО не пишет: без approve=1 шаги не начинаются.
"""
import sys
from pathlib import Path

AGENT = Path(__file__).resolve().parent
for _p in (AGENT / "plan_run", AGENT / "batch_params"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

R_LOG_DIR = Path(r"D:\AI\log\plans")   # папка планов и журнала шагов


def tool_plan_build(root="", param="", limit=300, as_json=False, **kw):
    """Построить ЕДИНЫЙ план `plan.json` из плана batch_params (без записи, без Creo).

    root  — папка с моделями; пусто = боевая библиотека стандартных изделий.
    param — параметры через `;`: `GROUP=std;МАССА=0.1`.
    План сохраняется в `log\plans\` и возвращает путь и сводку рисков."""
    try:
        import plan as BPP
        import plan_fmt as F
    except Exception as e:
        return "движок плана недоступен: %s" % e
    params = [x for x in str(param or "").split(";") if x.strip()]
    if not params:
        return "нужен параметр: param=ИМЯ=ЗНАЧЕНИЕ (несколько — через «;»)"
    bp = BPP.build_plan(root or None, params, int(limit or 300))
    if bp.get("error"):
        return "ошибка плана: %s" % bp["error"]
    plan = F.from_batch_params(bp)
    ok, errs = F.validate(plan)
    if not ok:
        return "план не прошёл проверку формата: %s" % "; ".join(errs[:3])
    path = F.save_plan(plan, R_LOG_DIR)
    if as_json:
        return plan
    return "%s\n%s\nфайл плана: %s\nЗАПИСИ НЕ БЫЛО. Исполнение - отдельным шагом с согласием."\
        % (F.brief(plan, limit=15),
           "шагов с риском write: %d" % plan["counts"].get("write", 0), path)


def tool_plan_run(plan_json="", approve=0, dry_run=1, **kw):
    """Исполнить план `plan.json` по шагам (класс Ж: пишет в Creo).

    Без approve=1 шаги НЕ начинаются (RC 3). При мёртвом CREOSON - честный отказ RC 2.
    По умолчанию dry_run=1: сначала показать, что будет, без записи."""
    try:
        import runner as R
    except Exception as e:
        return "движок plan_run недоступен: %s" % e
    if not plan_json:
        return "нужен файл плана (plan_json): сначала plan_build, потом plan_run"
    plan, ok, errs = R.F.load_plan(plan_json)
    if not ok:
        return "план не прошёл проверку: %s" % "; ".join(errs[:3])
    res = R.run_plan(plan, approve=bool(approve), dry_run=bool(dry_run))
    return ("ИСПОЛНЕНИЕ ПЛАНА: RC %s - %s (вышло: %s)"
            % (res.get("rc"), res.get("detail", ""), res.get("done", 0)))


def tool_plan_report(limit=40, **kw):
    """Журнал шагов `plan_run`: последние строки из `log\plans\plan_run.log`."""
    try:
        import runner as R
    except Exception as e:
        return "движок plan_run недоступен: %s" % e
    p = R.LOG_DIR / "plan_run.log"
    if not p.exists():
        return "журнала шагов ещё нет: %s" % p
    try:
        lines = p.read_text(encoding="utf-8").splitlines()[-int(limit or 40):]
    except Exception as e:
        return "журнал не читается: %s" % e
    return "ЖУРНАЛ ШАГОВ (%d строк):\n%s" % (len(lines), "\n".join(lines))


TOOLS = [
    {"name": "plan_build",
     "desc": "Построить единый план plan.json из плана пакетных параметров "
             "(без записи, без Creo): шаги с риском и откатом",
     "params": {"root": "папка с моделями", "param": "GROUP=std;МАССА=0.1",
                "limit": "сколько файлов", "as_json": "для витрины"},
     "fn": tool_plan_build, "kind": "check", "group": "Creo",
     "source": "plan_run_tools", "needs_creo": False},
    {"name": "plan_run",
     "desc": "Исполнить план plan.json по шагам (класс Ж, пишет в Creo): нужен approve, "
             "при мёртвом CREOSON честный отказ, при неверной активной модели RC 4",
     "params": {"plan_json": "файл плана", "approve": "0/1 - согласие",
                "dry_run": "1 - без записи, показать что будет"},
     "fn": tool_plan_run, "kind": "act", "group": "Creo",
     "source": "plan_run_tools", "needs_creo": True},
    {"name": "plan_report",
     "desc": "Журнал шагов исполнения плана: где вышло, где нет, где остановились",
     "params": {"limit": "сколько последних строк"},
     "fn": tool_plan_report, "kind": "check", "group": "Creo",
     "source": "plan_run_tools", "needs_creo": False},
]
