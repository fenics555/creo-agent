# -*- coding: utf-8 -*-
r"""Полный тест CREOSON: матрица живых функций на активной модели (только чтение)."""
import creo_tools as CT

def _probe(cmd, fn, data, check=None):
    j = CT.creo_call(cmd, fn, data, 20)
    if not CT.ok(j):
        return "✗ %s" % CT.errmsg(j)[:70]
    note = check(j.get("data")) if check else ""
    return "✓" + (" " + note if note else "")

def tool_creoson_test(**kw):
    st = CT.creo_call("connection", "is_creo_running", {}, 10)
    if not CT.ok(st) or not (st.get("data") or {}).get("running"):
        return "Creo не запущен — тест не гоняю: is_creo_running без Creo роняет JVM CREOSON. Сначала запусти Creo."
    act = CT.tool_get_active()
    out = ["ПОЛНЫЙ ТЕСТ CREOSON, активная: %s" % act]
    out.append("creo:pwd " + _probe("creo", "pwd", {}))
    out.append("creo:list_files " + _probe("creo", "list_files", {"filename": "*"}, lambda d: "%d файлов" % len(CT._flex_list(d))))
    out.append("creo:get_config " + _probe("creo", "get_config", {"name": "trail_dir"}))
    out.append("file:list " + _probe("file", "list", {}, lambda d: "%d в сессии" % len(CT._flex_list(d))))
    out.append("file:get_active " + _probe("file", "get_active", {}))
    out.append("file:exists " + _probe("file", "exists", {"file": act}))
    out.append("file:get_fileinfo " + _probe("file", "get_fileinfo", {"file": act}))
    out.append("file:open_errors " + _probe("file", "open_errors", {"file": act}))
    out.append("file:massprops " + _probe("file", "massprops", {"file": act}, lambda d: "масса %.1f кг" % (d.get("mass") or 0)))
    out.append("file:relations_get " + _probe("file", "relations_get", {"file": act}))
    def _pl(d):
        key = "paramlist" if d.get("paramlist") is not None else "param_list"
        return "%d параметров (ключ: %s)" % (len(d.get("paramlist") or d.get("param_list") or []), key)
    out.append("parameter:list " + _probe("parameter", "list", {"file": act}, _pl))
    out.append("parameter:exists " + _probe("parameter", "exists", {"file": act, "name": "ОБОЗНАЧЕНИЕ"}))
    out.append("dimension:list " + _probe("dimension", "list", {"file": act}))
    out.append("feature:list " + _probe("feature", "list", {"file": act}))
    out.append("bom:get_paths " + _probe("bom", "get_paths", {"file": act, "paths": False, "top_level": False, "exclude_inactive": True}, lambda d: "дерево ок"))
    out.append("familytable:list " + _probe("familytable", "list", {"file": act}))
    out.append("layer:list " + _probe("layer", "list", {"file": act}))
    out.append("note:list " + _probe("note", "list", {"file": act}))
    out.append("view:list " + _probe("view", "list", {"file": act}))
    out.append("geometry:bound_box " + _probe("geometry", "bound_box", {"file": act}))
    out.append("— пишущие НЕ дёргаем (под ✅): file:backup/rename/save, interface:export_pdf/mapkey, drawing:*")
    return "\n".join(out)

TOOLS = [
    {"name": "creoson_test", "desc": "Полный тест CREOSON: матрица живых функций на активной модели", "params": {}, "approval": False, "fn": tool_creoson_test},
]