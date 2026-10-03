# -*- coding: utf-8 -*-
r"""dev\vol8_live.py - ЖИВАЯ ПРОБА ИСПОЛНЕНИЯ ПЛАНА `plan_run` НА КОПИИ (волна 8).

ОТЛИЧИЕ ОТ `dev\vol7_live_apply.py`: там запись проверялась прямым вызовом
`tool_set_param`. Здесь запись идёт ТОЛЬКО через `plan_run\runner.run_plan` -
то есть проверяется сам механизм волны 8 (план -> согласие -> щит -> шаг ->
журнал), а не отдельный вызов.

Правила прогона (класс Ж, инцидент 03.10.2026):
  * модель - ТОЛЬКО копия `D:\AI\PROBA\vol8_copy\vol8_probe.prt` с УНИКАЛЬНЫМ
    именем (коллизия по стену = причина инцидента);
  * `file:open` с `dirname` ОТДЕЛЬНО, иначе файл ищется в рабочей папке;
  * параметр ставится на СВОЁ имя (VOL8_PLAN), боевые параметры не трогаем;
  * проверка результата - ПО ФАЙЛУ на диске, последняя версия `prt.N`;
  * щит `ensure_active` обязан согласиться (иначе RC 4 и запись не идёт);
  * ОТКАТ: удалить параметр, сохранить, проверить по файлу.

Запуск: Set-Location D:\AI\tools\agent; python -X utf8 dev\vol8_live.py
"""
import io
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
for _p in (AGENT, AGENT / "plan_run", AGENT / "batch_params"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

fail = []
COPY_DIR = Path(r"D:\AI\PROBA\vol8_copy")
COPY_MODEL = COPY_DIR / "vol8_probe.prt"     # УНИКАЛЬНОЕ имя — правило волны 7
PARAM = "VOL8_PLAN"
VALUE = "plan_run_2026_10_03"
LOG_DIR = Path(r"D:\AI\log\plans")


def ok(name, cond, detail=""):
    d = detail if isinstance(detail, str) else str(detail)
    print(("OK   " if cond else "FAIL ") + name + ((" | " + d) if d else ""))
    if not cond:
        fail.append(name)


def latest_version(model):
    """Последняя версия модели (prt.N): живой факт 03.10.2026 — при save Creo
    создаёт НОВУЮ версию, базовый файл не меняется."""
    model = Path(model)
    vers = []
    for f in model.parent.glob(model.name + ".*"):
        tail = f.name[len(model.name) + 1:]
        if tail.isdigit():
            vers.append((int(tail), f))
    return sorted(vers)[-1][1] if vers else model


def main():
    print("ЖИВАЯ ПРОБА ИСПОЛНЕНИЯ ПЛАНА plan_run НА КОПИИ")
    import apply as BA
    import plan_fmt as F
    import runner as R

    # 1. Стек
    ready, why = BA.creoson_ready()
    ok("стек готов к записи", ready, why)
    if not ready:
        print("СТОП: запись без стека невозможна. Проба не выдаётся за успех.")
        return 3

    import creo_tools as CT

    # 2. Копия на диске
    ok("копия модели на диске", COPY_MODEL.exists(), str(COPY_MODEL))
    if not COPY_MODEL.exists():
        return 2

    # 3. Открыть копию (dirname ОТДЕЛЬНО — иначе ищет в рабочей папке)
    t0 = time.time()
    j = CT.creo_call("file", "open", {"file": COPY_MODEL.name,
                                      "dirname": str(COPY_MODEL.parent),
                                      "activate": True, "display": True}, 90)
    ok("копия открыта в Creo", CT.ok(j),
       CT.errmsg(j) if not CT.ok(j) else "%.1f с" % (time.time() - t0))
    time.sleep(2)

    # 4. До записи: параметра нет
    import facts as FT
    before, n_before = FT.facts_from_file(COPY_MODEL)
    ok("до записи параметра нет",
       not any(f["parameter"] == PARAM for f in before), "параметров: %d" % n_before)

    # 5. ЩИТ: активна ли копия (иначе plan_run обязан отказать RC 4)
    same, why_active = BA.ensure_active(str(COPY_MODEL))
    ok("щит видит копию как активную модель", same, why_active)

    # 6. ПЛАН: план batch_params переводим в единый формат
    import plan as BPP
    bp = BPP.build_plan(str(COPY_DIR), ["%s=%s" % (PARAM, VALUE)], limit=5)
    plan = F.from_batch_params(bp)
    plan["title"] = "Живая проба plan_run: %s=%s" % (PARAM, VALUE)
    good, errs = F.validate(plan)
    ok("план прошёл проверку формата", good, "; ".join(errs[:3]))
    plan_path = F.save_plan(plan, LOG_DIR)
    ok("план записан", Path(plan_path).exists(), plan_path)
    write_steps = [s for s in plan["steps"] if s["risk"] == "write"]
    ok("в плане есть пишущий шаг по копии", len(write_steps) == 1,
       "write %d, всего %d" % (len(write_steps), len(plan["steps"])))
    ok("шаг бьёт по копии, а не по боевому файлу",
       all(str(s["where"]).lower().startswith(str(COPY_DIR).lower())
           for s in plan["steps"]),
       plan["steps"][0]["where"] if plan["steps"] else "—")

    # 7. БЕЗ СОГЛАСИЯ — шаги не начинаются (даже при живом стеке)
    R.STOP["flag"] = False
    res_no = R.run_plan(plan, approve=False)
    ok("без согласия RC 3 (живой стек не спас)", res_no["rc"] == 3, res_no["detail"])

    # 8. СОГЛАСИЕ + запись через САМ runner
    t1 = time.time()
    res = R.run_plan(plan, approve=True, on_log=lambda s: print("  | " + s))
    ok("plan_run вернул успех", res["rc"] == 0 and res.get("done", 0) == 1,
       "RC %s за %.1f с: %s" % (res.get("rc"), time.time() - t1, res.get("detail")))
    time.sleep(2)

    # 9. ПРОВЕРКА ПО ФАЙЛУ — главная, а не по ответу сервера
    latest = latest_version(COPY_MODEL)
    ok("после save появилась новая версия", latest != COPY_MODEL, str(latest))
    after, n_after = FT.facts_from_file(latest)
    hit = [f for f in after if f["parameter"] == PARAM]
    ok("параметр виден в файле на диске (запись реальна)", bool(hit),
       "%s: %s" % (latest.name, hit[0]["param_value"] if hit else "НЕ НАЙДЕН"))
    ok("значение совпадает", bool(hit) and str(hit[0]["param_value"]) == VALUE,
       str(hit[0]["param_value"]) if hit else "—")

    # 10. ЖУРНАЛ шагов записан (спека п.4)
    jl = LOG_DIR / "plan_run.log"
    has_log = jl.exists() and PARAM in jl.read_text(encoding="utf-8")
    ok("журнал шагов содержит шаг с параметром", has_log, str(jl))

    # 11. ОТКАТ по плану: удалить параметр, сохранить, проверить по файлу
    jd = CT.creo_call("parameter", "delete", {"file": str(COPY_MODEL), "name": PARAM}, 30)
    ok("откат: параметр удалён в сессии", CT.ok(jd),
       CT.errmsg(jd) if not CT.ok(jd) else "удалён")
    time.sleep(1)
    CT.creo_call("file", "save", {"file": str(COPY_MODEL)}, 60)
    time.sleep(3)
    last2 = latest_version(COPY_MODEL)
    back, _ = FT.facts_from_file(last2)
    ok("откат: параметра в файле нет",
       not any(f["parameter"] == PARAM for f in back),
       "параметров в %s: %d" % (last2.name, len(back)))

    # 12. Закрыть окно копии — file:close_window (file:close НЕ существует)
    CT.creo_call("file", "close_window", {"file": str(COPY_MODEL)}, 30)

    print("-" * 78)
    print("ИТОГ ЖИВОЙ ЗАПИСИ plan_run: %s (провалов %d)"
          % ("ОК" if not fail else "НЕ ОК", len(fail)))
    if fail:
        print("провалы: " + "; ".join(fail))
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
