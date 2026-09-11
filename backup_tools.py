# -*- coding: utf-8 -*-
"""АГЕНТ v12 — БЛОК БЭКАПОВ (backup_tools.py). Направление: архив базы."""
import backup as BK
import core
import settings

def tool_list(**kw): return BK.list_backups()
def tool_restore(name="", **kw): return BK.restore(name)

def tool_housekeeping():
    import os, datetime
    rep = []
    bak = core.BASE / "data" / "backups"
    keep = int(settings.get("retention") or 7)
    if bak.exists():
        fs = sorted(bak.glob("*.sqlite*"), key=os.path.getmtime, reverse=True)
        for f in fs[keep:]:
            f.unlink(); rep.append("backup removed " + f.name)
    days = int(settings.get("image_days") or 7)
    cut = datetime.datetime.now().timestamp() - days * 86400
    pc = core.BASE / "data" / "pdfcache"
    if pc.exists():
        for f in pc.glob("*.png"):
            if os.path.getmtime(f) < cut:
                f.unlink(); rep.append("cache removed " + f.name)
    c = core.db()
    c.execute("DELETE FROM history WHERE ts < datetime('now','-90 days')")
    c.execute("DELETE FROM feedback WHERE ts < datetime('now','-180 days')")
    c.commit(); c.close()
    rep.append("history/feedback pruned")
    return "\n".join(rep) or "housekeeping: чисто"

TOOLS = [
    {"name": "backup_list", "desc": "Список бэкапов базы", "params": {}, "approval": False, "fn": tool_list},
    {"name": "backup_restore", "desc": "Восстановить базу из бэкапа", "params": {"name": "имя файла"}, "approval": True, "fn": tool_restore},
    {"name": "backup_housekeeping", "desc": "Ночная уборка: бекапы до retention, pdfcache по image_days, prune истории", "params": {}, "fn": tool_housekeeping},
]
