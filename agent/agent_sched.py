# -*- coding: utf-8 -*-
"""АГЕНТ v15 — sched.py: ночной планировщик и сторож сервисов."""
import sys, subprocess, time, datetime
import core
from core import log, trace
import settings
import scanner

def _scheduler():
    last_day = ""
    while True:
        try:
            now = datetime.datetime.now()
            if settings.get("night_enable"):
                hh = int(settings.get("night_hour") or 2); mm = int(settings.get("night_minute") or 0)
                if now.hour == hh and now.minute == mm and now.strftime("%Y-%m-%d") != last_day:
                    last_day = now.strftime("%Y-%m-%d")
                    for t in str(settings.get("night_tasks") or "scan,index,usage").split(","):
                        t = t.strip()
                        log("night start: %s" % t)
                        try:
                            if t == "scan":
                                log("night %s: пропущено по пункту 19 (harvest.py вне процесса агента)" % t)
                            elif t == "index":
                                log("night index: %s" % scanner.index_all())
                            elif t == "usage":
                                import usage_tools; usage_tools.build_usage(True)
                            elif t == "backup":
                                import backup; backup._do(); import backup_tools; log(backup_tools.tool_housekeeping()); log(backup_tools.tool_drift_check())
                            elif t == "drafts":
                                import draft_tools
                                log(draft_tools.tool_drafts_build())
                            elif t == "check":
                                subprocess.run([sys.executable, r"D:\AI\tools\agent\dev\skills_check.py"], cwd=r"D:\AI\tools\agent")
                        except Exception as e:
                            log("night %s err: %s" % (t, e))
                        else:
                            log("night ok: %s" % t)
                    log("night run done")
        except Exception:
            pass
        time.sleep(30)


def _wd_port(port, host="127.0.0.1"):
    import socket as _s
    try:
        with _s.create_connection((host, port), timeout=2): return True
    except Exception: return False

def _wd_spawn(cmd):
    if not cmd: return False
    try:
        subprocess.Popen(cmd if isinstance(cmd, list) else cmd, shell=isinstance(cmd, str),
                         cwd=r"D:\AI\tools\agent", creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return True
    except Exception: return False

def _watchdog():
    fails = {}
    while True:
        try:
            if int(settings.get("wd_enable") or 1):
                for name, port, key, dflt in (("ollama", 11434, "wd_ollama_cmd", "ollama serve"),):
                    if not _wd_port(port):
                        n = fails.get(name, 0) + 1; fails[name] = n
                        if n <= 3:
                            log("wd: %s down, raising (%d)" % (name, n))
                            _wd_spawn(settings.get(key) or dflt)
                        elif n == 4: log("wd: %s still down, cooldown" % name)
                    else: fails[name] = 0
        except Exception: pass
        time.sleep(int(settings.get("wd_interval") or 60))

