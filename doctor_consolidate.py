# -*- coding: utf-8 -*-
import io, os
BASE = r"D:\AI\tools\agent"

# 1) матрица и сырой JSON переезжают в diagnostic_tools (TEST-блок)
dt = os.path.join(BASE, "diagnostic_tools.py")
s = io.open(dt, encoding="utf-8").read()
add = '''

# ---- матрица CREOSON (поглощено из creoson_test.py) ----
def tool_creoson_matrix(**kw):
    import creo_tools as CT
    act = CT.tool_get_active()
    if act.startswith("не знаю"):
        return "нет активной модели в Creo"
    probes = [
        ("creo", "pwd", {}), ("creo", "list_files", {"filename": "*"}),
        ("file", "list", {}), ("file", "get_active", {}), ("file", "exists", {"file": act}),
        ("file", "get_fileinfo", {"file": act}), ("file", "massprops", {"file": act}),
        ("file", "relations_get", {"file": act}), ("parameter", "list", {"file": act}),
        ("dimension", "list", {"file": act}), ("feature", "list", {"file": act}),
        ("bom", "get_paths", {"file": act, "paths": False, "top_level": False, "exclude_inactive": True}),
        ("familytable", "list", {"file": act}), ("layer", "list", {"file": act}),
        ("note", "list", {"file": act}), ("view", "list", {"file": act}),
        ("geometry", "bound_box", {"file": act}),
    ]
    out = ["МАТРИЦА CREOSON на %s:" % act]
    for cmd, fn, data in probes:
        j = CT.creo_call(cmd, fn, data, 20)
        out.append("%s %s:%s" % ("V" if CT.ok(j) else "X", cmd, fn) + ("" if CT.ok(j) else " - %s" % CT.errmsg(j)[:60]))
    out.append("- пишущие не дёргаем (под щитом): file:backup/rename/save, interface:export_pdf/mapkey")
    return "\\n".join(out)

# ---- сырой ответ CREOSON (поглощено из diag_creoson.py) ----
def tool_creoson_raw(cmd="parameter", fn="list", name="", **kw):
    import creo_tools as CT, json
    nm = name or CT.tool_get_active()
    j = CT.creo_call(cmd, fn, {"file": nm}, 20)
    return json.dumps(j, ensure_ascii=False)[:900]

TOOLS.append({"name": "creoson_matrix", "desc": "ТЕСТ: матрица живых функций CREOSON на активной модели", "params": {}, "approval": False, "fn": tool_creoson_matrix})
TOOLS.append({"name": "creoson_raw", "desc": "ТЕСТ: сырой JSON любого вызова CREOSON (cmd, fn, name)", "params": {"cmd": "группа", "fn": "функция", "name": "модель"}, "approval": False, "fn": tool_creoson_raw})
'''
if "creoson_matrix" in s:
    print("[~] матрица уже в diagnostic_tools")
elif "TOOLS = [" in s or "TOOLS=[" in s:
    s += add
    io.open(dt, "w", encoding="utf-8").write(s)
    print("[+] diagnostic_tools поглотил матрицу и raw")
else:
    print("[x] в diagnostic_tools не найден TOOLS — проверь вручную")

# 2) удаляем поглощённые блоки
for fn in ("creoson_test.py", "diag_creoson.py"):
    p = os.path.join(BASE, fn)
    if os.path.exists(p):
        os.remove(p); print("[+] удалён %s" % fn)

# 3) сторож реже поллит is_creo_running (не насиловать JVM)
ct = os.path.join(BASE, "creo_tools.py")
c = io.open(ct, encoding="utf-8").read()
if "time.sleep(20)" in c:
    c = c.replace("time.sleep(20)", "time.sleep(60)", 1)
    io.open(ct, "w", encoding="utf-8").write(c)
    print("[+] watch: поллинг 60 сек")

# 4) fleet_tools.py — настоящий флот вместо doctor7
FLEET = '''# -*- coding: utf-8 -*-
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
    return "\\n".join(out) or "список хостов пуст"

def tool_fleet_hosts(hosts="", **kw):
    if hosts:
        settings.set_val("fleet_hosts", hosts)
        return "хосты обновлены: %s" % hosts
    return "текущие хосты: %s" % ", ".join(_hosts())

TOOLS = [
    {"name": "fleet_status", "desc": "Флот: какие агенты в сети живы (модель, блоки, инструменты)", "params": {}, "approval": False, "fn": tool_fleet_status},
    {"name": "fleet_hosts", "desc": "Показать/задать список машин флота (IP через запятую)", "params": {"hosts": "список"}, "approval": False, "fn": tool_fleet_hosts},
]
'''
io.open(os.path.join(BASE, "fleet_tools.py"), "w", encoding="utf-8").write(FLEET)
print("[+] fleet_tools.py = настоящий флот")
print("ГОТОВО: .\\AI_RESTART.bat, потом GIT_SYNC")