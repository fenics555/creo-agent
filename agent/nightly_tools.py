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
    с 27.09). Состояние теперь читаем из агентской `usage_meta`, а ПЛМ — из ПЛМ-READER.

    ЖИВАЯ НАХОДКА 04.10.2026 (баг из эстафеты волн 9–12): таблица `usage_meta` УДАЛЕНА из
    agent.sqlite при переезде на ПЛМ-READER (см. db_tools.py:35), но чтение здесь осталось —
    и `nightly_state` падал с «no such table: usage_meta» (лог агента 04.10 10:31).
    Лечение: сначала ПРОВЕРЯЕМ наличие таблицы; состояние ночи берём из таблицы `files`
    (сколько проиндексировано), а ПЛМ-состояние — из ПЛМ-READER, как и задумано."""
    out = ""
    try:
        import core
        c = core.db()
        try:
            have = {r[0] for r in c.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")}
            if "usage_meta" in have:
                rows = c.execute("SELECT * FROM usage_meta").fetchall()
                cols = [d[0] for d in c.execute("SELECT * FROM usage_meta LIMIT 0").description]
                out = ("; ".join("=".join(map(str, r)) for r in rows) if rows else "(usage_meta пуст)")
                out = "usage_meta(%s): %s" % (",".join(cols), out)
            else:
                # Таблицы usage_meta больше нет (переход на ПЛМ-READER) — показываем живой индекс.
                parts = []
                if "files" in have:
                    parts.append("файлов в индексе: %d" %
                                 c.execute("SELECT COUNT(*) FROM files").fetchone()[0])
                if "fts_index" in have:
                    parts.append("строк в FTS: %d" %
                                 c.execute("SELECT COUNT(*) FROM fts_index").fetchone()[0])
                if "chunks" in have:
                    parts.append("чанков: %d" %
                                 c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0])
                out = "состояние индекса: %s" % (", ".join(parts) if parts else "индекс не собран")
                out += " | usage_meta удалена 03.10 (переход на ПЛМ-READER)"
        finally:
            c.close()
    except Exception as e:
        out = "состояние не прочитано: %s" % e
    try:
        import plm_reader_tools as PRT
        return out + "\nПЛМ: " + PRT.tool_plm_summary().replace("\n", " | ")
    except Exception as e:
        return out + "\nПЛМ: не прочитан (%s)" % e
TOOLS = [
 {"name": "nightly_run", "desc": "Ночной прогон (скан+индекс+usage)", "params": {}, "approval": True, "fn": tool_nightly_run},
 {"name": "nightly_state", "desc": "Прогресс ночного прогона", "params": {}, "approval": False, "fn": tool_nightly_state},
]
