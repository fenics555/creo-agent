# -*- coding: utf-8 -*-
r"""dev\creo_write_diag.py - ПОЧЕМУ save не пишет на диск (диагностика живой записи).

Проверяет три уровня по отдельности, чтобы не гадать:
  1) запись в СЕССИЮ (parameter:set) - читаем обратно через parameter:get;
  2) сохранение (file:save) - что отвечает сервер;
  3) что лежит на ДИСКЕ (creo_read) - реальный результат.
"""
import io
import json
import sys
import time
from pathlib import Path

AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(AGENT / "batch_params"))

MODEL = r"D:\AI\PROBA\vol7_copy\din439.prt"
MODEL_SHORT = "din439.prt"      # так модель значится в CREOSON (file:list)
PARAM, VALUE = "VOL7_PROBA", "проверка_2026_10_03"


def show(tag, j):
    print("%-22s ok=%-5s %s" % (tag, bool(j) and not (j.get("status") or {}).get("error"),
                                json.dumps(j, ensure_ascii=False, default=str)[:300]))


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    import apply as A
    import creo_tools as CT
    import facts as FT
    import creo_read as CR

    ready, why = A.creoson_ready()
    print("стек готов: %s" % ready)
    if not ready:
        return 3

    print("\n--- 1. СЕССИЯ (открываем АКТИВНЫМ окном) ---")
    # НАЙДЕНО по живому клиенту CREOSON (web\assets\...\creoson_file.js:8,15):
    # у file:open есть поля `activate` и `display`. Без activate окно не становится
    # активным, get_active пустой, и file:save отвечает «ok», НИЧЕГО не записывая.
    show("file:open activate", CT.creo_call("file", "open",
                                            {"file": MODEL, "activate": True,
                                             "display": True}, 60))
    time.sleep(4)
    show("file:get_active", CT.creo_call("file", "get_active", {}, 20))
    show("parameter:set", CT.creo_call("parameter", "set",
                                       {"file": MODEL_SHORT, "name": PARAM,
                                        "value": VALUE}, 30))
    time.sleep(1)
    show("file:list", CT.creo_call("file", "list", {}, 20))

    print("\n--- 2. СОХРАНЕНИЕ ---")
    show("file:save short", CT.creo_call("file", "save", {"file": MODEL_SHORT}, 60))
    time.sleep(4)
    show("file:save full", CT.creo_call("file", "save", {"file": MODEL}, 60))
    time.sleep(4)

    print("\n--- 2б. ПОИСК АКТИВНОГО ОКНА ---")
    # get_active пустой -> save может идти не туда. Ищем команду активации.
    for cmd, fn, data in (("window", "activate", {}),
                          ("file", "activate", {"file": MODEL_SHORT}),
                          ("creo", "activate", {}),
                          ("window", "list", {}),
                          ("window", "main", {})):
        try:
            show("%s:%s" % (cmd, fn), CT.creo_call(cmd, fn, data, 20))
        except Exception as e:
            print("%s:%s -> %s" % (cmd, fn, e))

    print("\n--- 3. ДИСК ---")
    p = Path(MODEL)
    print("mtime до: %s" % time.strftime("%H:%M:%S", time.localtime(p.stat().st_mtime)))
    raw = CR.read(str(p))
    pr = CR.params(raw, CR.parse_toc(raw))
    print("параметров в файле: %d, VOL7_PROBA в них: %s"
          % (len(pr), PARAM in pr))
    fs, n = FT.facts_from_file(str(p))
    print("facts: %d, есть наш: %s" % (n, any(f["parameter"] == PARAM for f in fs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())