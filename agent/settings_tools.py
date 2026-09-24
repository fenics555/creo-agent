# -*- coding: utf-8 -*-
r"""АГЕНТ v12 — БЛОК НАСТРОЕК (settings_tools.py). Направление: конфигурация."""
import json, urllib.request
import core
import settings as ST

def _caller():
    import threading
    try:
        return getattr(threading.current_thread(), "_tokclient", None)
    except Exception:
        return None


def tool_show(**kw):
    cl = _caller()
    txt = ST.show_all()
    try:
        import users
        if not (cl and users.is_admin(cl)):
            return txt + "\n\n(настройки — просмотр; менять может только админ)"
    except Exception:
        pass
    return txt


def tool_set(key="", value="", **kw):
    # СТРОГО АДМИН (требование дома 24.09.2026): смена модели и параметров — только администратору,
    # иначе любой в окне может «уронить» машину сменой модели (агент и Cline держат одни веса).
    cl = _caller()
    try:
        import users
        if not (cl and users.is_admin(cl)):
            return "⛔ менять настройки может только админ (сейчас: %s)" % (cl or "нет входа")
    except Exception:
        pass
    return "обновлено: %s=%s" % (key, value) if ST.set_val(key, value) else "ключ %s не найден" % key


def tool_models(**kw):
    try:
        j = json.load(urllib.request.urlopen(core.OLL + "/api/tags", timeout=5))
        cur = ST.get("llm_model")
        return "\n".join("• %s%s" % (m.get("name"), " ← активна" if m.get("name") == cur else "")
                         for m in j.get("models", [])) or "моделей нет"
    except Exception:
        return "Ollama не отвечает"


def tool_memory(**kw):
    """Что СЕЙЧАС лежит в памяти видеокарты (политика дома: одна модель на агент и Cline)."""
    try:
        j = json.load(urllib.request.urlopen(core.OLL + "/api/ps", timeout=5))
    except Exception:
        return "Ollama не отвечает"
    ms = j.get("models") or []
    if not ms:
        return "в памяти пусто (веса выгружены). Держать: ollama_keep_alive=%s" % (ST.get("ollama_keep_alive") or "1h")
    out = ["В ПАМЯТИ СЕЙЧАС: %d модель(ей)" % len(ms)]
    for m in ms:
        vr = (m.get("size_vram") or 0) / 2 ** 30
        out.append("• %s — ВРАМ %.1f ГБ, до %s" % (m.get("name"), vr, m.get("expires_at") or "?"))
    mx = int(ST.get("ollama_max_models") or 1)
    out.append("политика: максимум %d (ollama_max_models), активная модель: %s" % (mx, ST.get("llm_model")))
    if len(ms) > mx:
        out.append("⚠ в памяти больше, чем разрешено — проверь OLLAMA_MAX_LOADED_MODELS у службы Ollama")
    return "\n".join(out)


TOOLS = [
    {"name": "settings_show", "desc": "Показать все настройки системы", "params": {}, "approval": False, "fn": tool_show},
    {"name": "settings_set", "desc": "Изменить настройку (только админ: модель, окна и т.д.)", "params": {"key": "ключ", "value": "значение"}, "approval": True, "fn": tool_set},
    {"name": "settings_models", "desc": "Список моделей Ollama с активной", "params": {}, "approval": False, "fn": tool_models},
    {"name": "ollama_memory", "desc": "Что сейчас в памяти GPU: какие модели, ВРАМ, до когда", "params": {}, "approval": False, "fn": tool_memory},
]