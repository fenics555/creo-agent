# -*- coding: utf-8 -*-
"""АГЕНТ v12 — БЛОК БЭКАПОВ (backup_tools.py). Направление: архив базы."""
import backup as BK
import core
import settings
import os
import datetime

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
    c2 = core.db()
    c2.execute("VACUUM")
    c2.close()
    rep.append("sqlite vacuum done")
    return "\n".join(rep) or "housekeeping: чисто"

def tool_drift_check():
    import os
    rep = []
    c = core.db()
    exts = (".prt", ".asm", ".drw", ".pdf")
    pats = ["%" + e for e in exts]
    db_n = c.execute("SELECT COUNT(*) FROM files WHERE " + " OR ".join(["lower(path) LIKE ?"] * len(exts)), pats).fetchone()[0]
    ch_n = c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    c.close()
    disk_n = 0
    _rr = settings.get("scan_roots") or []
    if isinstance(_rr, str):
        _rr = _rr.split(",")
    for r in [x.strip() for x in _rr if x and x.strip()]:
        if not os.path.isdir(r):
            continue
        for w, _, fs in os.walk(r):
            for f in fs:
                if f.lower().endswith(exts):
                    disk_n += 1
    if disk_n == 0:
        rep.append("ROOTS ALARM: scan_roots пусты или недоступны, проверь настройку")
    drift = abs(disk_n - db_n) * 100 // max(disk_n, 1)
    rep.append("files: db %d, disk %d, drift %d%%" % (db_n, disk_n, drift))
    if drift > 5:
        rep.append("DRIFT ALARM: файловый индекс разошёлся с диском, нужен scan")
    if ch_n == 0:
        rep.append("CHUNKS ALARM: база знаний пуста, нужен index")
    return "\n".join(rep)

TOOLS = [
    {"name": "backup_list", "desc": "Список бэкапов базы", "params": {}, "approval": False, "fn": tool_list},
    {"name": "backup_restore", "desc": "Восстановить базу из бэкапа", "params": {"name": "имя файла"}, "approval": True, "fn": tool_restore},
    {"name": "backup_housekeeping", "desc": "Ночная уборка: бекапы до retention, pdfcache по image_days, prune истории", "params": {}, "fn": tool_housekeeping},
    {"name": "drift_check", "desc": "Сверка баз с диском: файлы и чанки, аварийные строки", "params": {}, "fn": tool_drift_check},
]

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
