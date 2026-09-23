# -*- coding: utf-8 -*-
import threading
import scanner
import usage_tools as UT
def _work():
    """Ночной прогон: индекс знаний (FTS5 по текстовым файлам) + пересбор связей.
    Скан моделей ведёт harvest.py (отдельная программа класса Р), не агент."""
    for name, fn in (("индекс знаний", lambda: scanner.index_all()),
                     ("связи", lambda: UT.build_usage(True))):
        try:
            fn()
        except Exception:
            pass
    # Помечаем старые факты как устаревшие
    try:
        from core import mark_facts_stale
        mark_facts_stale(30)
    except Exception: 
        pass
def tool_nightly_run(**kw):
    threading.Thread(target=_work, daemon=True).start()
    return "ночной прогон запущен"
def tool_nightly_state(**kw): return UT.tool_usage_state()
TOOLS = [
 {"name": "nightly_run", "desc": "Ночной прогон (скан+индекс+usage)", "params": {}, "approval": True, "fn": tool_nightly_run},
 {"name": "nightly_state", "desc": "Прогресс ночного прогона", "params": {}, "approval": False, "fn": tool_nightly_state},
]
