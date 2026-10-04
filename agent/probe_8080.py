# -*- coding: utf-8 -*-
r"""probe_8080 - ПРОБА: кто живёт на 8080 и отвечает ли CREOSON (04.10.2026).

WHY: apply.py проверяет порт 8080 как признак CREOSON, но на этой машине там
слушает java.exe (PID 17220) - это может быть и CREOSON, и агент дома. Не
выдумываем: спрашиваем сам CREOSON живым запросом и пишем ответ в файл.
"""
import json
import sys
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent / "probe_8080_out.txt"


def post(url, body, timeout=8):
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def main():
    lines = []
    # 1. живой ли вообще порт
    try:
        import socket
        s = socket.socket()
        s.settimeout(3)
        s.connect(("127.0.0.1", 8080))
        s.close()
        lines.append("ПОРТ 8080: ОТВЕЧАЕТ")
    except Exception as e:
        lines.append("ПОРТ 8080: НЕ ОТВЕЧАЕТ (%s)" % e)
        OUT.write_text("\n".join(lines), encoding="utf-8")
        return 2

    # 2. спросить сам CREOSON: жив ли Creo
    for fn in ("connection", "is_creo_running"):
        try:
            txt = post("http://127.0.0.1:8080/creoson",
                       {"command": fn, "function": "is_creo_running",
                        "data": {}, "sessionId": ""})
            lines.append("CREOSON %s -> %s" % (fn, txt[:300]))
        except Exception as e:
            lines.append("CREOSON %s -> ОШИБКА %s" % (fn, e))

    # 3. какая это служба: /ask агента или CREOSON
    try:
        txt = post("http://127.0.0.1:8080/ask", {"q": "кто ты"})
        lines.append("POST /ask -> %s" % txt[:200])
    except Exception as e:
        lines.append("POST /ask -> ОШИБКА (%s)" % e)

    OUT.write_text("\n".join(lines), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())