# -*- coding: utf-8 -*-
r"""dev\close_models.py - ЗАКРЫТЬ открытые модели в Creo БЕЗ сохранения.

Нужно перед прогоном записи на копию: пока в сессии открыта модель с тем же стемом,
`file:open` не переключает окно (инцидент 03.10.2026).
"""
import io
import json
import sys
import time
from pathlib import Path

AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    import creo_tools as CT
    j = CT.creo_call("file", "list", {}, 20)
    print("открыто до: %s" % json.dumps(j, ensure_ascii=False, default=str)[:200])
    # erase=false -> НЕ удалять с диска, только закрыть окно; discard -> не сохранять
    # функция называется close_window (живая цитата из клиента CREOSON creoson_file.js)
    jc = CT.creo_call("file", "close_window", {"erase": False}, 40)
    print("file:close ok=%s %s" % (CT.ok(jc), json.dumps(jc, ensure_ascii=False,
                                                        default=str)[:200]))
    time.sleep(3)
    j2 = CT.creo_call("file", "list", {}, 20)
    print("открыто после: %s" % json.dumps(j2, ensure_ascii=False, default=str)[:200])
    j3 = CT.creo_call("file", "get_active", {}, 20)
    print("get_active: %s" % json.dumps(j3, ensure_ascii=False, default=str)[:200])
    return 0


if __name__ == "__main__":
    sys.exit(main())