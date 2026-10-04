# -*- coding: utf-8 -*-
r"""probe_save_path - ПРОБА: КАК уравнение реально попадает на ДИСК (04.10.2026).

WHY: file:save отвечал «ok», но после выгрузки из памяти уравнение на диске
ОСТАВАЛОСЬ. Перебираем порядок операций и каждый раз проверяем результат
честно: выгружаем модель из памяти и читаем с диска заново.
"""
import json
import sys
import time
from pathlib import Path

_AGENT = Path(__file__).resolve().parent
sys.path.insert(0, str(_AGENT))
OUT = _AGENT / "postregen_clean" / "probe_save_path_out.txt"
DIR = r"D:\AI\PROBA\postregen_clean\00080"
NAME = "00080-03.prt"


def unload(name):
    import creo_tools as CT
    CT.creo_call("file", "close_window", {"file": name}, 30)
    time.sleep(1)
    CT.creo_call("file", "erase_not_displayed", {}, 30)
    time.sleep(2)


def read_disk(name):
    import creo_tools as CT
    CT.creo_call("file", "open", {"dirname": DIR, "file": name, "display": False}, 60)
    r = CT.creo_call("file", "postregen_relations_get", {"file": name}, 30)
    return json.dumps((r.get("data") or {}).get("relations"), ensure_ascii=False)[:80]


def trial(lines, tag, ops):
    import creo_tools as CT
    CT.creo_call("file", "open", {"dirname": DIR, "file": NAME,
                                  "display": True, "activate": True}, 60)
    time.sleep(1)
    for cmd, fn, data in ops:
        r = CT.creo_call(cmd, fn, data, 60)
        lines.append("   %s -> %s" % (fn, json.dumps(r, ensure_ascii=False,
                                                    default=str)[:90]))
    unload(NAME)
    lines.append("   НА ДИСКЕ: %s" % read_disk(NAME))
    unload(NAME)


def main():
    import creo_tools as CT
    lines = ["проба порядка сохранения на модели %s" % NAME]

    lines.append("ПОПЫТКА 1: relations_set([]) -> save")
    trial(lines, "1", [("file", "postregen_relations_set",
                        {"file": NAME, "relations": []}),
                       ("file", "save", {"file": NAME})])

    lines.append("ПОПЫТКА 2: relations_set([]) -> regenerate -> save")
    trial(lines, "2", [("file", "postregen_relations_set",
                        {"file": NAME, "relations": []}),
                       ("file", "regenerate", {"file": NAME}),
                       ("file", "save", {"file": NAME})])

    lines.append("ПОПЫТКА 3: relations_set([]) -> refresh -> regenerate -> save")
    trial(lines, "3", [("file", "postregen_relations_set",
                        {"file": NAME, "relations": []}),
                       ("file", "refresh", {"file": NAME}),
                       ("file", "regenerate", {"file": NAME}),
                       ("file", "save", {"file": NAME})])

    OUT.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())