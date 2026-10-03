# -*- coding: utf-8 -*-
r"""PLM агента — тонкая обёртка над САМОСТОЯТЕЛЬНОЙ программой PLM-READER (03.10.2026).

ЗАЧЕМ: старый блок `plm_tools.py` держал свой ПЛМ в базе агента (`plm_items/plm_bom`) и брал
связи из индекса `usage`, который пуст с 27.09 (проверено: usage=0, plm_bom=1324 строки, все
`source='usage'`). Источник истины теперь один — программа `plm_reader\`: своя база
`plm_reader\db\plm_reader_ГГГГММДД_ЧЧММСС.db`, свои настройки `plm_reader\settings\settings.json`.

ИМПОРТ ПО ПУТИ, А НЕ `import engine`: в доме четыре файла `engine.py` (plm_reader, log_clean,
purge_versions, копии в бекапах), и обычный `import engine` может отдать чужой модуль из
sys.modules. Здесь `importlib` с явным файлом — гонки имён не будет.

ПЕСОЧНИЦА: `PLM_SETTINGS` и `PLM_DB_DIR` уводят настройки и базу; `plm_scan` в агенте по
умолчанию НЕ пишет (apply=0) — запись только под щитом согласования.
"""
import importlib.util
import io
import os
import time
from contextlib import redirect_stdout
from pathlib import Path

import core

HERE = Path(__file__).resolve().parent
READER = HERE / "plm_reader"
_ENGINE = None


def engine():
    """Движок PLM-READER, загруженный по явному пути (без гонки имён)."""
    global _ENGINE
    if _ENGINE is None:
        path = READER / "engine.py"
        if not path.exists():
            raise FileNotFoundError("нет движка PLM-READER: %s" % path)
        spec = importlib.util.spec_from_file_location("plm_reader_engine", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _ENGINE = mod
        dbdir = os.environ.get("PLM_DB_DIR")
        if dbdir:
            _ENGINE.set_base_dir(dbdir)
    return _ENGINE


def _call(fn, *a, **kw):
    """Позвать команду движка и вернуть её текстовый вывод (движок печатает, не возвращает)."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*a, **kw)
    return buf.getvalue().strip()


def _conn(ro=True):
    return engine().connect(ro=ro)
# ---------------- инструменты ----------------

def tool_plm_item(q="", **kw):
    """Карточка изделия из базы PLM-READER (таблица snapshots)."""
    if not q:
        return "укажи обозначение или имя файла"
    c = _conn(ro=True)
    try:
        like = "%" + q.strip().lower() + "%"
        rows = c.execute(
            "SELECT designation, name, material, rev, path FROM snapshots "
            "WHERE LOWER(designation) LIKE ? OR LOWER(name) LIKE ? OR LOWER(path) LIKE ? "
            "LIMIT 8", (like, like, like)).fetchall()
    finally:
        c.close()
    if not rows:
        return "не найдено в базе ПЛМ-READER: %s (база: %s)" % (q, _where_db())
    out = ["БАЗА: %s" % _where_db(), "НАЙДЕНО: %d" % len(rows)]
    for d, n, m, rev, p in rows:
        out.append("- %s | %s | материал: %s | рев: %s" % (d or "?", n or "?", m or "—", rev or "—"))
        out.append("    %s" % p)
    return "\n".join(out)


def tool_plm_tree(q="", depth=4, **kw):
    """Дерево производства (вниз) из базы ПЛМ-READER — таблица links."""
    if not q:
        return "укажи сборку"
    return _call(engine().do_tree, q, int(depth or 4))


def tool_plm_where(q="", **kw):
    """Куда входит изделие (входимость) — таблица links, поиск по child."""
    if not q:
        return "укажи деталь"
    return _call(engine().do_where, q)


def tool_plm_changes(n=20, **kw):
    """Последние изменения из базы ПЛМ-READER — таблица changes."""
    return _call(engine().do_changes, int(n or 20))


def tool_plm_history(q="", n=50, **kw):
    """История изменений одного изделия по файлам ПЛМ-READER."""
    if not q:
        return "укажи изделие или файл"
    return _call(engine().do_changes_model, q, int(n or 50))


def tool_plm_summary(**kw):
    """Сводка базы ПЛМ-READER: сколько изделий, связей, изменений, где база.

    03.10.2026: `engine.summary()` ВОЗВРАЩАЕТ словарь, а не печатает — обёртка брала только
    stdout и отдавала пустоту.
    """
    s = engine().summary()
    if not s:
        return "сводка пуста (база не прочитана): %s" % _where_db()
    return ("БАЗА: %s\nизделий (моделей): %s · снимков: %s · связей: %s · папок: %s · изменений: %s"
            % (_where_db(), s.get("models"), s.get("snapshots"), s.get("links"),
               s.get("folders"), s.get("changes")))


def tool_plm_rename_plan(old="", new="", **kw):
    """План переименования: какие файлы и связи заденет переименование."""
    if not (old and new):
        return "укажи старое и новое имя"
    return _call(engine().do_rename_plan, old, new)


def tool_plm_scan(root="", full=0, apply=0, **kw):
    """Скан ПЛМ-READER. По умолчанию НЕ пишет (apply=0) — показывает, что будет сделано.
    apply=1 — запись в базу, только под щитом согласования."""
    E = engine()
    roots = [root] if root else list(E.scan_config()[0] or E.DEFAULT_ROOTS)
    if not apply:
        return ("DRY-RUN. Скан %s.\nЧтобы записать — повтори с apply=1 (новая база в %s)."
                % (roots, _where_db()))
    return _call(E.do_scan, roots, 8, 120, None, None, bool(full), None)


def _ensure_status_table(c):
    c.execute("CREATE TABLE IF NOT EXISTS plm_statuses (designation TEXT PRIMARY KEY, "
              "status TEXT, rev TEXT, updated TEXT)")


def tool_plm_ii(q="", reason="", who="", **kw):
    """Извещение об изменении (ГОСТ 2.503).

    Статуса и ревизии в самой программе ПЛМ-READER нет (там нет полей lifecycle), поэтому агент
    ведёт их у себя в маленькой таблице `plm_statuses` — отдельно от данных ПЛМ.
    """
    if not q:
        return "укажи обозначение"
    c = core.db()
    try:
        _ensure_status_table(c)
        row = c.execute("SELECT designation, rev, status FROM plm_statuses WHERE designation=?",
                        (q.lower(),)).fetchone()
        des, rev = (row[0], row[1]) if row else (q.lower(), None)
        rev2 = chr(ord(rev) + 1) if rev and rev < "Я" else "А"
        ts = time.strftime("%y%m%d_%H%M")
        if row:
            c.execute("UPDATE plm_statuses SET rev=?, status='Утверждено', updated=? "
                      "WHERE designation=?", (rev2, time.strftime("%d.%m %H:%M"), des))
        else:
            c.execute("INSERT INTO plm_statuses(designation,status,rev,updated) VALUES(?,?,?,?)",
                      (des, "Утверждено", rev2, time.strftime("%d.%m %H:%M")))
        c.commit()
    finally:
        c.close()
    d = core.REPO / "Изменения"
    d.mkdir(parents=True, exist_ok=True)
    p = d / ("ИИ_%s_%s.md" % (ts, des))
    p.write_text("ИЗВЕЩЕНИЕ ОБ ИЗМЕНЕНИИ (ГОСТ 2.503)\nОбозначение: %s\nРевизия: %s -> %s\n"
                 "Дата: %s\nКто: %s\nПричина: %s\n"
                 % (des, rev or "—", rev2, ts, who or "агент", reason or "—"), encoding="utf-8")
    return "ИИ %s: %s (%s->%s). Данные изделия — в ПЛМ-READER (%s)." % (
        p.name, des, rev or "—", rev2, _where_db())


def tool_plm_status(q="", **kw):
    """Статус и ревизия изделия (таблица агента plm_statuses; данные изделия — в ПЛМ-READER)."""
    c = core.db()
    try:
        _ensure_status_table(c)
        if q:
            row = c.execute("SELECT designation,status,rev,updated FROM plm_statuses "
                            "WHERE designation=?", (q.lower(),)).fetchone()
            return ("%s: статус %s, ревизия %s (%s)" % (row[0], row[1], row[2] or "—", row[3])
                    if row else "статуса нет: %s" % q)
        rows = c.execute("SELECT designation,status,rev FROM plm_statuses ORDER BY updated DESC "
                         "LIMIT 20").fetchall()
        return ("статусов: %d\n" % len(rows)) + "\n".join("- %s: %s (%s)" % r for r in rows)
    finally:
        c.close()


TOOLS = [
    {"name": "plm_item", "desc": "Карточка изделия из базы ПЛМ-READER",
     "params": {"q": "обозначение или имя файла"}, "approval": False, "fn": tool_plm_item},
    {"name": "plm_tree", "desc": "Дерево производства (ПЛМ-READER, таблица links)",
     "params": {"q": "сборка", "depth": "глубина"}, "approval": False, "fn": tool_plm_tree},
    {"name": "plm_where", "desc": "Куда входит изделие (входимость в ПЛМ-READER)",
     "params": {"q": "деталь"}, "approval": False, "fn": tool_plm_where},
    {"name": "plm_changes", "desc": "Последние изменения из базы ПЛМ-READER",
     "params": {"n": "сколько"}, "approval": False, "fn": tool_plm_changes},
    {"name": "plm_history", "desc": "История изменений одного изделия (ПЛМ-READER)",
     "params": {"q": "изделие или файл", "n": "сколько"}, "approval": False, "fn": tool_plm_history},
    {"name": "plm_summary", "desc": "Сводка базы ПЛМ-READER: изделия, связи, изменения",
     "params": {}, "approval": False, "fn": tool_plm_summary},
    {"name": "plm_rename_plan", "desc": "План переименования в терминах ПЛМ-READER",
     "params": {"old": "старое имя", "new": "новое"}, "approval": False, "fn": tool_plm_rename_plan},
    {"name": "plm_scan", "desc": "Скан ПЛМ-READER; apply=1 — запись (щит согласования)",
     "params": {"root": "папка", "full": "1 полный", "apply": "1 записать"}, "approval": True,
     "fn": tool_plm_scan},
    {"name": "plm_ii", "desc": "Извещение об изменении по ГОСТ 2.503 (статус ведёт агент)",
     "params": {"q": "обозначение", "reason": "причина", "who": "кто"}, "approval": True,
     "fn": tool_plm_ii},
    {"name": "plm_status", "desc": "Статус и ревизия изделия",
     "params": {"q": "обозначение"}, "approval": False, "fn": tool_plm_status},
]


def _where_db():
    try:
        return engine().active_db()
    except Exception:
        return "(база не определена)"