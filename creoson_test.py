# -*- coding: utf-8 -*-
r"""Полный тест CREOSON: матрица живых функций на активной модели."""
import creo_tools as CT

def tool_creoson_test(**kw):
    act = CT.tool_get_active()
    if act.startswith("не знаю"):
        return "нет активной модели в Creo"
    probes = [
        ("connection", "is_creo_running", {}),
        ("creo", "pwd", {}),
        ("creo", "list_files", {"filename": "*"}),
        ("creo", "get_config", {"name": "trail_dir"}),
        ("file", "list", {}),
        ("file", "get_active", {}),
        ("file", "exists", {"file": act}),
        ("file", "get_fileinfo", {"file": act}),
        ("file", "open_errors", {"file": act}),
        ("file", "massprops", {"file": act}),
        ("file", "relations_get", {"file": act}),
        ("parameter", "list", {"file": act}),
        ("parameter", "exists", {"file": act, "name": "ОБОЗНАЧЕНИЕ"}),
        ("dimension", "list", {"file": act}),
        ("feature", "list", {"file": act}),
        ("bom", "get_paths", {"file": act, "paths": False, "top_level": False, "exclude_inactive": True}),
        ("familytable", "list", {"file": act}),
        ("layer", "list", {"file": act}),
        ("note", "list", {"file": act}),
        ("view", "list", {"file": act}),
        ("geometry", "bound_box", {"file": act}),
    ]
    out = ["ТЕСТ CREOSON на %s:" % act]
    for cmd, fn, data in probes:
        j = CT.creo_call(cmd, fn, data, 20)
        if CT.ok(j):
            d = j.get("data")
            n = len(d) if isinstance(d, (list, dict)) else (1 if d not in (None, "") else 0)
            out.append("✓ %s:%s — ОК (данных: %s)" % (cmd, fn, n))
        else:
            out.append("✗ %s:%s — %s" % (cmd, fn, CT.errmsg(j)[:80]))
    out.append("— пишущие (не дёргаем, есть под ✅): file:backup/rename/save, interface:export_pdf/mapkey, drawing:*")
    return "\n".join(out)

TOOLS = [
    {"name": "creoson_test", "desc": "Полный тест CREOSON: матрица живых функций на активной модели", "params": {}, "approval": False, "fn": tool_creoson_test},
]