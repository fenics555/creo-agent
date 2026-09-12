# -*- coding: utf-8 -*-
r"""
ТРАНСФОРМЕР v12 — БЭКАПЫ (backup.py)
Двухуровневые: рабочие копии sqlite каждые 6 часов + архив.
Глубина — из settings (retention).
"""
import time, datetime, threading, sqlite3, shutil
from core import log, DB, DATA_DIR
import settings

BK = DATA_DIR / "backups"

def _do():
    try:
        BK.mkdir(parents=True, exist_ok=True)
        if not DB.exists(): return
        name = "agent_%s.sqlite" % datetime.datetime.now().strftime("%y%m%d_%H%M")
        dst = BK / name
        src = sqlite3.connect(DB, timeout=30); dst_c = sqlite3.connect(dst)
        src.backup(dst_c); src.close(); dst_c.close()
        log("бэкап: %s" % name)
        keep = settings.get("retention") or 7
        olds = sorted(BK.glob("agent_*.sqlite"), key=lambda f: f.stat().st_mtime, reverse=True)
        for f in olds[keep:]: f.unlink(missing_ok=True)
    except Exception as e:
        log("бэкап err: %s" % e)

def _loop():
    while True:
        _do()
        time.sleep(6 * 3600)

def start():
    threading.Thread(target=_loop, daemon=True).start()

def restore(name):
    src = BK / name
    if not src.exists(): return "нет такого бэкапа"
    shutil.copyfile(src, DB)
    return "восстановлено из %s (перезапустите агента)" % name

def list_backups():
    if not BK.exists(): return "бэкапов нет"
    return "\n".join("• %s (%.1f МБ)" % (f.name, f.stat().st_size / 1e6) for f in sorted(BK.glob("agent_*.sqlite"), reverse=True))