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
TOOLS = [{"name": "guide", "desc": "Справка: что умеет агент", "params": {}, "approval": False, "fn": tool_guide}]
