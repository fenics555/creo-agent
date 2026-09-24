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


_INFO_CACHE = None


def _model_info(name):
    """Окно контекста и размер модели (кэш в data\\model_info.json — не дёргаем Ollama зря)."""
    global _INFO_CACHE
    cf = core.DATA_DIR / "model_info.json"
    if _INFO_CACHE is None:
        try:
            _INFO_CACHE = json.loads(cf.read_text(encoding="utf-8"))
        except Exception:
            _INFO_CACHE = {}
    if name in _INFO_CACHE and _INFO_CACHE[name].get("ctx"):
        return _INFO_CACHE[name]
    try:
        r = urllib.request.Request(core.OLL + "/api/show", json.dumps({"model": name}).encode(),
                                   {"Content-Type": "application/json"})
        d = json.load(urllib.request.urlopen(r, timeout=20))
        mi = d.get("model_info") or {}
        ctx = next((v for k, v in mi.items() if str(k).endswith(".context_length")), None)
        _INFO_CACHE[name] = {"ctx": ctx, "params": (d.get("details") or {}).get("parameter_size")}
        cf.write_text(json.dumps(_INFO_CACHE, ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception:
        _INFO_CACHE[name] = {"ctx": None, "params": None}
    return _INFO_CACHE[name]


def tool_models(**kw):
    """Список моделей с ДЛИНОЙ ОКНА: чтобы человек сам выбирал модель и окно под неё."""
    try:
        j = json.load(urllib.request.urlopen(core.OLL + "/api/tags", timeout=5))
    except Exception:
        return "Ollama не отвечает"
    cur = ST.get("llm_model")
    ncx = ST.get("num_ctx")
    out = ["МОДЕЛИ OLLAMA (окно — свойство модели; своё окно дома: %s, активная модель: %s)" % (ncx, cur)]
    for m in j.get("models", []):
        nm = m.get("name")
        inf = _model_info(nm)
        out.append("• %-34s окно %-7s %-8s%s" % (nm, inf.get("ctx") or "?", inf.get("params") or "",
                                                 " ← активна" if nm == cur else ""))
    out.append("Поменять модель/окно: панель настроек (только админ) — «Модель чата» и «Окно контекста».")
    return "\n".join(out)


def tool_window(model="", **kw):
    """Какое окно у модели и что поставить в «Окно контекста» (без выдумок)."""
    nm = model or ST.get("llm_model")
    inf = _model_info(nm)
    ctx = inf.get("ctx")
    if not ctx:
        return "не смог узнать окно модели %s (Ollama не ответила)" % nm
    cur = int(ST.get("num_ctx") or 0)
    verdict = "совпадает с моделью" if cur == ctx else ("меньше, чем может: %s из %s" % (cur, ctx))
    return ("модель %s: окно %s, размер %s\nсейчас в настройках num_ctx=%s (%s)\n"
            "Совет дома: ставить не больше окна модели; больше — пустая трата памяти, меньше — режем контекст."
            % (nm, ctx, inf.get("params") or "?", cur, verdict))


def loaded_ctx():
    """Сколько контекста ВЫДЕЛЕНО загруженной модели прямо сейчас (факт, а не желаемое).
    Для сверки агента и Cline: они должны просить одинаковое окно, иначе Ollama перезагружает веса."""
    try:
        j = json.load(urllib.request.urlopen(core.OLL + "/api/ps", timeout=5))
        for m in (j.get("models") or []):
            return m.get("context_length") or (m.get("details") or {}).get("context_length")
    except Exception:
        return None
    return None


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
    {"name": "settings_models", "desc": "Список моделей Ollama с окном контекста и активной", "params": {}, "approval": False, "fn": tool_models},
    {"name": "model_window", "desc": "Какое окно у модели и что поставить в «Окно контекста»", "params": {"model": "имя модели (пусто = активная)"}, "approval": False, "fn": tool_window},
    {"name": "ollama_memory", "desc": "Что сейчас в памяти GPU: какие модели, ВРАМ, до когда", "params": {}, "approval": False, "fn": tool_memory},
]