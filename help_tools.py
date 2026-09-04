# -*- coding: utf-8 -*-
GUIDE = """🤖 Что я умею (кликни-повтори):
— CREO: «какая модель открыта?» · «creo_get_params» · «creo_get_bom q=creoson_tests»
— ПОИСК: «найди: турновер» · «где используется: mv2400s» · «models_stats»
— СПЕЦЫ: «spec_read path=<путь.xlsx>» · «creo_audit_folder»
— ТРЕЙЛЫ: «trail_diagnose» · «trail_predict»
— КОПИЯ: «copy_model old=<имя> new=<имя> dry_run=1»
— ВЕБ: «web_study url=<ссылка>»
— ПЛМ: «plm_mine» · «plm_bom q=<сборка>» · «plm_audit»
Пиши по-русски, один вопрос за ход. Пишущие операции спрашивают ✅."""
def tool_guide(**kw): return GUIDE
def tool_tools_help(block="", **kw):
    """Полное описание инструментов блока или всех: tools_help block=creo"""
    import importlib
    import tools_registry as TR
    out = []
    for b in TR.BLOCKS:
        if block and block.lower() not in b.lower(): continue
        try:
            m = importlib.import_module(b)
            for t in getattr(m, "TOOLS", []):
                ps = ", ".join((t.get("params") or {}).keys())
                out.append("- %s(%s) — %s%s" % (t["name"], ps, (t.get("desc") or "")[:80], " [СОГЛАСОВАНИЕ]" if t.get("approval") else ""))
        except Exception as e:
            out.append("%s: ошибка %s" % (b, e))
    return "\n".join(out) or ("блок не найден. Блоки: " + ", ".join(TR.BLOCKS))

TOOLS = [
 {"name": "guide", "desc": "Справка: что умеет агент", "params": {}, "approval": False, "fn": tool_guide},
 {"name": "tools_help", "desc": "Полное описание инструментов блока (block=creo/web/trail/plm и т.п., пусто = все)", "params": {"block": "часть имени блока"}, "approval": False, "fn": tool_tools_help},
]
