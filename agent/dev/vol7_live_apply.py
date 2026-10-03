# -*- coding: utf-8 -*-
r"""dev\vol7_live_apply.py - ЖИВАЯ ЗАПИСЬ ПАКЕТНЫХ ПАРАМЕТРОВ НА КОПИИ (долг волны 7).

Правила прогона (класс Ж):
  * модель — ТОЛЬКО КОПИЯ в D:\AI\PROBA\vol7_copy, боевой файл не открывается;
  * параметр ставится на СВОЁ имя (VOL7_PROBA), чтобы не портить боевые параметры;
  * проверка результата — по файлу на диске (через facts/creo_read), а не «по ответу сервера»;
  * откат = удалить параметр и сохранить (описание в отчёте, как в плане).

Запуск: cmd /c "cd /d D:\AI\tools\agent && python -X utf8 dev\vol7_live_apply.py"
"""
import io
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(AGENT / "batch_params"))

fail = []
COPY_DIR = Path(r"D:\AI\PROBA\vol7_copy")
COPY_MODEL = COPY_DIR / "vol7_probe.prt"   # УНИКАЛЬНОЕ имя: коллизия по стену — причина инцидента
PARAM = "VOL7_PROBA"
VALUE = "проверка_2026_10_03"


def ok(name, cond, detail=""):
    d = detail if isinstance(detail, str) else str(detail)
    print(("OK   " if cond else "FAIL ") + name + ((" | " + d) if d else ""))
    if not cond:
        fail.append(name)


def latest_version(model):
    """Последняя версия файла модели (prt.N). Creo при save создаёт новую версию,
    а базовый файл не меняется — проверять надо её (живой факт 03.10.2026)."""
    model = Path(model)
    vers = []
    for f in model.parent.glob(model.name + ".*"):
        tail = f.name[len(model.name) + 1:]
        if tail.isdigit():
            vers.append((int(tail), f))
    return sorted(vers)[-1][1] if vers else model


def main():
    print("ЖИВАЯ ЗАПИСЬ ПАКЕТНЫХ ПАРАМЕТРОВ НА КОПИИ")
    import apply as A
    ready, why = A.creoson_ready()
    ok("стек готов к записи", ready, why)
    if not ready:
        print("СТОП: запись без стека невозможна.")
        return 3

    import creo_tools as CT
    import creo_ops_tools as OT

    # 1. Копия на диске
    ok("копия модели на диске", COPY_MODEL.exists(), str(COPY_MODEL))
    if not COPY_MODEL.exists():
        return 2

    CT.cc = CT.creo_call   # живая цитата: в creo_tools функция называется creo_call, не cc

    # 2. Открыть копию в Creo
    t0 = time.time()
    # КОНТРАКТ ИЗ ЖИВОГО КЛИЕНТА CREOSON (creoson_file.js): у FileObj есть поля
    # `file` и `dirname`. Без dirname файл ищется в рабочей папке (pwd) — отсюда ошибка
    # «Could not open file ... in directory Z:\PTC\CREO-START\START-STD\».
    j = CT.creo_call("file", "open", {"file": COPY_MODEL.name,
                                          "dirname": str(COPY_MODEL.parent),
                                          "activate": True, "display": True}, 90)
    ok("копия открыта в Creo", CT.ok(j), CT.errmsg(j) if not CT.ok(j) else "%.1f с" % (time.time() - t0))
    time.sleep(2)

    act = CT.tool_get_active()
    ok("CREOSON знает активную модель", bool(act) and "не знаю" not in act, str(act))
    print("  рабочая папка Creo: %s" % CT.tool_pwd())
    print("  файлы в папке Creo: %s" % CT.tool_list_files("din439*").replace("\n", " | "))

    # 3. До записи: параметра нет
    import facts as FT
    before, n_before = FT.facts_from_file(COPY_MODEL)
    has_before = any(f["parameter"] == PARAM for f in before)
    ok("до записи параметра нет", not has_before, "параметров в копии: %d" % n_before)

    # 4. ЗАПИСЬ (тот самый путь, что зовёт apply.py)
    res = OT.tool_set_param(name=PARAM, value=VALUE, model=str(COPY_MODEL))
    ok("запись параметра принята CREOSON", "установлен" in str(res), str(res)[:120])
    time.sleep(2)

    # 5. Сохранить на диск
    js = CT.creo_call("file", "save", {"file": str(COPY_MODEL)}, 60)
    ok("модель сохранена", CT.ok(js), CT.errmsg(js) if not CT.ok(js) else "сохранена")
    time.sleep(3)

    # 6. ПРОВЕРКА ПО ФАЙЛУ — главная, а не по ответу сервера.
    # ВАЖНО (живой факт 03.10.2026): Creo при save создаёт НОВУЮ ВЕРСИЮ (prt.N),
    # базовый файл не меняется. Проверять надо последнюю версию, иначе «запись не видна».
    latest = latest_version(COPY_MODEL)
    ok("после save появилась новая версия", latest != COPY_MODEL, str(latest))
    after, n_after = FT.facts_from_file(latest)
    hit = [f for f in after if f["parameter"] == PARAM]
    ok("параметр виден в файле на диске (запись реальна)", bool(hit),
       "%s: значение %s" % (latest.name, hit[0]["param_value"] if hit else "НЕ НАЙДЕН"))
    ok("значение совпадает", bool(hit) and str(hit[0]["param_value"]) == VALUE,
       str(hit[0]["param_value"]) if hit else "—")

    # 7. ОТКАТ: удалить параметр и сохранить (план отката должен быть рабочим)
    jd = CT.creo_call("parameter", "delete", {"file": str(COPY_MODEL), "name": PARAM}, 30)
    ok("откат: параметр удалён в сессии", CT.ok(jd),
       CT.errmsg(jd) if not CT.ok(jd) else "удалён")
    time.sleep(1)
    CT.creo_call("file", "save", {"file": str(COPY_MODEL)}, 60)
    time.sleep(3)
    back, _ = FT.facts_from_file(COPY_MODEL)
    ok("откат: параметра в файле нет", not any(f["parameter"] == PARAM for f in back),
       "параметров: %d" % len(back))

    print("-" * 78)
    print("ИТОГ ЖИВОЙ ЗАПИСИ: %s (провалов %d)"
          % ("ОК" if not fail else "НЕ ОК", len(fail)))
    if fail:
        print("провалы: " + "; ".join(fail))
    return 0 if not fail else 1


if __name__ == "__main__":
    sys.exit(main())