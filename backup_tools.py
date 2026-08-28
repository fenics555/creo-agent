# -*- coding: utf-8 -*-
r"""АГЕНТ v12 — БЛОК БЭКАПОВ (backup_tools.py). Направление: архив базы."""
import backup as BK

def tool_list(**kw): return BK.list_backups()
def tool_restore(name="", **kw): return BK.restore(name)

TOOLS = [
    {"name": "backup_list", "desc": "Список бэкапов базы", "params": {}, "approval": False, "fn": tool_list},
    {"name": "backup_restore", "desc": "Восстановить базу из бэкапа", "params": {"name": "имя файла"}, "approval": True, "fn": tool_restore},
]