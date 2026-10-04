# -*- coding: utf-8 -*-
r"""probe_seq - ПРОБА: полная последовательность открытия с замерами (04.10.2026).

WHY: после close_window + erase_not_displayed + open + display щит снова увидел
пустую активную модель. Где именно она теряется — не гадаем: печатаем
get_active после КАЖДОГО шага, с паузами.
"""
import json
import sys
import time
from pathlib import Path

_AGENT = Path(__file__).resolve().parent
sys.path.insert(0, str(_AGENT))
OUT = _AGENT / "postregen_clean" / "probe_seq_out.txt"
DIR = r"D:\AI\PROBA\postregen_clean\00080"
NAME = "00080-03.asm"


def main():
    import creo_tools as CT
    lines = []

    def step(tag, wait=0.0):
        if wait:
            time.sleep(wait)
        a = CT.creo_call("file", "get_active", {}, 20)
        lines.append("%-46s активная: %s" % (tag, json.dumps(a, ensure_ascii=False,
                                                              default=str)[:150]))

    step("старт")
    r = CT.creo_call("file", "close_window", {"file": NAME}, 30)
    lines.append("close_window -> %s" % json.dumps(r, ensure_ascii=False, default=str)[:120])
    step("после close_window")
    r = CT.creo_call("file", "erase_not_displayed", {}, 30)
    lines.append("erase_not_displayed -> %s" % json.dumps(r, ensure_ascii=False,
                                                          default=str)[:120])
    step("после erase", 2.0)
    r = CT.creo_call("file", "open", {"dirname": DIR, "file": NAME}, 60)
    lines.append("open -> %s" % json.dumps(r, ensure_ascii=False, default=str)[:150])
    step("после open", 1.0)
    r = CT.creo_call("file", "display", {"file": NAME}, 60)
    lines.append("display -> %s" % json.dumps(r, ensure_ascii=False, default=str)[:150])
    step("после display", 2.0)

    # Гипотеза: активного окна нет вообще — get_active пуст. Создаём окно.
    r = CT.creo_call("file", "open", {"dirname": DIR, "file": NAME,
                                      "display": True, "activate": True}, 60)
    lines.append("open display=True -> %s" % json.dumps(r, ensure_ascii=False,
                                                        default=str)[:150])
    step("после open display=True", 2.0)
    r = CT.creo_call("file", "display", {"file": NAME}, 60)
    step("после повторного display", 2.0)
    v = CT.creo_call("view", "list", {}, 30)
    lines.append("view:list -> %s" % json.dumps(v, ensure_ascii=False,
                                                default=str)[:200])

    OUT.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())