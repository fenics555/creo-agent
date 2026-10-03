# -*- coding: utf-8 -*-
r"""dev\vol8_live_rename.py - ЖИВАЯ ПРОБА ШАГА `rename_model` ПЛАНА (хвост волны 7).

Долг эстафеты: «запись feature_rename через onlysession+save». Закрывается волной 8
тем, что переименование стало ШАГОМ ПЛАНА (`what=rename_model`), а не отдельным
инструментом.

УСЛОВИЕ, ОТКРЫТОЕ ЖИВЬЁМ 03.10.2026: `rename_tools` работает в РАБОЧЕЙ ПАПКЕ Creo
(`file:pwd`), а не по произвольному пути — с абсолютным путём он отвечает отказом.
Значит копия обязана лежать в рабочей папке, и это указано в отчёте как долг
обобщения (инструмент должен принимать папку).

Безопасность: только копия в D:\AI\PROBA, боевые файлы не открываются.
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


def ok(name, cond, detail=""):
    d = detail if isinstance(detail, str) else str(detail)
    print(("OK   " if cond else "FAIL ") + name + ((" | " + d) if d else ""))
    if not cond:
        fail.append(name)


def main():
    print("ЖИВАЯ ПРОБА ШАГА rename_model ПЛАНА")
    import apply as BA
    import plan_fmt as F
    import runner as R

    ready, why = BA.creoson_ready()
    import rename_tools as RT
    ok("стек готов", ready, why)
    if not ready:
        print("СТОП: без стека проба невозможна.")
        return 3

    import creo_tools as CT

    wd = Path(str(CT.tool_pwd()).rstrip("/").replace(":", ":", 1))
    print("рабочая папка Creo: %s" % CT.tool_pwd())
    src = Path(r"D:\AI\PROBA\vol8_copy\vol8_ren.prt")
    ok("копия для переименования есть", src.exists(), str(src))
    if not src.exists():
        return 2

    # 1. Открыть копию (уникальное имя) — иначе rename открывает по своей папке
    jo = CT.creo_call("file", "open", {"file": src.name, "dirname": str(src.parent),
                                      "activate": True, "display": True}, 90)
    ok("копия открыта", CT.ok(jo), CT.errmsg(jo) if not CT.ok(jo) else "открыта")
    time.sleep(2)

    # 2. ЩИТ: активна ли именно копия
    same, why_active = BA.ensure_active(str(src))
    ok("щит видит копию как активную", same, why_active)

    # 3. ПЛАН: шаг rename_model выражается планом (rollback = вернуть имя)
    new_name = src.with_name("vol8_ren_renamed.prt")
    step = F.make_step(1, "rename_model", str(src),
                       args={"old_name": str(src), "new_name": str(new_name)},
                       risk="write",
                       rollback="вернуть имя обратно: rename_model %s -> %s"
                                % (new_name.name, src.name),
                       target=src.name)
    plan = {"plan_version": F.PLAN_VERSION, "kind": "rename_model",
            "title": "Живая проба шага rename_model", "steps": [step],
            "counts": {"write": 1}, "total": 1}
    good, errs = F.validate(plan)
    ok("план со шагом rename прошёл проверку формата", good, "; ".join(errs[:3]))

    # 4. БЕЗ СОГЛАСИЯ
    R.STOP["flag"] = False
    ok("без согласия RC 3", R.run_plan(plan, approve=False)["rc"] == 3)

    # 5. С СОГЛАСИЕМ — запись через сам runner
    # ЖИВАЯ НАХОДКА 03.10.2026 (два дефекта, оба проверены пробой):
    #  1) `file:close_window` отвечает «успех», но модель ОСТАЁТСЯ в сессии — убирает
    #     только `file:erase` (цитата пробы: после erase сессия = ['vol8_probe.prt']).
    #  2) висящая в памяти модель с новым именем роняет переименование:
    #     «Error renaming model; check to see there isn't another model in memory
    #     with the same name».
    CT.creo_call("file", "erase", {"file": "vol8_ren_renamed.prt"}, 30)
    CT.creo_call("file", "erase", {"file": "vol8_ren.prt"}, 30)
    time.sleep(1)
    jo2 = CT.creo_call("file", "open", {"file": src.name, "dirname": str(src.parent),
                                        "activate": True, "display": True}, 90)
    ok("сессия очищена, копия открыта заново", CT.ok(jo2),
       ", ".join(RT._session()) if RT._session() else "сессия пуста")
    res = R.run_plan(plan, approve=True, on_log=lambda s: print("  | " + s))
    ok("plan_run вернул успех", res["rc"] == 0 and res.get("done", 0) == 1,
       "RC %s: %s" % (res.get("rc"), res.get("detail")))
    time.sleep(2)

    # 6. ПРОВЕРКА НА ДИСКЕ: новое имя должно появиться
    made = list(src.parent.glob("vol8_ren_renamed*"))
    ok("новое имя появилось на диске", bool(made),
       ", ".join(p.name for p in made) or "НЕ НАЙДЕНО")
    old_left = list(src.parent.glob("vol8_ren.prt*"))
    ok("старое имя осталось (копия не пропала)", bool(old_left),
       ", ".join(p.name for p in old_left))

    # 7. ОТКАТ: возвращаем имя обратно, иначе следующий прогон упадёт по «same name»
    CT.creo_call("file", "erase", {"file": "vol8_ren_renamed.prt"}, 30)
    time.sleep(1)
    back = RT.tool_rename_model(old_name=str(new_name), new_name=str(src), dry_run=0)
    time.sleep(1)
    back_files = sorted(p.name for p in src.parent.glob("vol8_ren*"))
    ok("откат: имя возвращено", any(f.startswith("vol8_ren.") for f in back_files),
       "%s | %s" % (", ".join(back_files), str(back)[:120]))

    print("-" * 78)
    print("ИТОГ ЖИВОЙ ПРОБЫ rename_model: %s (провалов %d)"
          % ("ОК" if not fail else "НЕ ОК", len(fail)))
    if fail:
        print("провалы: " + "; ".join(fail))
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())
