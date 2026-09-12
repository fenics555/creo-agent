# -*- coding: utf-8 -*-
r"""АГЕНТ v12 — БЛОК 1С (one_c_tools.py). Статус выгрузки."""
import datetime
from pathlib import Path

DIR1C = Path(r"D:\AI\1c")

def _find():
    if not DIR1C.exists(): return None
    hits = []
    for m in ("*.xml", "*.csv"): hits += list(DIR1C.glob(m))
    return max(hits, key=lambda p: p.stat().st_mtime) if hits else None

def tool_status(**kw):
    p = _find()
    if not p:
        return "выгрузка 1С не найдена: %s" % DIR1C
    mt = datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%d.%m.%Y %H:%M")
    return "выгрузка 1С на месте: %s (%d байт, обновлена %s)" % (p.name, p.stat().st_size, mt)

TOOLS = [
    {"name": "one_c_status", "desc": "Статус выгрузки 1С: файл, размер, свежесть", "params": {}, "approval": False, "fn": tool_status},
]