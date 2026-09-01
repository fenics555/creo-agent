# -*- coding: utf-8 -*-
import io
p = r"D:\AI\tools\agent\diagnostic_tools.py"
s = io.open(p, encoding="utf-8").read()
marks = ["# ---- CREOSON", "# ==== CREOSON", "def tool_creoson_matrix", "def tool_creoson_raw",
         "def tool_write_test", "def tool_creoson_write_test", "_orig_raw = CT.creo_raw",
         "import creo_tools as CT"]
idx = [i for i in (s.find(m) for m in marks) if i >= 0]
cut = min(idx) if idx else len(s)
s = s[:cut]

NEW = r'''
# ==== CREOSON: ОДИН полный тест; всё в diag_creoson.log ====
import os as _os
import re as _re
import time as _time
import json as _json
from pathlib import Path as _Path
import creo_tools as CT

def _fw(line):
    try:
        with open(_Path(core.BASE) / "diag_creoson.log", "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (_time.strftime("%m-%d %H:%M:%S"), line))
    except Exception:
        pass

if getattr(CT.creo_raw, "__name__", "") != "_logged_raw":
    _orig_raw = CT.creo_raw
    def _logged_raw(cmd, fn, data=None, t=15):
        _fw(">> %s:%s %s" % (cmd, fn, _json.dumps(data or {}, ensure_ascii=False)[:200]))
        j = _orig_raw(cmd, fn, data, t)
        _fw("<< %s:%s %s" % (cmd, fn, "OK" if CT.ok(j) else "ERR " + str(CT.errmsg(j))[:80]))
        return j
    CT.creo_raw = _logged_raw

def tool_creoson_full_test(**kw):
    out = ["ПОЛНЫЙ ТЕСТ CREOSON (чтение -> запись на копии -> очистка):"]
    def rep(line):
        out.append(line); _fw(line)
    act = CT.tool_get_active()
    rep("== старт, активная: %s ==" % act)
    reads = [
        ("creo", "pwd", {}), ("creo", "list_files", {"filename": "*"}),
        ("creo", "get_config", {"name": "trail_dir"}),
        ("file", "list", {}), ("file", "get_active", {}), ("file", "exists", {"file": act}),
        ("file", "get_fileinfo", {"file": act}), ("file", "massprops", {"file": act}),
        ("file", "relations_get", {"file": act}), ("file", "open_errors", {"file": act}),
        ("parameter", "list", {"file": act}), ("parameter", "exists", {"file": act, "name": "ОБОЗНАЧЕНИЕ"}),
        ("dimension", "list", {"file": act}), ("feature", "list", {"file": act}),
        ("bom", "get_paths", {"file": act, "paths": False, "top_level": False, "exclude_inactive": True}),
        ("familytable", "list", {"file": act}), ("layer", "list", {"file": act}),
        ("note", "list", {"file": act}), ("view", "list", {"file": act}),
        ("geometry", "bound_box", {"file": act}),
    ]
    for cmd, fn, data in reads:
        j = CT.creo_call(cmd, fn, data, 20)
        rep("чтение %-20s %s" % (cmd + ":" + fn, "OK" if CT.ok(j) else "ERR " + str(CT.errmsg(j))[:60]))
    d = str(_Path(core.BASE) / "diag_test"); _os.makedirs(d, exist_ok=True)
    src = act if act.lower().endswith(".prt") else ""
    if not src:
        jl = CT.creo_call("file", "list", {})
        src = next((x for x in CT._flex_list(jl.get("data")) if str(x).lower().endswith(".prt")), "")
    if not src:
        rep("запись: нет .prt для копии — цикл пропущен")
    else:
        base = _re.sub(r"\.prt(\.\d+)?$", "", src, flags=_re.I)
        jb = CT.creo_call("file", "backup", {"file": src, "dirname": d, "target_dir": d}, 30)
        rep("запись backup %s: %s" % (src, "OK" if CT.ok(jb) else "ERR " + str(CT.errmsg(jb))[:60]))
        cands = sorted(_Path(d).glob(base + ".prt*"), key=lambda q: q.stat().st_mtime, reverse=True)
        copy = "diagtest_%d" % int(_time.time())
        if cands:
            _os.rename(cands[0], _Path(d) / (copy + ".prt"))
        jp0 = CT.creo_call("creo", "pwd", {})
        dd0 = jp0.get("data")
        orig = (dd0.get("directory") if isinstance(dd0, dict) else str(dd0 or "")) or ""
        CT.creo_call("creo", "cd", {"dirname": d})
        jo = CT.creo_call("file", "open", {"file": copy + ".prt", "display": False}, 30)
        rep("запись open копии: %s" % ("OK" if CT.ok(jo) else "ERR " + str(CT.errmsg(jo))[:60]))
        jps = CT.creo_call("parameter", "set", {"file": copy + ".prt", "name": "DIAG_TEST", "value": "full", "type": "STRING"}, 20)
        rep("запись parameter:set: %s" % ("OK" if CT.ok(jps) else "ERR " + str(CT.errmsg(jps))[:60]))
        jrs = CT.creo_call("file", "relations_set", {"file": copy + ".prt", "relations": "DIAG_REL = 42"}, 20)
        rep("запись relations_set: %s" % ("OK" if CT.ok(jrs) else "ERR " + str(CT.errmsg(jrs))[:60]))
        jrg = CT.creo_call("file", "regenerate", {"file": copy + ".prt"}, 30)
        rep("запись regenerate: %s" % ("OK" if CT.ok(jrg) else "ERR " + str(CT.errmsg(jrg))[:60]))
        jpl = CT.creo_call("parameter", "list", {"file": copy + ".prt"}, 20)
        have = []
        if CT.ok(jpl):
            dd = jpl.get("data") or {}
            have = [q.get("name") for q in (dd.get("paramlist") or dd.get("param_list") or [])]
        rep("запись чтение обратно DIAG_TEST: %s" % ("DIAG_TEST" in have))
        jrn = CT.creo_call("file", "rename", {"file": copy + ".prt", "new_name": copy + "_ren"}, 20)
        rep("запись rename копии: %s" % ("OK" if CT.ok(jrn) else "ERR " + str(CT.errmsg(jrn))[:60]))
        cur = (copy + "_ren") if CT.ok(jrn) else copy
        jsv = CT.creo_call("file", "save", {"file": cur + ".prt"}, 20)
        rep("запись save: %s" % ("OK" if CT.ok(jsv) else "ERR " + str(CT.errmsg(jsv))[:60]))
        je = CT.creo_call("file", "erase", {"file": cur + ".prt"}, 20)
        rep("запись erase: %s" % ("OK" if CT.ok(je) else "ERR " + str(CT.errmsg(je))[:60]))
        if orig:
            CT.creo_call("creo", "cd", {"dirname": orig})
        for q in list(_Path(d).glob("diagtest_*")) + list(_Path(d).glob(base + ".prt*")):
            try:
                q.unlink(); _fw("очистка del %s" % q.name)
            except Exception:
                pass
    rep("== конец ==")
    out.append("полный лог (кто/когда/что): diag_creoson.log")
    return "\n".join(out)

TOOLS += [
    {"name": "creoson_full_test", "desc": "ОДИН полный тест CREOSON: 20 чтений + пишущий цикл на копии (backup, cd, open, параметр, relations, regenerate, rename, save, erase) + очистка. Всё в diag_creoson.log. Без параметров.", "params": {}, "approval": True, "fn": tool_creoson_full_test},
]
'''
s += NEW
io.open(p, "w", encoding="utf-8").write(s)
print("[+] diagnostic_tools: один creoson_full_test вместо зоопарка")