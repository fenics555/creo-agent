import loop
from http_handlers import Hd
from loop import _wd_port

import loop
'АГЕНТ v15 — agent.py (полная сборка)\nThreadingHTTPServer + стриминг токенов + параллельные инструменты + планировщик.\nВитрина живёт в data/ui/index.html; константы PAGE больше нет.\n'
import json, re, os, socket, threading, time, datetime
from concurrent.futures import ThreadPoolExecutor
import subprocess, sys
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import core
from core import log, trace
import settings
import pdf_tools
import tools_registry as TR
import scanner
import users
import chat_tools
import panel
import vision_tools as VI
HOST, PORT = ('0.0.0.0', 8765)
HOSTNAME = socket.gethostname()
UI_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui', 'index.html')
_UI_CACHE = [0, b'']
STUB_PAGE = "<html><head><meta charset='utf-8'><title>АГЕНТ v15</title></head><body style='background:#1B1C1E;color:#E8E8E8;font:14px Segoe UI,sans-serif;padding:40px'><h2>ВИТРИНА НЕ НАЙДЕНА</h2><p>Положи index.html в D:\\AI\\tools\\agent\\data\\ui\\</p></body></html>"

def _scheduler():
    last_day = ''
    while True:
        try:
            now = datetime.datetime.now()
            if settings.get('night_enable'):
                hh = int(settings.get('night_hour') or 2)
                mm = int(settings.get('night_minute') or 0)
                if now.hour == hh and now.minute == mm and (now.strftime('%Y-%m-%d') != last_day):
                    last_day = now.strftime('%Y-%m-%d')
                    for t in str(settings.get('night_tasks') or 'scan,index,usage').split(','):
                        t = t.strip()
                        log('night start: %s' % t)
                        try:
                            if t == 'scan':
                                scanner.scan_models()
                            elif t == 'index':
                                scanner.index_all()
                            elif t == 'check':
                                subprocess.run([sys.executable, 'D:\\AI\\tools\\agent\\dev\\skills_check.py'], cwd='D:\\AI\\tools\\agent')
                            elif t == 'usage':
                                import usage_tools
                                usage_tools.build_usage(True)
                            elif t == 'backup':
                                import backup
                                backup._do()
                                import backup_tools
                                log(backup_tools.tool_housekeeping())
                                log(backup_tools.tool_drift_check())
                            elif t == 'drafts':
                                import draft_tools
                                log(draft_tools.tool_drafts_build())
                        except Exception as e:
                            log('night %s err: %s' % (t, e))
                        else:
                            log('night ok: %s' % t)
                    log('night run done')
        except Exception:
            pass
        time.sleep(30)

def _wd_port(port, host='127.0.0.1'):
    import socket as _s
    try:
        with _s.create_connection((host, port), timeout=2):
            return True
    except Exception:
        return False

def _wd_spawn(cmd):
    if not cmd:
        return False
    try:
        subprocess.Popen(cmd if isinstance(cmd, list) else cmd, shell=isinstance(cmd, str), cwd='D:\\AI\\tools\\agent', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        return True
    except Exception:
        return False

def _watchdog():
    fails = {}
    while True:
        try:
            if int(settings.get('wd_enable') or 1):
                for name, port, key, dflt in (('ollama', 11434, 'wd_ollama_cmd', 'ollama serve'), ('creoson', 8080, 'wd_creoson_cmd', '')):
                    if not _wd_port(port):
                        n = fails.get(name, 0) + 1
                        fails[name] = n
                        if n <= 3:
                            log('wd: %s down, raising (%d)' % (name, n))
                            _wd_spawn(settings.get(key) or dflt)
                        elif n == 4:
                            log('wd: %s still down, cooldown' % name)
                    else:
                        fails[name] = 0
        except Exception:
            pass
        time.sleep(int(settings.get('wd_interval') or 60))

if __name__ == '__main__':
    import atexit
    log('=== старт АГЕНТ v15 на %s ===' % HOSTNAME)
    pidfile = core.BASE / 'agent' / 'agent.pid'
    pidfile.write_text(str(os.getpid()), encoding='ascii')
    atexit.register(lambda: pidfile.unlink(missing_ok=True))
    threading.Thread(target=_scheduler, daemon=True).start()
    threading.Thread(target=_watchdog, daemon=True).start()
    try:
        ThreadingHTTPServer((HOST, PORT), Hd).serve_forever()
    finally:
        try:
            pidfile.unlink(missing_ok=True)
        except Exception:
            pass
