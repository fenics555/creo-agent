# -*- coding: utf-8 -*-
"""АГЕНТ v15 — СПРАВКА (help_tools.py): меню направлений и содержимое GUIDE/*.md."""
import core

GUIDE_DIR = core.REPO / "GUIDE"

_KEYS = ["db", "creoson", "models", "trails", "pdf", "copy", "plm", "fleet", "settings", "kb"]
_TITLES = {
    "db": "Базы данных: что где лежит и как проверить",
    "creoson": "CREOSON и Creo: сессия, операции, согласования",
    "models": "Модели: поиск, где используется, состав",
    "trails": "Трейлы: кто работал, болезни, прогнозы",
    "pdf": "PDF-глаза: страницы, миниатюры, свежесть, перепечать",
    "copy": "Копия и переименование: план, сухой прогон",
    "plm": "Спецы, PLM, 1С: чтение, bom, аудит",
    "fleet": "Веб, флот, git: служба и синхронизация",
    "settings": "Настройки, роли, безопасность",
    "kb": "База знаний и поиск: чанки, индексы",
}


def _menu():
    lines = ["📖 СПРАВОЧНИК АГЕНТА — направления (guide topic=<ключ> или кнопка «подробнее»):"]
    for k in _KEYS:
        lines.append("— %s [DETAILS:%s]подробнее[/DETAILS]" % (_TITLES[k], k))
    lines.append("Пиши по-русски, один вопрос за ход.")
    return "\n".join(lines)


def tool_guide(topic="", **kw):
    """Меню справочника или содержимое D:\\AI\\repo\\GUIDE\\<topic>.md."""
    topic = (topic or "").strip()
    if not topic:
        return _menu()
    p = GUIDE_DIR / ("%s.md" % topic)
    if p.exists():
        return p.read_text(encoding="utf-8")
    return _menu() + "\n\n(файл направления «%s» ещё не написан)" % topic


def tool_tools_help(block="", **kw):
    """Полное описание инструментов блока или всех: tools_help block=creo/web/trail/plm, пусто = все"""
    import importlib
    import tools_registry as TR
    out = []
    for b in TR.BLOCKS:
        if block and block.lower() not in b.lower():
            continue
        try:
            m = importlib.import_module(b)
            for t in getattr(m, "TOOLS", []):
                ps = ", ".join((t.get("params") or {}).keys())
                out.append("- %s(%s) — %s%s" % (t["name"], ps, (t.get("desc") or "")[:80],
                                                " [СОГЛАСОВАНИЕ]" if t.get("approval") else ""))
        except Exception as e:
            out.append("%s: ошибка %s" % (b, e))
    return "\n".join(out) or ("Блок не найден. Блоки: " + ", ".join(TR.BLOCKS))


TOOLS = [
    {"name": "guide", "desc": "Справочник: меню направлений или тема (topic=db/creoson/models/...)",
     "params": {"topic": "ключ направления или пусто"}, "approval": False, "fn": tool_guide},
    {"name": "tools_help", "desc": "Полное описание инструментов блока (block=creo/web/trail/plm, пусто = все)",
     "params": {"block": "имя блока или пусто"}, "approval": False, "fn": tool_tools_help},
]