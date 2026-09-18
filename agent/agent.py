"""АГЕНТ v15 — agent.py (полная сборка)
ThreadingHTTPServer + стриминг токенов + параллельные инструменты + планировщик.
Витрина живёт в data/ui/index.html; константы PAGE больше нет.
"""

import loop
from http_handlers import Hd
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
import sched
HOST, PORT = ('0.0.0.0', 8765)
HOSTNAME = socket.gethostname()
UI_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ui', 'index.html')
_UI_CACHE = [0, b'']
STUB_PAGE = "<html><head><meta charset='utf-8'><title>АГЕНТ v15</title></head><body style='background:#1B1C1E;color:#E8E8E8;font:14px Segoe UI,sans-serif;padding:40px'><h2>ВИТРИНА НЕ НАЙДЕНА</h2><p>Положи index.html в D:\\AI\\tools\\agent\\data\\ui\\</p></body></html>"

if __name__ == '__main__':
    import atexit
    log('=== старт АГЕНТ v15 на %s ===' % HOSTNAME)
    pidfile = core.BASE / 'agent' / 'agent.pid'
    pidfile.write_text(str(os.getpid()), encoding='ascii')
    atexit.register(lambda: pidfile.unlink(missing_ok=True))
    threading.Thread(target=sched._scheduler, daemon=True).start()
    threading.Thread(target=sched._watchdog, daemon=True).start()
    try:
        ThreadingHTTPServer((HOST, PORT), Hd).serve_forever()
    finally:
        try:
            pidfile.unlink(missing_ok=True)
        except Exception:
            pass
