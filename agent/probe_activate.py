# -*- coding: utf-8 -*-
r"""probe_activate - ПРОБА: что делает модель АКТИВНОЙ в CREOSON (04.10.2026).

WHY: щит ensure_active заблокировал запись: после `file:open {activate:true}`
активной осталась ПРЕЖНЯЯ модель (probe_regen_20261004.prt). Не гадаем —
перебираем способы и печатаем СЫРОЙ ответ `file:get_active` после каждого.
"""
import json
import sys
from pathlib import Path

_AGENT = Path(__file__).resolve().parent
sys.path.insert(0, str(_AGENT))
OUT = _AGENT / "postregen_clean" / "probe_activate_out.txt"
DIR = r"D:\AI\PROBA\postregen_clean\00080"
NAME = "00080-03.asm"


def act():
    return json.dumps(CT_call("file", "get_active", {}), ensure_ascii=False,
                      default=str)[:160]


def CT_call(cmd, fn, data, t=60):
    import creo_tools as CT
    return CT.creo_call(cmd, fn, data, t)


def main():
    lines = []
    lines.append("активная ДО: %s" % act())

    lines.append("1) open activate=true -> %s"
                 % json.dumps(CT_call("file", "open",
                                      {"dirname": DIR, "file": NAME, "activate": True}),
                              ensure_ascii=False, default=str)[:160])
    lines.append("   активная: %s" % act())

    lines.append("2) file:display -> %s"
                 % json.dumps(CT_call("file", "display", {"file": NAME}),
                              ensure_ascii=False, default=str)[:160])
    lines.append("   активная: %s" % act())

    lines.append("3) open display=true activate=true -> %s"
                 % json.dumps(CT_call("file", "open",
                                      {"dirname": DIR, "file": NAME,
                                       "display": True, "activate": True}),
                              ensure_ascii=False, default=str)[:160])
    lines.append("   активная: %s" % act())

    OUT.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())