# -*- coding: utf-8 -*-
"""АГЕНТ v15 — agent.py (тонкий вход)
Хост: HTTP-сервер + потоки планировщика и сторожа.
Вся логика: loop.py (ходовый цикл), http_handlers.py (маршруты), sched.py (ночь/сторож).
"""
import os, socket, threading
import core
from core import log
import settings
import pdf_tools
import loop
import sched
from http_handlers import Hd

HOST, PORT = "0.0.0.0", 8765
UI_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui", "index.html")


def read_kb_roots():
    """Чтение kb_roots.txt: одна папка в строке, '#' — комментарий."""
    roots = []
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kb_roots.txt")
    try:
        with open(p, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    roots.append(line)
    except Exception as e:
        log("kb_roots read err: %s" % e)
    return roots


if __name__ == "__main__":
    import atexit
    log("=== старт АГЕНТ v15 на %s ===" % socket.gethostname())
    _roots = read_kb_roots()
    log("kb_roots: %d папок" % len(_roots))
    pidfile = core.BASE / "agent" / "agent.pid"
    pidfile.write_text(str(os.getpid()), encoding="ascii")
    atexit.register(lambda: pidfile.unlink(missing_ok=True))
    threading.Thread(target=sched._scheduler, daemon=True).start()
    threading.Thread(target=sched._watchdog, daemon=True).start()
    try:
        from http.server import ThreadingHTTPServer
        ThreadingHTTPServer((HOST, PORT), Hd).serve_forever()
    finally:
        try: pidfile.unlink(missing_ok=True)
        except Exception: pass
