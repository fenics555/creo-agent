# -*- coding: utf-8 -*-
r"""ПРИЁМКА ВОЛНЫ 8 - планы задач `plan.json` -> `plan_run` (этап 6 плана).
Запуск: Set-Location D:\AI\tools\agent; python -X utf8 dev\vol8_check.py

Класс Ж. Ключевое: живая запись не проверяется «на успех» - стек погашен по слову
владельца, и приёмка требует ЧЕСТНЫЙ ОТКАЗ (RC 2), а не «прогон успешен».
Приёмка п.6 спеки: если `parametric.exe` не найден - живая запись не объявляется
проверенной, это пишется в вердикт строкой.
"""
import io
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
HERE = Path(__file__).resolve().parent
AGENT = HERE.parent
for _p in (AGENT, AGENT / "plan_run", AGENT / "batch_params"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

fail = []
t0 = time.time()


def ok(name, cond, detail=""):
    d = detail if isinstance(detail, str) else str(detail)
    print(("OK   " if cond else "FAIL ") + name + ((" | " + d) if d else ""))
    if not cond:
        fail.append(name)


import plan as BPP                    # noqa: E402
import plan_fmt as F                  # noqa: E402
import runner as R                    # noqa: E402

ZAKI = r"Z:\PTC\CREO-START\Libraries\Библиотека_стандартных_изделий\Гайки"

# 1. СОСТАВ инструмента (закон шаблона: три руки + контракт + ридми)
files = ["plan_fmt.py", "runner.py", "gui.py", "tool.json", "README.md",
         "run.bat", "plan_run_gui.bat"]
missing = [f for f in files if not (AGENT / "plan_run" / f).exists()]
ok("состав plan_run на месте", not missing, "нет: %s" % missing)
ok("инструменты агента объявлены",
   (AGENT / "plan_run_tools.py").exists())

# 2. ПЛАН batch_params выражается ЕДИНЫМ форматом (спека п.2)
ok("боевая папка с моделями есть", Path(ZAKI).exists(), ZAKI)
bp = BPP.build_plan(ZAKI, ["GROUP=std"], limit=60)
ok("план batch_params построен (без CREOSON)", not bp.get("error") and bp.get("total", 0) > 0,
   "моделей %d, шагов %d" % (len(bp.get("files", [])), bp.get("total", 0)))
plan = F.from_batch_params(bp)
ok("переведён в единый формат v%s" % F.PLAN_VERSION, plan["plan_version"] == F.PLAN_VERSION)
good, errs = F.validate(plan)
ok("план прошёл проверку формата", good, "; ".join(errs[:3]))
ok("у каждого шага есть what/where/rollback",
   all(s.get("what") and s.get("where") and s.get("rollback") for s in plan["steps"]),
   "шагов: %d" % len(plan["steps"]))
ok("риск назначен по вердикту разведки",
   plan["counts"].get("write", 0) > 0 and set(plan["counts"]) <= set(F.RISKS),
   "сводка рисков: %s" % plan["counts"])

# 3. БИТЫЙ план отвергается, а не исполняется
broken = dict(plan)
broken["plan_version"] = 99
ok("чужая версия плана отвергнута", not F.validate(broken)[0])
bad_step = F.make_step(1, "set_param", "x.prt", risk="write", rollback="")
ok("шаг без rollback отвергнут", not F.validate(
    {"plan_version": F.PLAN_VERSION, "steps": [bad_step]})[0])
ok("шаг без where отвергнут", not F.validate(
    {"plan_version": F.PLAN_VERSION,
     "steps": [F.make_step(1, "set_param", "", risk="write", rollback="копия")]})[0])

# 4. ФАЙЛ ПЛАНА пишется и читается обратно (спека п.1)
path = F.save_plan(plan, R.LOG_DIR)
back, ok2, errs2 = F.load_plan(path)
ok("plan.json записан и прочитан", ok2 and back.get("total") == plan["total"],
   "%s (шагов %d)" % (path, back.get("total", 0) if back else 0))

# 5. СОГЛАСИЕ и СТОП (спека п.3)
res = R.run_plan(plan, approve=False)
ok("без согласия RC 3 и шаги не начаты",
   res["rc"] == 3 and res.get("done", 0) == 0, res["detail"])
res = R.run_plan(plan, approve=True, dry_run=True)
ok("проба без записи RC 0", res["rc"] == 0 and res.get("done", 0) == 0, res["detail"])
R.STOP["flag"] = True
res = R.run_plan(plan, approve=True)
ok("СТОП до цикла - шаги не начинались",
   res["rc"] == 0 and res.get("stopped") and res.get("done", 0) == 0, res["detail"])
R.STOP["flag"] = False
res = R.run_plan({"plan_version": F.PLAN_VERSION, "steps": []}, approve=True)
ok("пустой план - нечего выполнять", res["rc"] == 0 and "нечего" in res["detail"],
   res["detail"])

# 6. ЧЕСТНЫЙ ОТКАЗ без CREOSON (спека п.3 и п.6) + признак живости стека
import apply as BA   # noqa: E402

ready, why = BA.creoson_ready()
print("стек: %s" % ("готов - %s" % why if ready else "НЕ ГОТОВ - %s" % why))
res = R.run_plan(plan, approve=True)
if ready:
    print("ЖИВАЯ ЗАПИСЬ не проверялась этой приёмкой (стек готов, но запись не велась)")
else:
    ok("без CREOSON честный отказ RC 2, а не «успех»",
       res["rc"] == 2 and res.get("stack_ready") is False, res["detail"])

# 7. ЖУРНАЛ шагов пишется в log\plans\ (спека п.4)
jl = R.LOG_DIR / "plan_run.log"
ok("журнал шагов создан в log\\plans", jl.exists(), str(jl))

# 8. ИНСТРУМЕНТЫ АГЕНТА отвечают
import plan_run_tools as PT   # noqa: E402

names = [t["name"] for t in PT.TOOLS]
ok("объявлены plan_build/plan_run/plan_report",
   set(["plan_build", "plan_run", "plan_report"]) <= set(names), str(names))
rep = PT.tool_plan_report(limit=5)
ok("plan_report отвечает", isinstance(rep, str) and len(rep) > 0, rep.splitlines()[0])
build = PT.tool_plan_build(param="GROUP=std", limit=20)
ok("plan_build строит единый план", "файл плана" in build, build.splitlines()[0])
run_noap = PT.tool_plan_run(plan_json=path, approve=0, dry_run=1)
ok("инструмент plan_run без согласия отказывает", "RC 3" in run_noap, run_noap)

# 9. РЕГРЕСС волн 1-7 (спека п.5) - полные прогоны в отчёт ноги
print("-" * 74)
print("ВЕРДИКТ: %s · провалов %d · %.2f с"
      % ("ВСЁ ПРОШЛО" if not fail else "ЕСТЬ ПРОВАЛЫ", len(fail), time.time() - t0))
if fail:
    print("провалы: %s" % ", ".join(fail))
sys.exit(0 if not fail else 1)
