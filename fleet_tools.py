# -*- coding: utf-8 -*-
r"""FLEET: агенты офиса: кто жив, кто в Creo, кто когда запускал (трейлы)."""
import json
import urllib.request
import settings

DEFAULT_HOSTS = "192.168.88.159"

def _hosts():
    raw = settings.get("fleet_hosts") or DEFAULT_HOSTS
    return [h.strip() for h in str(raw).replace(";", ",").split(",") if h.strip()]

def _info(host, t=2):
    try:
        with urllib.request.urlopen("http://%s:8765/fleet/info" % host, timeout=t) as r:
            d = json.loads(r.read().decode("utf-8"))
        d["alive"] = True
        d["host"] = host
        return d
    except Exception as e:
        return {"host": host, "alive": False, "error": str(e)[:60]}

def tool_fleet_status(**kw):
    out = []
    for d in (_info(h) for h in _hosts()):
        if not d.get("alive"):
            out.append("- %s: недоступен (%s)" % (d["host"], d.get("error")))
            continue
        out.append("- %s | юзер: %s | агент жив | %s | блоков: %s | инструментов: %s"
                   % (d["host"], d.get("user") or "?", d.get("model"), d.get("blocks"), d.get("tools")))
        tr = (d.get("trails") or "").strip()
        if tr:
            lines = [l.strip() for l in tr.splitlines() if l.strip()]
            out.append("  трейлы: " + " | ".join(lines[-3:]))
    return "\n".join(out) or "список хостов пуст"

def tool_fleet_hosts(hosts="", **kw):
    if hosts:
        settings.set_val("fleet_hosts", hosts)
        return "хосты обновлены: %s" % hosts
    return "текущие хосты: %s" % ", ".join(_hosts())

TOOLS = [
    {"name": "fleet_status", "desc": "Флот: кто жив, какой юзер, в Creo ли, последние трейлы по каждой машине", "params": {}, "approval": False, "fn": tool_fleet_status},
    {"name": "fleet_hosts", "desc": "Показать/задать список машин флота (IP через запятую)", "params": {"hosts": "список IP, пусто = показать"}, "approval": False, "fn": tool_fleet_hosts},
]