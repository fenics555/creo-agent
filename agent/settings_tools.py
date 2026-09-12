# -*- coding: utf-8 -*-
r"""АГЕНТ v12 — БЛОК НАСТРОЕК (settings_tools.py). Направление: конфигурация."""
import json, urllib.request
import core
import settings as ST

def tool_show(**kw): return ST.show_all()

def tool_set(key="", value="", **kw):
    return "обновлено: %s=%s" % (key, value) if ST.set_val(key, value) else "ключ %s не найден" % key

def tool_models(**kw):
    try:
        j = json.load(urllib.request.urlopen(core.OLL + "/api/tags", timeout=5))
        cur = ST.get("llm_model")
        return "\n".join("• %s%s" % (m.get("name"), " ← активна" if m.get("name") == cur else "")
                         for m in j.get("models", [])) or "моделей нет"
    except Exception:
        return "Ollama не отвечает"

TOOLS = [
    {"name": "settings_show", "desc": "Показать все настройки системы", "params": {}, "approval": False, "fn": tool_show},
    {"name": "settings_set", "desc": "Изменить настройку (модель, окна и т.д.)", "params": {"key": "ключ", "value": "значение"}, "approval": True, "fn": tool_set},
    {"name": "settings_models", "desc": "Список моделей Ollama с активной", "params": {}, "approval": False, "fn": tool_models},
]