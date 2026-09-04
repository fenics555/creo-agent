# -*- coding: utf-8 -*-
r"""
АГЕНТ v12 — РЕЕСТР ИНСТРУМЕНТОВ (tools_registry.py)
АВТОПОДКЛЮЧЕНИЕ: каждый файл *_tools.py в папке агента — направление работы.
Блок сам объявляет свой список TOOLS. Реестр только собирает.
Новое направление = новый файл *_tools.py. Больше ничего трогать не надо.
"""
import importlib
from pathlib import Path
from core import log

TOOLS = []
BLOCKS = []

def load_all():
    TOOLS[:] = []; BLOCKS[:] = []
    here = Path(__file__).parent
    for p in sorted(here.glob("*_tools.py")):
        name = p.stem
        try:
            m = importlib.import_module(name)
            block_tools = getattr(m, "TOOLS", [])
            TOOLS.extend(block_tools)
            BLOCKS.append(name)
            log("реестр: блок <%s> подключён автоматически, инструментов: %d" % (name, len(block_tools)))
        except Exception as e:
            log("реестр: блок <%s> НЕ загружен: %s" % (name, e))

load_all()

def get(name):
    for t in TOOLS:
        if t["name"] == name: return t
    return None

def execute(name, args, client=None):
    t = get(name)
    if not t: return "инструмент %s не найден" % name
    if client:
        prof = __import__('users').get_profile(client)
        if prof and __import__('users').role_denied(prof.get("role", "Инженер"), name):
            return "⛔ роль «%s» не может выполнить «%s» (запрет администратора)" % (prof.get("role", "?"), name)
    try:
        return str(t["fn"](**(args or {})))
    except Exception as e:
        log("tool %s err: %s" % (name, e))
        return "ошибка исполнения %s: %s" % (name, e)


def describe():
    except Exception as e:
        log("tool %s err: %s" % (name, e))
        return "ошибка исполнения %s: %s" % (name, e)
def execute(name, args):
    t = get(name)
    if not t: return "инструмент %s не найден" % name
    try:
        return str(t["fn"](**(args or {})))
    except Exception as e:
        log("tool %s err: %s" % (name, e))
        return "ошибка исполнения %s: %s" % (name, e)

def describe():
    out = []
    for t in TOOLS:
        ps = ", ".join(t.get("params", {}).keys()) if t.get("params") else ""
        d = (t.get("desc") or "").strip()
        if len(d) > 45: d = d[:43].rstrip(" ,.;:-") + "…"
        out.append("- %s(%s) — %s%s" % (t["name"], ps, d, " [СОГЛАСОВАНИЕ]" if t.get("approval") else ""))
    return "\n".join(out)