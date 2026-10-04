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
import agent_sched
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
    import sys as _sys
    _PID = os.getpid()
    log("=== старт АГЕНТ v15 на %s ===" % socket.gethostname())
    # ДИАГНОСТИКА ТИХОЙ СМЕРТИ (04.10.2026, крах agent_silent-death_noport-8765): агент умер
    # без единой строки в журнале, и по нему нельзя было понять — сам упал или убит снаружи.
    # Три факта теперь пишутся всегда: PID старта, PID завершения, код возврата.
    log("ДИАГНОСТИКА: старт, PID %d, python %s" % (_PID, _sys.version.split()[0]))
    _roots = read_kb_roots()
    log("kb_roots: %d папок" % len(_roots))
    pidfile = core.BASE / "agent" / "agent.pid"

    def _bye():
        # Сработает и при исключении, и при нормальном выходе. НЕ сработает при `taskkill /F`
        # и жёстком убийстве процесса — именно это и отличает «упал» от «убили снаружи».
        log("ДИАГНОСТИКА: завершение, PID %d, код %s" % (_PID, str(_bye.code)))

    _bye.code = 0
    pidfile.write_text(str(_PID), encoding="ascii")
    atexit.register(lambda: pidfile.unlink(missing_ok=True))
    atexit.register(_bye)
    threading.Thread(target=agent_sched._scheduler, daemon=True).start()
    threading.Thread(target=agent_sched._watchdog, daemon=True).start()
    try:
        from http.server import ThreadingHTTPServer
        ThreadingHTTPServer((HOST, PORT), Hd).serve_forever()
    except BaseException as e:
        _bye.code = 1
        log("ДИАГНОСТИКА: АГЕНТ УПАЛ, PID %d, %s: %s"
            % (_PID, type(e).__name__, e))
        raise
    finally:
        log("ДИАГНОСТИКА: сервер остановлен, PID %d, код %s" % (_PID, str(_bye.code)))
        try: pidfile.unlink(missing_ok=True)
        except Exception: pass
