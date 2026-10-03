# -*- coding: utf-8 -*-
"""АГЕНТ v15 — СПРАВКА (help_tools.py): меню направлений и содержимое GUIDE/*.md."""
import core

GUIDE_DIR = core.REPO / "GUIDE"

_KEYS = ["db", "passport", "creoson", "creo", "models", "trails", "pdf", "copy", "plm", "fleet", "settings", "kb"]
_TITLES = {
    "db": "Базы данных: что где лежит и как проверить",
    "passport": "Паспорт компании: люди, цели, стратегия, живые базы",
    "creoson": "CREOSON: мост к Creo, команды, согласования",
    "creo": "Creo: сессия, параметры, аудит, сохранение",
    "models": "Модели: поиск, где используется, состав",
    "trails": "Трейлы: кто работал, болезни, прогнозы",
    "pdf": "PDF-глаза: страницы, миниатюры, свежесть, реестр",
    "copy": "Копия и переименование: план, сухой прогон",
    "plm": "Спецы, PLM, 1С: чтение, bom, аудит",
    "fleet": "Веб, флот, git: служба и синхронизация",
    "settings": "Настройки, роли, безопасность",
    "kb": "База знаний и поиск: чанки, индексы, скиллы",
}


def _menu():
    lines = ["📖 СПРАВОЧНИК АГЕНТА — направления (guide topic=<ключ> или кнопка «подробнее»):"]
    for k in _KEYS:
        lines.append("— %s [DETAILS:%s][/DETAILS]" % (_TITLES[k], k))
    lines.append("Пиши по-русски, один вопрос за ход.")
    return "\n".join(lines)


def tool_guide(topic="", **kw):
    """Меню справочника или содержимое D:\\AI\\repo\\GUIDE\\<topic>.md."""
    topic = (topic or "").strip()
    if not topic:
        return _menu()
    if topic == "passport":
        pp = core.REPO / "PASSPORT.md"
        if pp.exists():
            return pp.read_text(encoding="utf-8")
        return _menu() + "\n\n(паспорт ещё не ведётся)"
    p = GUIDE_DIR / ("%s.md" % topic)
    if p.exists():
        return p.read_text(encoding="utf-8")
    return _menu() + "\n\n(файл направления «%s» ещё не написан)" % topic


def tool_tools_help(block="", kind="", group="", **kw):
    """Описание инструментов: block=.../kind=check|report|act|read|admin, пусто = все.
    kind/group берутся из карты инструментов (tools_registry), поля в блоках необязательны."""
    import tools_registry as TR
    block = (block or "").strip()
    kind = (kind or "").strip().lower()
    group = (group or "").strip()
    out = []
    for k, g, t in TR.iter_tools(kind or None, group or None):
        b = t.get("source") or ""
        if block and block.lower() not in str(b).lower():
            continue
        ps = ", ".join((t.get("params") or {}).keys())
        out.append("- %s(%s) [%s%s%s] — %s%s" % (
            t["name"], ps, k, "/" + g if g else "",
            "/требует Creo" if TR.meta_of(t["name"])[2] else "", (t.get("desc") or "")[:80],
            " [СОГЛАСОВАНИЕ]" if t.get("approval") else ""))
    return "\n".join(out) or ("Ничего не найдено. Блоки: " + ", ".join(TR.BLOCKS)
                              + ". Типы: " + ", ".join(TR.KINDS))


def tool_tools_card(kind="", group="", **kw):
    """Карта инструментов агента: сводка по типам и предметам + списки имён"""
    import tools_registry as TR
    return TR.card((kind or "").strip().lower() or None, (group or "").strip() or None)


TOOLS = [
    {"name": "guide", "desc": "Справочник: меню направлений или тема (topic=db/creoson/creo/models/...)",
     "params": {"topic": "ключ направления или пусто"}, "approval": False, "fn": tool_guide,
     "kind": "read", "group": "справочник"},
    {"name": "tools_help", "desc": "Описание инструментов: фильтр block=.../kind=check|report|act|read|admin, пусто = все",
     "params": {"block": "имя блока или пусто", "kind": "тип инструмента или пусто",
                "group": "предмет или пусто"},
     "approval": False, "fn": tool_tools_help, "kind": "read", "group": "справочник"},
    {"name": "tools_card", "desc": "Карта инструментов: сводка по типам (kind) и предметам (group), с числами",
     "params": {"kind": "тип инструмента или пусто", "group": "предмет или пусто"},
     "approval": False, "fn": tool_tools_card, "kind": "read", "group": "справочник"},
]