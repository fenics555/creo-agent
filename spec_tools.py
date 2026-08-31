# -*- coding: utf-8 -*-
r"""ГОСТ-спецификация в Excel: чтение и создание через creo-параметры."""
import os
import base64
import json
import core
from core import log

try:
    import excel_import as EI
    import excel_export as EE
    _OK = True
except Exception as _e:
    _OK = False
    _ERR = str(_e)

def _creoson(session, command, function, data=None):
    import urllib.request
    body = {"command": command, "function": function, "data": data or {}}
    if session:
        body["sessionId"] = session
    req = urllib.request.Request("http://127.0.0.1:8080/creoson",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"status": {"error": True, "message": str(e)}}

def _get_session():
    r = _creoson(None, "connection", "connect", {})
    if r.get("status", {}).get("error"):
        return None, r.get("status", {}).get("message")
    return r.get("data", {}).get("sessionId"), None

def _param_value(plist, names):
    for n in names:
        for p in plist:
            if str(p.get("name", "")).upper() == n.upper():
                return p.get("value")
    return None

def tool_spec_read(path="", **kw):
    if not _OK:
        return "модуль не загружен: %s" % _ERR
    p = (path or "").strip().strip('"')
    if not p:
        return "укажи путь к XLSX"
    if not os.path.isfile(p):
        return "файл не найден: %s" % p
    try:
        with open(p, "rb") as f:
            sections, rows = EI.read_specification_xlsx(f.read())
    except ValueError as e:
        return "ошибка XLSX: %s" % e
    out = ["разделы: %s" % ", ".join(sections) if sections else "(без разделов)"]
    out.append("строк: %d" % len(rows))
    for r in rows[:20]:
        out.append("- %s | %s | %s | %s | %s" % (
            r.get("section", ""), r.get("designation", ""),
            r.get("name", ""), r.get("quantity", ""), r.get("note", "")))
    if len(rows) > 20:
        out.append("...и ещё %d" % (len(rows) - 20))
    return "\n".join(out)

def tool_spec_create_active(**kw):
    if not _OK:
        return "модуль не загружен: %s" % _ERR
    sid, err = _get_session()
    if not sid:
        return "CREOSON недоступен: %s" % err
    # активная сборка
    a = _creoson(sid, "file", "get_active", {})
    active = (a.get("data") or {}).get("file") or a.get("data") or ""
    if not active:
        return "нет активной сборки в Creo"
    active = str(active).replace("\\", "/").split("/")[-1].split(".")[0] + ".asm"
    # рабочая папка
    pwd = _creoson(sid, "creo", "pwd", {})
    directory = (pwd.get("data") or {}).get("directory") or pwd.get("data") or ""
    directory = str(directory)
    # параметры сборки
    pl = _creoson(sid, "parameter", "list", {"file": active})
    params = (pl.get("data") or {}).get("param_list") or []
    designation = _param_value(params, ["ОБОЗНАЧЕНИЕ", "DESIGNATION", "ШИФР"]) or active.replace(".asm", "")
    name = _param_value(params, ["НАИМЕНОВАНИЕ", "NAME"]) or active
    # компоненты первого уровня (bom)
    bom = _creoson(sid, "bom", "get_paths", {"file": active, "paths": False, "top_level": True})
    tree = bom.get("data") or {}
    children = tree.get("children") or []
    rows = []
    seen = set()
    for c in children:
        f = str(c.get("file", "")).lower()
        if f in seen or not f:
            continue
        seen.add(f)
        # параметры компонента
        cp = _creoson(sid, "parameter", "list", {"file": c.get("file")})
        cp_params = (cp.get("data") or {}).get("param_list") or []
        d = _param_value(cp_params, ["ОБОЗНАЧЕНИЕ", "DESIGNATION"]) or ""
        n = _param_value(cp_params, ["НАИМЕНОВАНИЕ", "NAME"]) or f
        q = c.get("quantity") or 1
        rows.append({"section": "Детали", "format": "А4", "zone": "",
                     "position": "", "designation": d, "name": n,
                     "quantity": str(q), "note": ""})
    sections = ["Детали"] if rows else []
    try:
        out, n_rows, n_img = EE.create_xlsx(
            directory=directory, designation=designation,
            sections=json.dumps(sections), rows=json.dumps(rows),
            images=json.dumps([]), assembly_model_name=active)
    except ValueError as e:
        return "не создался: %s" % e
    return "спецификация создана: %s (строк: %d, картинок: %d)" % (out, n_rows, n_img)

TOOLS = [
    {"name": "spec_read", "desc": "Прочитать ГОСТ-спецификацию из XLSX-файла (разделы, строки)",
     "params": {"path": "путь к xlsx"}, "approval": False, "fn": tool_spec_read},
    {"name": "spec_create_active", "desc": "Создать ГОСТ-спецификацию по активной сборке Creo (XLSX в папку сборки)",
     "params": {}, "approval": False, "fn": tool_spec_create_active},
]