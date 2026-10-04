# -*- coding: utf-8 -*-
r"""apply.py - ЗАПИСЬ плана очистки пост-регенерации в Creo.

ПРАВИЛА ЖЕЛЕЗА ДЛЯ ЭТОГО ФАЙЛА (наследованы от batch_params, класс Ж):
1. Сначала согласие: без approve=True запись не начинается — RC 3.
2. ЩИТ АКТИВНОЙ МОДЕЛИ: перед записью сверяем, что в Creo активна ИМЕННО та
   модель, куда пишем (инцидент 03.10.2026: стен боевой и копии одинаков).
3. СТОП: цикл проверяет флаг между моделями, отчёт говорит, где остановились.
4. Нет CREOSON/Creo — честный отказ RC 2, а НЕ «прогон успешен».
5. Боевые `config.pro` и файлы на Z: не трогаем никогда.

Пишущие вызовы (живые спеки CREOSON jsonSpecs):
  file:postregen_relations_set {file, relations: []} — очистить уравнения пост-регенерации
    («Clear the relations if missing» — пустой список = очистка);
  parameter:delete {file, name: маска}             — удалить параметры;
  feature:rename {file, name, new_name}            — переименовать элемент;
  file:refresh / file:save                         — пересчёт и сохранение.
"""
import io
import json
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_AGENT = _HERE.parent
for _p in (_AGENT, _HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import plan as P   # noqa: E402

STOP = P.STOP     # один флаг СТОП на оба модуля: окно ставит его один раз


def _norm_dir(s):
    """Путь от CREOSON может вернуться с удвоенным диском («Z:Z:/PTC/...»).
    Убираем повтор, ПОКА дальше не двоеточие, и возвращаем букву диска."""
    s = str(s or "").replace("\\", "/").lower().strip()
    while "//" in s:
        s = s.replace("//", "/")
    if len(s) >= 2 and s[1] == ":":
        drive = s[0]
        while len(s) >= 3 and s[1] == ":" and s[2] != ":":
            s = s[2:]
        if not s.startswith(drive + ":"):
            s = drive + s
    return s.rstrip("/")


def ensure_active(target_file, retries=3, pause=1.0):
    """ЩИТ: активная модель ДОЛЖНА быть целевой. Возвращает (ok, причина).

    Инцидент 03.10.2026 (dev\\incident_din439.py): `file:open` с полным путём не
    переключает окно — активируется модель с тем же стемом, уже открытая в
    сессии. Сверяем по ПОЛНОМУ пути, а не по имени файла."""
    import time as _t
    import creo_tools as CT
    want_name = str(Path(target_file).name).lower()
    want_dir = _norm_dir(Path(target_file).parent)
    for _i in range(int(retries)):
        j = CT.creo_call("file", "get_active", {}, 20)
        d = j.get("data") if CT.ok(j) else None
        if isinstance(d, dict):
            got = str(d.get("file") or "").lower()
            got_dir = _norm_dir(d.get("dirname") or "")
            if got == want_name and got_dir == want_dir:
                return True, "активна целевая модель %s (%s)" % (got, d.get("dirname"))
            return False, ("активна ДРУГАЯ модель: %s (%s) — запись прервана, "
                           "цель была %s (%s)" % (got or "неизвестна",
                                                  d.get("dirname") or "?", want_name,
                                                  Path(target_file).parent))
        _t.sleep(pause)
    return False, "CREOSON не отдал активную модель — запись прервана"


def clear_postregen(model):
    """Очистить уравнения пост-регенерации. Возвращает (ok, причина).

    СПЕКА: relations с пометкой «Clear the relations if missing» — значит ПУСТОЙ
    список relations = очистка, а не «оставить как было»."""
    import creo_tools as CT
    j = CT.creo_call("file", "postregen_relations_set",
                     {"file": P.model_name(model), "relations": []}, 25)
    if CT.ok(j):
        return True, "уравнения пост-регенерации сняты"
    return False, CT.errmsg(j)


def delete_param(model, mask):
    """Удалить параметры по маске. Возвращает (ok, причина)."""
    import creo_tools as CT
    j = CT.creo_call("parameter", "delete",
                     {"file": P.model_name(model), "name": mask}, 25)
    if CT.ok(j):
        return True, "параметры %s удалены" % mask
    return False, CT.errmsg(j)


def rename_feature(model, old, new):
    """Переименовать элемент модели. Возвращает (ok, причина)."""
    import creo_tools as CT
    j = CT.creo_call("feature", "rename",
                     {"file": P.model_name(model), "name": old, "new_name": new}, 25)
    if CT.ok(j):
        return True, "%s -> %s" % (old, new)
    return False, CT.errmsg(j)


def _act(kind, path, target, rename_to=""):
    """Одна пишущая операция по виду шага."""
    if kind == "postregen":
        return clear_postregen(path)
    if kind == "param":
        return delete_param(path, target)
    if kind == "rename":
        old, _, new = target.partition("->")
        return rename_feature(path, old.strip(), new.strip())
    return False, "неизвестный вид шага: %s" % kind


def _open_model(path):
    """Открыть модель в сессии и СДЕЛАТЬ АКТИВНОЙ — запись идёт по активной модели.

    ЖИВЫЕ НАХОДКИ 04.10.2026 (probe_activate, на боевой сборке 00080-03):
      1) `activate:true` НЕ переключает активную модель — после вызова
         get_active отдавал ПРЕЖНЮЮ модель; активной становится модель только
         после `file:display`;
      2) если модель с тем же именем уже загружена из ДРУГОЙ папки, `file:open`
         открывает ИМЕННО ТУ (из Z:), а не копию — и запись ушла бы в боевую
         модель. Именно это поймал щит (RC 4).
    Поэтому порядок: убрать из памяти сессии -> открыть -> показать.
    """
    import creo_tools as CT
    p = Path(path)
    name = P.model_name(path)
    # 1. убираем одноимённые модели из памяти, иначе откроется не та
    try:
        CT.creo_call("file", "close_window", {"file": name}, 30)
        CT.creo_call("file", "erase_not_displayed", {}, 30)
    except Exception:
        pass
    j = CT.creo_call("file", "open",
                     {"dirname": str(p.parent), "file": name}, 60)
    if not CT.ok(j):
        return False, CT.errmsg(j)
    d = CT.creo_call("file", "display", {"file": name}, 60)
    if not CT.ok(d):
        return False, "открыта, но не показана: %s" % CT.errmsg(d)
    return True, "открыта и активна %s" % name


def _finish_model(path):
    """Пересчёт + сохранение. Возвращает (ok, причина)."""
    import creo_tools as CT
    p = Path(path)
    r = CT.creo_call("file", "refresh", {"file": P.model_name(path)}, 40)
    if not CT.ok(r):
        return False, "refresh: %s" % CT.errmsg(r)
    r = CT.creo_call("file", "save", {"file": P.model_name(path)}, 40)
    if not CT.ok(r):
        return False, "save: %s" % CT.errmsg(r)
    return True, "пересчитано и сохранено"


TO_WRITE = ("clear", "delete", "rename")


def apply_plan(plan, approve=False, dry_run=False, on_log=None):
    """Исполнить план. Согласие обязательно; СТОП; честный отказ; щит активной модели."""
    log = on_log or (lambda s: None)
    # СТОП проверяется ПЕРВЫМ: человек нажал СТОП - запись не начинается вовсе.
    if STOP["flag"]:
        return {"rc": 0, "detail": "СТОП нажат до начала: запись не начиналась",
                "done": 0, "stopped": True}
    if plan.get("error"):
        return {"rc": 2, "detail": "план пуст или битый: %s" % plan["error"]}
    steps = [s for s in plan.get("steps", []) if s["verdict"] in TO_WRITE]
    if not steps:
        return {"rc": 0, "detail": "нечего применять: всё same/read_fail", "done": 0}
    # ЩИТ ЗАПИСИ: сетевые и несуществующие диски не пишем (аудит 04.10.2026).
    denied = []
    for s in steps:
        ok, why = P.write_allowed(s["file"])
        if not ok and (s["file"], why) not in denied:
            denied.append((s["file"], why))
    if denied:
        f, why = denied[0]
        return {"rc": 5, "stack_ready": False,
                "detail": ("ЗАПИСЬ ЗАПРЕЩЕНА щитом: %s (%s). Всего запрещённых целей: %d. "
                           "Запись НЕ выполнялась." % (f, why, len(denied)))}
    if not approve:
        return {"rc": 3, "detail": "НЕ СОГЛАСОВАНО: запись не начиналась",
                "planned": len(steps)}
    if dry_run:
        return {"rc": 0, "detail": "пробный прогон (dry_run): записи не было",
                "planned": len(steps), "done": 0}
    ready, why = P.stack_ready()
    if not ready:
        return {"rc": 2, "detail": "%s - запись НЕ выполнена; файлы не тронуты." % why,
                "planned": len(steps), "stack_ready": False}
    results, saved = [], set()
    for i, s in enumerate(steps):
        if STOP["flag"]:
            log("СТОП на шаге %d из %d" % (i, len(steps)))
            return {"rc": 0, "detail": "остановлено СТОП на шаге %d" % i,
                    "done": sum(1 for r in results if r["ok"]),
                    "results": results, "stopped": True}
        path = s["file"]
        # ЩИТ АКТИВНОЙ МОДЕЛИ — на первой операции этой модели.
        if path not in saved:
            opened, note = _open_model(path)
            if not opened:
                results.append({"file": s["name"], "kind": s["kind"], "target": s["target"],
                                "ok": False, "note": "не открылась: %s" % note})
                log("ПРОВАЛ открытия %s: %s" % (s["name"], note))
                return {"rc": 4, "detail": "модель не открылась — запись прервана",
                        "done": 0, "results": results, "stopped": True}
            same, why_active = ensure_active(path)
            if not same:
                results.append({"file": s["name"], "kind": s["kind"], "target": s["target"],
                                "ok": False, "note": why_active})
                log("СТОП-ЩИТ: %s" % why_active)
                return {"rc": 4, "detail": why_active, "done": 0, "results": results,
                        "stopped": True, "shield": "wrong_active_model"}
            saved.add(path)
        ok, note = _act(s["kind"], path, s["target"])
        results.append({"file": s["name"], "kind": s["kind"], "target": s["target"],
                        "ok": ok, "note": note})
        log("%s %s %s (%s)" % ("OK " if ok else "FAIL", s["name"], s["target"], note))
        time.sleep(0.05)
    # Сохраняем каждую изменённую модель один раз - снизу вверх не нужно,
    # сборки не трогаем на диске иначе, а через file:save.
    for path in list(saved):
        ok, note = _finish_model(path)
        log("%s сохранение %s (%s)" % ("OK " if ok else "FAIL", Path(path).name, note))
        if not ok:
            results.append({"file": Path(path).name, "kind": "save",
                            "target": Path(path).name, "ok": False, "note": note})
    done = sum(1 for r in results if r["ok"])
    return {"rc": 0 if done == len(results) else 1,
            "detail": "вышло: %d из %d" % (done, len(results)),
            "done": done, "planned": len(steps), "results": results, "stopped": False}


def write_apply_report(res):
    """Журнал прогона: где вышло, где нет. По закону дома отчёт = REPORT_* в log\\reports."""
    P.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    P.LOG_DIR.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%d_%H%M%S")
    rp = P.REPORT_DIR / ("REPORT_postregen_clean_apply_%s.md" % stamp)
    o = ["# ОТЧЁТ ПРИМЕНЕНИЯ ОЧИСТКИ ПОСТ-РЕГЕНЕРАЦИИ", "",
         "Итог: **%s** (RC %d) · %s" % ("ОК" if res.get("rc") == 0 else "НЕ ОК",
                                          res.get("rc", 0), res.get("detail", "")), ""]
    if res.get("results"):
        o += ["| Модель | Вид | Цель | Вердикт | Что |", "|---|---|---|---|---|"]
        for r in res["results"]:
            o.append("| %s | %s | %s | %s | %s |" % (
                r["file"], P.KIND_RU.get(r["kind"], r["kind"]), r["target"],
                "ОК" if r["ok"] else "ПРОВАЛ", str(r["note"]).replace("|", "/")[:160]))
    rp.write_text("\n".join(o), encoding="utf-8")
    return str(rp)


def main(argv):
    approve = "--approve" in argv or "--approve=1" in argv
    dry = "--dry_run" in argv
    jp = next((a for a in argv[1:] if a.endswith(".json")), None)
    if not jp:
        print("нужен файл плана: apply.py <plan.json> [--approve] [--dry_run]")
        return 2
    plan = json.loads(Path(jp).read_text(encoding="utf-8"))
    res = apply_plan(plan, approve=approve, dry_run=dry,
                     on_log=lambda s: print("  " + s))
    print("ПРИМЕНЕНИЕ ПЛАНА: RC %d - %s" % (res.get("rc", 0), res.get("detail", "")))
    if res.get("results"):
        print("отчёт: %s" % write_apply_report(res))
    return res.get("rc", 0)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.exit(main(sys.argv))