# -*- coding: utf-8 -*-
r"""dev\creoson_probe.py - ЖИВАЯ ПРОБА CREOSON (долг волны 7): что сервер реально умеет.

Ничего не пишет в модели. Только читает состояние: запущен ли Creo, видна ли модель.
Вывод честный: если Creo не запущен - запись параметров невозможна, и это пишется прямо.
"""
import io
import sys
from pathlib import Path

AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    print("ЖИВАЯ ПРОБА CREOSON")
    import socket
    s = socket.socket()
    s.settimeout(3)
    try:
        s.connect(("127.0.0.1", 8080))
        print("  порт 8080: ОТВЕЧАЕТ")
    except Exception as e:
        print("  порт 8080: НЕ ОТВЕЧАЕТ (%s)" % e)
        return 2
    finally:
        s.close()

    import subprocess
    ps = subprocess.run(["tasklist", "/FI", "IMAGENAME eq parametric.exe"],
                        capture_output=True, text=True, timeout=20)
    has_creo = "parametric.exe" in ps.stdout
    print("  Creo (parametric.exe): %s" % ("ЗАПУЩЕН" if has_creo else "НЕ ЗАПУЩЕН"))

    try:
        import creo_tools as CT
        act = CT.tool_get_active()
        print("  активная модель CREOSON: %s" % (act or "—"))
    except Exception as e:
        print("  активная модель: не прочитана (%s)" % e)

    if not has_creo:
        print("ВЕРДИКТ: CREOSON поднят, но Creo не запущен.")
        print("  Запись параметров (parameter:set) без parametric.exe невозможна.")
        print("  Это НЕ «прогон успешен» - живой прогон записи не выполнен.")
        return 3
    print("ВЕРДИКТ: CREOSON и Creo живы - можно пробовать запись на копии.")
    return 0


if __name__ == "__main__":
    sys.exit(main())