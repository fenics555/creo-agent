# -*- coding: utf-8 -*-
r"""
АГЕНТ v12 — БЛОК CREO (creo_tools.py)
Чтение живого Creo через CREOSON: статус, сессия, параметры, отношения,
масса, BOM, аудит, трейлы. Пишущие операции — в creo_ops_tools.
watch: тихий полл, trace только при смене состояния (не спамит лог).
"""
import json, re, time, threading, urllib.request
from pathlib import Path
from core import log, trace
import settings
import scanner

CREOSON_URL = "http://127.0.0.1:8080/creoson"
CREO_SESSION = ""
RUNNING = False

def _post(body, t=15):
    r = urllib.request.Request(CREOSON_URL, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=t))

def connect():
    global CREO_SESSION
    j = _post({"command": "connection", "function": "connect", "data": {}})
    CREO_SESSION = j.get("sessionId") or CREO_SESSION
    return CREO_SESSION

def creo_raw(cmd, fn, data=None, t=15):
    if not CREO_SESSION: connect()
    body = {"sessionId": CREO_SESSION, "command": cmd, "function": fn, "data": data or {}}
    j = _post(body, t)
    if (j.get("status") or {}).get("error"):
        connect(); body["sessionId"] = CREO_SESSION
        j = _post(body, t)
    return j

def creo_call(cmd, fn, data=None, t=15):
    try:
        return creo_raw(cmd, fn, data, t)
    except Exception as e:
        return {"status": {"error": True, "message": str(e)}}

def ok(j): return bool(j) and not (j.get("status") or {}).get("error")
def errmsg(j): return (j.get("status") or {}).get("message") or "неизвестная ошибка"

def watch():
    global RUNNING
    prev = None
    while True:
        try:
            j = _post({"command": "connection", "function": "is_creo_running", "data": {}}, 5)
            RUNNING = (not (j.get("status") or {}).get("error")) and bool((j.get("data") or {}).get("running"))
        except Exception:
            RUNNING = False
        if RUNNING != prev:
            trace("CREOSON watch", "Creo запущен: %s" % ("ДА" if RUNNING else "НЕТ"))
            prev = RUNNING
        time.sleep(20)
threading.Thread(target=watch, daemon=True).start()

def _flex_list(d):
    if isinstance(d, list): return d
    d = d or {}
    return d.get("file_list") or d.get("filelist") or d.get("files") or []

def tool_status(**kw):
    try:
        j = _post({"command": "connection", "function": "is_creo_running", "data": {}}, 5)
        run = bool((j.get("data") or {}).get("running"))
    except Exception:
        return "CREOSON молчит (порт 8080). Лечение: CREO-START.bat дебаг-клик."
    return "CREOSON: жив; Creo запущен: %s" % ("ДА" if run else "НЕТ")

def tool_session(**kw):
    j = creo_call("file", "list", {}, 10)
    lst = _flex_list(j.get("data")) if ok(j) else []
    return "\n".join("• %s" % x for x in lst) or "(пусто)"

def tool_get_active(**kw):
    j = creo_call("file", "get_active", {}, 10)
    d = j.get("data") if ok(j) else None
    if isinstance(d, dict): d = d.get("file") or d.get("name") or ""
    return str(d or "") or "не знаю активную модель"

def tool_pwd(**kw):
    j = creo_call("creo", "pwd", {}, 10)
    d = j.get("data") if ok(j) else None
    if isinstance(d, dict): d = d.get("directory") or d.get("dirname") or ""
    return str(d or "") or "не узнал папку"

def tool_list_files(mask="*.*", **kw):
    j = creo_call("creo", "list_files", {"filename": mask}, 15)
    lst = _flex_list(j.get("data")) if ok(j) else []
    return "\n".join(str(x) for x in lst) or "пусто"

def tool_find_model(q="", **kw):
    hits = scanner.name_search(q or "", 8)
    return "\n".join("• %s" % h for h in hits) or "не нашёл в индексе"

def tool_get_params(name="", **kw):
    nm = name or tool_get_active()
    j = creo_call("parameter", "list", {"file": nm}, 20)
    if not ok(j): return "ошибка параметров: %s" % errmsg(j)
    pl = (j.get("data") or {}).get("param_list") or []
    return "\n".join("• %s (%s) = %s" % (p.get("name"), p.get("type"), p.get("value")) for p in pl) or "параметров нет"

def tool_get_relations(name="", **kw):
    nm = name or tool_get_active()
    j = creo_call("file", "relations_get", {"file": nm}, 20)
    if not ok(j): return "ошибка отношений: %s" % errmsg(j)
    d = j.get("data")
    return (d if isinstance(d, str) else (d or {}).get("relations") or "") or "отношений нет"

def tool_get_mass(name="", **kw):
    nm = name or tool_get_active()
    j = creo_call("file", "massprops", {"file": nm}, 30)
    if not ok(j): return "ошибка massprops: %s" % errmsg(j)
    d = j.get("data") or {}
    return "масса %.2f кг, объём %.0f мм3, площадь %s мм2" % (
        d.get("mass") or 0, d.get("volume") or 0, d.get("area") or d.get("surface_area") or 0)

def tool_get_bom(name="", **kw):
    nm = name or tool_get_active()
    j = creo_call("bom", "get_paths", {"file": nm, "paths": False, "top_level": False, "exclude_inactive": True}, 30)
    if not ok(j): return "ошибка BOM: %s" % errmsg(j)
    root = j.get("data") or {}
    out, stack = [], [(root, 0)]
    while stack:
        node, lvl = stack.pop()
        if isinstance(node, dict):
            f = node.get("file") or ""
            if f: out.append("  " * lvl + "• %s" % f)
            for ch in (node.get("children") or []): stack.append((ch, lvl + 1))
        elif isinstance(node, list):
            for ch in node: stack.append((ch, lvl))
    return "\n".join(out) or "дерево пусто"

def tool_open_errors(name="", **kw):
    nm = name or tool_get_active()
    j = creo_call("file", "open_errors", {"file": nm}, 15)
    if not ok(j): return "ошибок открытия нет (или модель не открыта)"
    return str(j.get("data")) or "ошибок открытия нет"

def tool_read_trail(lines=60, **kw):
    dirs = []
    v = ((creo_call("creo", "get_config", {"name": "trail_dir"}, 10) or {}).get("data") or {}).get("values") or []
    if v: dirs.append(v[0])
    dirs.append(r"D:\PTC\CREO-LOCAL-SETUP\TEMP\trails")
    files = []
    for d in dirs:
        try: files += list(Path(d).glob("trail.txt.*"))
        except Exception: pass
    if not files: return "трейлов не нашёл"
    p = max(files, key=lambda f: f.stat().st_mtime)
    txt = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    return "\n".join(txt[-int(lines or 60):])

def tool_open(name="", **kw):
    if not name: return "укажи имя модели или чертежа"
    j = creo_call("file", "open", {"file": name, "display": True}, 30)
    return "открыто: %s" % name if ok(j) else "не открылось: %s" % errmsg(j)

def tool_audit_folder(**kw):
    limit = int(settings.get("audit_limit") or 20)
    req = list(settings.get("audit_params") or ["ОБОЗНАЧЕНИЕ", "НАИМЕНОВАНИЕ", "MASS"])
    wd = tool_pwd()
    if not wd: return "не узнал рабочую папку"
    sess = set(_flex_list((creo_call("file", "list", {}, 10) or {}).get("data")))
    seen, names = set(), []
    _mre = re.compile(r"\.(prt|asm)(\.\d+)?$", re.I)
    lst = _flex_list((creo_call("creo", "list_files", {"filename": "*"}, 20) or {}).get("data"))
    if not lst:
        lst = _flex_list((creo_call("creo", "list_files", {"filename": "."}, 20) or {}).get("data"))
    for x in lst:
        s2 = str(x)
        if not _mre.search(s2):
            continue
        base = _mre.sub("", s2)
        if base not in seen:
            seen.add(base); names.append((base, s2))
    names = names[:limit]
    out = ["АУДИТ папки %s (%d моделей):" % (wd, len(names))]
    for base, fn in names:
        is_asm = base.lower().endswith(".asm")
        was = fn in sess
        creo_call("file", "open", {"file": fn, "display": False}, 30)
        probs = []
        jp = creo_call("parameter", "list", {"file": fn}, 20)
        have = set(p.get("name") for p in ((jp.get("data") or {}).get("param_list") or [])) if ok(jp) else set()
        for r in req:
            if r == "MASS" and is_asm: continue
            if r not in have: probs.append("нет %s" % r)
        rel = tool_get_relations(fn)
        if "нет" in rel[:12]: probs.append("нет relations")
        if not was: creo_call("file", "erase", {"file": fn}, 15)
        out.append("• %s — %s" % (base, ", ".join(probs) if probs else "ОК"))
    return "\n".join(out)

TOOLS = [
    {"name": "creo_status", "desc": "Статус CREOSON и запущен ли Creo", "params": {}, "approval": False, "fn": tool_status},
    {"name": "creo_session", "desc": "Список моделей, открытых в Creo", "params": {}, "approval": False, "fn": tool_session},
    {"name": "creo_get_active", "desc": "Имя активной модели в Creo", "params": {}, "approval": False, "fn": tool_get_active},
    {"name": "creo_pwd", "desc": "Текущая рабочая папка Creo", "params": {}, "approval": False, "fn": tool_pwd},
    {"name": "creo_list_files", "desc": "Список файлов в рабочей папке Creo по маске", "params": {"mask": "маска"}, "approval": False, "fn": tool_list_files},
    {"name": "creo_find_model", "desc": "Поиск модели по имени в индексе", "params": {"q": "имя/шифр"}, "approval": False, "fn": tool_find_model},
    {"name": "creo_get_params", "desc": "Все параметры модели Creo", "params": {"name": "имя модели"}, "approval": False, "fn": tool_get_params},
    {"name": "creo_get_relations", "desc": "Отношения (уравнения) модели", "params": {"name": "имя модели"}, "approval": False, "fn": tool_get_relations},
    {"name": "creo_get_mass", "desc": "Масса/объём/площадь модели", "params": {"name": "имя модели"}, "approval": False, "fn": tool_get_mass},
    {"name": "creo_get_bom", "desc": "Дерево компонентов сборки", "params": {"name": "имя сборки"}, "approval": False, "fn": tool_get_bom},
    {"name": "creo_open_errors", "desc": "Ошибки открытия модели (для поиска битых файлов)", "params": {"name": "имя модели"}, "approval": False, "fn": tool_open_errors},
    {"name": "creo_read_trail", "desc": "Хвост трейл-файла Creo: ошибки, таймауты", "params": {"lines": "сколько строк"}, "approval": False, "fn": tool_read_trail},
    {"name": "creo_open", "desc": "Открыть модель или чертёж в Creo", "params": {"name": "имя файла"}, "approval": False, "fn": tool_open},
    {"name": "creo_audit_folder", "desc": "Аудит рабочей папки Creo по эталону КБ", "params": {}, "approval": False, "fn": tool_audit_folder},
]

try:
    import trail_tools as TT
    TOOLS.append({"name": "creo_trail_analyze", "desc": "Разбор трейлов Creo: простой, болезни, журнал", "params": {"count": "сколько трейлов"}, "approval": False, "fn": TT.tool_trail_analyze})
except Exception as e:
    log("creo_tools: trail не прицепился: %s" % e)