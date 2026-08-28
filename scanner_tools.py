# -*- coding: utf-8 -*-
r"""АГЕНТ v12 — БЛОК СКАНЕРА (scanner_tools.py). Направление: индексация."""
import threading
import scanner as SC

def tool_index_run(**kw):
    threading.Thread(target=SC.index_all, daemon=True).start()
    return "переиндексация запущена в фоне"

def tool_scan_run(**kw):
    threading.Thread(target=SC.scan_models, daemon=True).start()
    return "скан моделей запущен в фоне"

def tool_state(**kw):
    s = SC.state()
    return "файлов: %s, чанков: %s, моделей: %s, индексация: %s (%s/%s)" % (
        s["files"], s["chunks"], s["models"], "идёт" if s["indexing"] else "нет", s["done"], s["total"])

TOOLS = [
    {"name": "index_run", "desc": "Запустить переиндексацию базы знаний", "params": {}, "approval": False, "fn": tool_index_run},
    {"name": "scan_run", "desc": "Запустить скан 3D-моделей Creo", "params": {}, "approval": False, "fn": tool_scan_run},
    {"name": "index_state", "desc": "Состояние базы: файлов/чанков/моделей", "params": {}, "approval": False, "fn": tool_state},
]