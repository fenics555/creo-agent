# -*- coding: utf-8 -*-
import threading
import scanner
def _work():
    """Ночной прогон: индекс знаний (FTS5 по текстовым файлам).
    03.10.2026: пересбор связей убран — индекс `usage` мёртв (пуст с 27.09), связи ведёт
    ПЛМ-READER своей командой `plm_scan`."""
    for name, fn in (("индекс знаний", lambda: scanner.index_all()),):
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
def tool_nightly_state(**kw):
    """Состояние ночного прогона.

    03.10.2026: было `UT.tool_usage_state()` — блок `usage_tools` отключён (индекс usage пуст
    с 27.09). Состояние теперь читаем из агентской `usage_meta`, а ПЛМ — из ПЛМ-READER."""
    try:
        import core
        c = core.db()
        try:
            rows = c.execute("SELECT * FROM usage_meta").fetchall()
            cols = [d[0] for d in c.execute("SELECT * FROM usage_meta LIMIT 0").description]
        finally:
            c.close()
        out = ("; ".join("=".join(map(str, r)) for r in rows) if rows else "(usage_meta пуст)")
        out = "usage_meta(%s): %s" % (",".join(cols), out)
    except Exception as e:
        out = "usage_meta не прочитан: %s" % e
    try:
        import plm_reader_tools as PRT
        return out + "\nПЛМ: " + PRT.tool_plm_summary().replace("\n", " | ")
    except Exception as e:
        return out + "\nПЛМ: не прочитан (%s)" % e
TOOLS = [
 {"name": "nightly_run", "desc": "Ночной прогон (скан+индекс+usage)", "params": {}, "approval": True, "fn": tool_nightly_run},
 {"name": "nightly_state", "desc": "Прогресс ночного прогона", "params": {}, "approval": False, "fn": tool_nightly_state},
]
