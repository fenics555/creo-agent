# -*- coding: utf-8 -*-
r"""FLEET: агенты офиса: кто жив, модель, блоки (через /status соседей)."""
import json
import urllib.request
import settings

DEFAULT_HOSTS = "192.168.88.159"

def _hosts():
    raw = settings.get("fleet_hosts") or DEFAULT_HOSTS
    return [h.strip() for h in str(raw).replace(";", ",").split(",") if h.strip()]

def _info(host, t=2):
    try:
        with urllib.request.urlopen("http://%s:8765/status" % host, timeout=t) as r:
            d = json.loads(r.read().decode("utf-8"))
        d["alive"] = True; d["host"] = host
        return d
    except Exception as e:
        return {"host": host, "alive": False, "error": str(e)[:60]}

def tool_fleet_status(**kw):
    out = []
    for d in (_info(h) for h in _hosts()):
        if not d.get("alive"):
            out.append("- %s: недоступен (%s)" % (d["host"], d.get("error")))
        else:
            out.append("- %s | жив | %s | блоков: %s | инструментов: %s"
                       % (d["host"], d.get("model"), d.get("blocks"), d.get("tools")))
    return "\n".join(out) or "список хостов пуст"

def tool_fleet_hosts(hosts="", **kw):
    if hosts:
        settings.set_val("fleet_hosts", hosts)
        return "хосты обновлены: %s" % hosts
    return "текущие хосты: %s" % ", ".join(_hosts())

TOOLS = [
    {"name": "fleet_status", "desc": "Флот: какие агенты в сети живы (модель, блоки, инструменты)", "params": {}, "approval": False, "fn": tool_fleet_status},
    {"name": "fleet_hosts", "desc": "Показать/задать список машин флота (IP через запятую)", "params": {"hosts": "список"}, "approval": False, "fn": tool_fleet_hosts},
]
