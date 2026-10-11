# -*- coding: utf-8 -*-
r"""services_live — живая проверка стека дома (Волна 5.1 плана, только чтение).

Закрывает дефект «16/16 зелёно при мёртвом агенте»: checks.py смотрит ФАЙЛЫ, а этот
инструмент — ЖИВЫЕ службы (слушает ли порт, отвечает ли /health, совпадает ли agent.pid
с живым процессом). Образец — `ctl.py status()` (alive(port) + verify_agent).

Только чтение: ничего не поднимает, не останавливает, не пишет.
Код возврата: 0 — все обязательные службы живы · 1 — что-то обязательное мертво.

Запуск:  services_live.py            (проверить обязательные службы из настроек)
         services_live.py --json      (машиночитаемо для checks.py)
Настройки — settings\settings.json (ключ services: имя→порт→обязательность). Абс. путей в
коде нет (канон №2): порты — из настроек, агент ищем по месту модуля.
"""
import io
import json
import os
import socket
import sys
import time
import urllib.request
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
AGENT = HERE.parent                              # tools\agent
PID_FILE = AGENT / "agent.pid"


def settings():
    d = {}
    sf = HERE / "settings" / "settings.json"
    try:
        if sf.exists():
            d = json.loads(sf.read_text(encoding="utf-8"))
    except Exception:
        d = {}
    return d


def alive(port, host="127.0.0.1", timeout=1.0):
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except Exception:
        return False


def http_ok(port, path="/health", timeout=2.0):
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d%s" % (port, path),
                                    timeout=timeout) as r:
            return r.status in (200, 401)   # 401 = слушает и проверяет вход, это тоже «жив»
    except Exception:
        return False


def default_services():
    """Службы дома: имя → порт → обязательно?. Порты из образца ctl.py status()."""
    s = settings()
    return s.get("services") or [
        {"name": "агент", "port": 8765, "required": True, "health": "/health"},
        {"name": "copy", "port": 8000, "required": False, "health": ""},
        {"name": "CREOSON", "port": 8080, "required": False, "health": ""},
        {"name": "Ollama", "port": 11434, "required": False, "health": ""},
    ]


def agent_pid_ok():
    """agent.pid = живому процессу (по образцу ctl.verify_agent: порт + pid)."""
    if not PID_FILE.exists():
        return False, "agent.pid нет"
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip() or 0)
    except Exception:
        return False, "agent.pid бит"
    if pid <= 0:
        return False, "agent.pid пуст"
    # Живость процесса: порт 8765 слушает И этот PID есть. Проверяем через psutil-free способ.
    owner = _port_owner(8765)
    if owner is None:
        return False, "порт 8765 не слушает (agent.pid=%d)" % pid
    if owner and owner != pid:
        return False, "порт держит %s, в agent.pid %d — не совпадают" % (owner, pid)
    return True, "порт 8765 держит PID %d (совпадает)" % pid


def _port_owner(port):
    """PID процесса, слушающего порт (Windows: netstat; иначе None)."""
    try:
        import subprocess
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "(Get-NetTCPConnection -LocalPort %d -State Listen "
                              "-ErrorAction SilentlyContinue).OwningProcess" % port],
                             capture_output=True, text=True, timeout=15).stdout.strip()
        for line in out.splitlines():
            line = line.strip()
            if line.isdigit():
                return int(line)
    except Exception:
        pass
    return None


def check():
    rows = []
    ok_all = True
    for svc in default_services():
        port = int(svc.get("port", 0))
        a = alive(port)
        h = http_ok(port, svc.get("health") or "/health") if (a and svc.get("health")) else None
        req = bool(svc.get("required"))
        good = a if h is None else (a and h)
        if req and not good:
            ok_all = False
        rows.append({"name": svc.get("name"), "port": port, "alive": a,
                     "health": h, "required": req, "good": good})
    pid_ok, pid_why = agent_pid_ok()
    # Агент — обязателен: если pid-приёмка провалилась, общий вердикт красный.
    if not pid_ok:
        ok_all = False
    return {"ok": ok_all, "services": rows, "agent_pid": {"ok": pid_ok, "why": pid_why}}


def render(res):
    lines = ["=== ЖИВАЯ ПРОВЕРКА СТЕКА ==="]
    for r in res["services"]:
        mark = "жив" if r["good"] else ("МЁРТВ" if r["alive"] is False else "health FAIL")
        req = " (обязат.)" if r["required"] else ""
        hh = "" if r["health"] is None else (" health:%s" % r["health"])
        lines.append("  %-10s :%-6d %s%s%s" % (r["name"], r["port"], mark, req, hh))
    ap = res["agent_pid"]
    lines.append("  agent.pid: %s — %s" % ("OK" if ap["ok"] else "ПРОВАЛ", ap["why"]))
    lines.append("")
    lines.append("ВЕРДИКТ: %s" % ("СТЕК ЖИВ" if res["ok"] else "СТЕК НЕ ПОЛНОСТЬЮ ЖИВ"))
    return lines


def main(argv):
    as_json = "--json" in argv
    res = check()
    if as_json:
        print(json.dumps(res, ensure_ascii=False))
    else:
        for ln in render(res):
            print(ln)
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
