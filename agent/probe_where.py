# -*- coding: utf-8 -*-
r"""probe_where - ПРОБА: куда пишет postregen_relations_set (04.10.2026).

WHY: три порядка сохранения дали одно — на диске уравнение осталось. Значит
функция либо пишет в ДРУГОЕ место (обычные отношения), либо не пишет вовсе.
Проверяем: после postregen_relations_set что видно в ОБЫЧНЫХ отношениях, и
наоборот.
"""
import json
import sys
import time
from pathlib import Path

_AGENT = Path(__file__).resolve().parent
sys.path.insert(0, str(_AGENT))
OUT = _AGENT / "postregen_clean" / "probe_where_out.txt"
DIR = r"D:\AI\PROBA\postregen_clean\00080"
NAME = "00080-03.prt"


def snap(CT, tag):
    pr = CT.creo_call("file", "postregen_relations_get", {"file": NAME}, 30)
    rl = CT.creo_call("file", "relations_get", {"file": NAME}, 30)
    return ("%s\n   postregen: %s\n   обычные : %s"
            % (tag,
               json.dumps((pr.get("data") or {}).get("relations"), ensure_ascii=False)[:150],
               json.dumps((rl.get("data") or {}).get("relations"), ensure_ascii=False)[:150]))


def main():
    import creo_tools as CT
    lines = []
    CT.creo_call("file", "open", {"dirname": DIR, "file": NAME,
                                  "display": True, "activate": True}, 60)
    time.sleep(1)
    lines.append(snap(CT, "1) как есть"))
    CT.creo_call("file", "postregen_relations_set", {"file": NAME, "relations": []}, 60)
    time.sleep(1)
    lines.append(snap(CT, "2) после postregen_relations_set([])"))
    CT.creo_call("file", "save", {"file": NAME}, 60)
    lines.append(snap(CT, "3) после save (без выгрузки)"))
    CT.creo_call("file", "close_window", {"file": NAME}, 30)
    time.sleep(1)
    CT.creo_call("file", "erase_not_displayed", {}, 30)
    time.sleep(2)
    CT.creo_call("file", "open", {"dirname": DIR, "file": NAME, "display": False}, 60)
    lines.append(snap(CT, "4) после выгрузки и повторного открытия"))
    OUT.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())