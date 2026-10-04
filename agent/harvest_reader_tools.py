# -*- coding: utf-8 -*-
r"""HARVEST БЛОКА АГЕНТА — тонкая обёртка над САМОСТОЯТЕЛЬНОЙ программой HARVEST (04.10.2026).

ЗАЧЕМ. Слово владельца «доделывай» (пятое), после разговора про базы: у ПЛМ-READER есть мост —
10 инструментов `plm_*` в `plm_reader_tools.py` читают СВОЮ базу напрямую, а не копируют её в
главную. У HARVEST моста не было: `harvest_reader.py` (только чтение) звался ровно из одного места
(`pdf_tools.py:84` — один вызов `get_verdict`). То есть база чесалки (`harvest.db`: 93 076 моделей,
27 941 пара) была почти недоступна агенту — а спросить «где пара моделей» он не мог.

ПРИНЦИП (тот же, что у ПЛМ, манифест п.19 — программа самодостаточна):
  1. Источник истины один — база программы. В главную БД агента ничего не сливается: дубли
     только раздувают её (она уже 227 МБ).
  2. Мост ТОЛЬКО НА ЧТЕНИЕ. Чесалка пишет в свою базу — обёртка не пишет никогда.
  3. Импорт по явному пути: в доме есть одноимённые модули, обычный `import` отдаёт чужой.
"""
import io
import sqlite3
from contextlib import redirect_stdout
from pathlib import Path

import core

HERE = Path(__file__).resolve().parent
_HARVEST_DB = HERE / "data" / "harvest.db"
_reader = None


def reader():
    """Читатель базы чесалки (read-only), загруженный по явному пути — без гонки имён."""
    global _reader
    if _reader is None:
        import importlib.util
        path = HERE / "harvest_reader.py"
        if not path.exists():
            raise FileNotFoundError("нет читателя чесалки: %s" % path)
        spec = importlib.util.spec_from_file_location("harvest_reader_agent", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _reader = mod
    return _reader


def _ro():
    """Соединение ТОЛЬКО НА ЧТЕНИЕ: чесалка может писать в базу прямо сейчас."""
    if not _HARVEST_DB.exists():
        return None
    return sqlite3.connect("file:%s?mode=ro" % _HARVEST_DB, uri=True)


def _where_db():
    return str(_HARVEST_DB) if _HARVEST_DB.exists() else "(база чесалки не найдена)"


def tool_harvest_summary():
    """Сводка базы чесалки: сколько моделей, пар, что свежее."""
    c = _ro()
    if c is None:
        return "база чесалки не найдена: %s" % _HARVEST_DB
    try:
        models = c.execute("select count(*) from models_raw").fetchone()[0]
        pairs = c.execute("select count(*) from pairs").fetchone()[0]
        with_pdf = c.execute("select count(*) from pairs "
                             "where pdf_path is not null and pdf_path<>''").fetchone()[0]
        top = c.execute("select ext, count(*) from models_raw group by ext "
                        "order by 2 desc limit 8").fetchall()
        return "\n".join(["СВОДКА ЧЕСАЛКИ (источник: %s)" % _where_db(),
                          "моделей: %d · пар: %d · с путём к pdf: %d"
                          % (models, pairs, with_pdf),
                          "расширения: " + ", ".join("%s=%d" % r for r in top)])
    except sqlite3.Error as e:
        return "чесалка не прочитана: %s" % e
    finally:
        c.close()
def tool_harvest_pair(q):
    """Пара «модель — чертёж» по имени."""
    c = _ro()
    if c is None:
        return "база чесалки не найдена"
    try:
        q = (q or "").strip()
        if not q:
            return "укажи имя (например: 00080-03-z)"
        rows = c.execute("select model, pdf_path from pairs where model like ? limit 20",
                         ("%%%s%%" % q,)).fetchall()
        if not rows:
            return "в чесалке нет пар по «%s»" % q
        return ("НАЙДЕНО ПАР: %d\n" % len(rows)
                + "\n".join("- %s → %s" % r for r in rows))
    except sqlite3.Error as e:
        return "чесалка не прочитана: %s" % e
    finally:
        c.close()


def tool_harvest_find(q, limit="20"):
    """Есть ли модель в чесалке по имени."""
    c = _ro()
    if c is None:
        return "база чесалки не найдена"
    try:
        q = (q or "").strip()
        if not q:
            return "укажи имя"
        n = min(int(limit or 20), 200)
        rows = c.execute("select name, path from models_raw where name like ? limit ?",
                         ("%%%s%%" % q, n)).fetchall()
        if not rows:
            return "в чесалке нет моделей по «%s»" % q
        return ("МОДЕЛЕЙ: %d\n" % len(rows)) + "\n".join("- %s · %s" % r for r in rows)
    except (sqlite3.Error, ValueError) as e:
        return "чесалка не прочитана: %s" % e
    finally:
        c.close()


def tool_harvest_registry(root_filter=""):
    """Реестр пар с отметкой свежести (через читателя чесалки)."""
    try:
        entries = reader().get_registry_entries(root_filter or None)
    except Exception as e:
        return "реестр чесалки не прочитан: %s" % e
    if not entries:
        return "реестр чесалки пуст (или фильтр «%s» ничего не оставил)" % root_filter
    out = ["ПАР В РЕЕСТРЕ: %d" % len(entries)]
    for e in entries[:30]:
        out.append("- %s → %s · %s" % (e.get("model", "?"), e.get("pdf_path", "?"),
                                        "актуален" if e.get("fresh") else "устарел"))
    if len(entries) > 30:
        out.append("… ещё %d" % (len(entries) - 30))
    return "\n".join(out)


def tool_harvest_verdict(q):
    """Актуален ли чертёж против модели."""
    try:
        return "модель «%s»: %s" % (q, reader().get_verdict(q))
    except Exception as e:
        return "вердикт не получен: %s" % e


TOOLS = [
    # ПРАВКА 04.10.2026: у блока не было `kind`, поэтому `tools_registry` относил все пять
    # инструментов в `other`, и проверка `dev\vol1_check.py` падала («карта: other=5»).
    # Инструменты только читают — значит `kind: read`, как у соседей по смыслу.
    {"name": "harvest_summary", "desc": "Сводка базы чесалки HARVEST (модели, пары)",
     "kind": "read", "group": "PLM/базы", "params": {}, "approval": False,
     "fn": tool_harvest_summary},
    {"name": "harvest_pair", "desc": "Пара модель-чертёж из базы чесалки",
     "kind": "read", "group": "PLM/базы", "params": {"q": "имя"}, "approval": False,
     "fn": tool_harvest_pair},
    {"name": "harvest_find", "desc": "Есть ли модель в чесалке по имени",
     "kind": "read", "group": "PLM/базы", "params": {"q": "имя", "limit": "сколько"},
     "approval": False, "fn": tool_harvest_find},
    {"name": "harvest_registry", "desc": "Реестр пар со свежестью (чесалка, только чтение)",
     "kind": "read", "group": "PLM/базы", "params": {"root_filter": "корень"},
     "approval": False, "fn": tool_harvest_registry},
    {"name": "harvest_verdict", "desc": "Актуален ли чертёж против модели",
     "kind": "read", "group": "PLM/базы", "params": {"q": "имя"}, "approval": False,
     "fn": tool_harvest_verdict},
]