# -*- coding: utf-8 -*-
import io
p = r"D:\AI\tools\agent\diagnostic_tools.py"
s = io.open(p, encoding="utf-8").read()
start = s.find("def tool_creoson_full_test")
if start < 0:
    print("[x] tool_creoson_full_test не найдена")
    raise SystemExit
nxt = s.find("\ndef ", start + 10)
if nxt < 0:
    nxt = s.find("\nTOOLS", start)

NEW = '''def tool_creoson_full_test(**kw):
    import os, time as _t, pathlib
    import core
    import creo_tools as CT
    out = []
    def rep(line, okf=True):
        out.append(line); _w(line, True)
    act = CT.tool_get_active()
    rep("== старт, активная: %s ==" % act)
    reads = [("creo", "pwd", {}), ("creo", "list_files", {"filename": "*"}), ("file", "list", {}),
             ("file", "exists", {"file": act}), ("file", "get_fileinfo", {"file": act}),
             ("file", "massprops", {"file": act}), ("file", "relations_get", {"file": act}),
             ("file", "open_errors", {"file": act}), ("parameter", "list", {"file": act}),
             ("parameter", "exists", {"file": act, "name": "ОБОЗНАЧЕНИЕ"}),
             ("dimension", "list", {"file": act}), ("feature", "list", {"file": act}),
             ("bom", "get_paths", {"file": act, "paths": False, "top_level": False, "exclude_inactive": True}),
             ("familytable", "list", {"file": act}), ("layer", "list", {"file": act}),
             ("note", "list", {"file": act}), ("view", "list", {"file": act}),
             ("geometry", "bound_box", {"file": act})]
    for cmd, fn, data in reads:
        j = CT.creo_call(cmd, fn, data, 20)
        rep("чтение %-20s %s" % (cmd + ":" + fn, "OK" if CT.ok(j) else "ERR " + str(CT.errmsg(j))[:60]), CT.ok(j))
    d = str(pathlib.Path(core.BASE) / "diag_test"); os.makedirs(d, exist_ok=True)
    jl = CT.creo_call("file", "list", {})
    lst = CT._flex_list(jl.get("data")) if CT.ok(jl) else []
    src = next((x for x in lst if x.lower().endswith(".prt")), "")
    if not src:
        rep("FAIL: нет .prt в сессии для копии", False)
    else:
        import re as _re
        base = _re.sub(r"\\.prt(\\.\\d+)?$", "", src, flags=_re.I)
        jb = CT.creo_call("file", "backup", {"file": src, "dirname": d, "target_dir": d}, 30)
        rep("запись backup %s: %s" % (src, "OK" if CT.ok(jb) else "ERR " + str(CT.errmsg(jb))[:60]), CT.ok(jb))
        dd0 = (CT.creo_call("creo", "pwd", {}) or {}).get("data")
        orig = (dd0.get("directory") if isinstance(dd0, dict) else str(dd0 or "")) or ""
        CT.creo_call("creo", "cd", {"dirname": d})
        copy = "diagtest_%d" % int(_t.time())
        jo = CT.creo_call("file", "open", {"file": copy + ".prt", "display": False}, 30)
        rep("запись open копии: %s" % ("OK" if CT.ok(jo) else "ERR " + str(CT.errmsg(jo))[:60]), CT.ok(jo))
        jrn = CT.creo_call("file", "rename", {"file": copy + ".prt", "new_name": copy + "_ren"}, 20)
        rep("запись rename ЧИСТОЙ копии: %s" % ("OK" if CT.ok(jrn) else "ERR " + str(CT.errmsg(jrn))[:60]), CT.ok(jrn))
        cur = (copy + "_ren") if CT.ok(jrn) else copy
        jps = CT.creo_call("parameter", "set", {"file": cur + ".prt", "name": "DIAG_TEST", "value": "full", "type": "STRING"}, 20)
        rep("запись parameter:set: %s" % ("OK" if CT.ok(jps) else "ERR " + str(CT.errmsg(jps))[:60]), CT.ok(jps))
        jrs = CT.creo_call("file", "relations_set", {"file": cur + ".prt", "relations": "DIAG_REL = 42"}, 20)
        rep("запись relations_set: %s" % ("OK" if CT.ok(jrs) else "ERR " + str(CT.errmsg(jrs))[:60]), CT.ok(jrs))
        jrg = CT.creo_call("file", "regenerate", {"file": cur + ".prt"}, 30)
        rep("запись regenerate: %s" % ("OK" if CT.ok(jrg) else "ERR " + str(CT.errmsg(jrg))[:60]), CT.ok(jrg))
        jpl = CT.creo_call("parameter", "list", {"file": cur + ".prt"}, 20)
        have = []
        if CT.ok(jpl):
            dd = jpl.get("data") or {}
            have = [q.get("name") for q in (dd.get("paramlist") or dd.get("param_list") or [])]
        rep("запись чтение обратно DIAG_TEST: %s" % ("DIAG_TEST" in have), "DIAG_TEST" in have)
        jsv = CT.creo_call("file", "save", {"file": cur + ".prt"}, 20)
        rep("запись save: %s" % ("OK" if CT.ok(jsv) else "ERR " + str(CT.errmsg(jsv))[:60]), CT.ok(jsv))
        je = CT.creo_call("file", "erase", {"file": cur + ".prt"}, 20)
        rep("запись erase: %s" % ("OK" if CT.ok(je) else "ERR " + str(CT.errmsg(je))[:60]), CT.ok(je))
        CT.creo_call("creo", "cd", {"dirname": orig})
        for q in list(pathlib.Path(d).glob("diagtest_*")) + list(pathlib.Path(d).glob(base + ".prt*")):
            try:
                q.unlink(); _w("очистка del %s" % q.name, True)
            except Exception:
                pass
    fails = [l for l in out if "ERR" in l or l.startswith("FAIL")]
    v = "ПРОЙДЕН" if not fails else "НЕ ПРОЙДЕН (%d): %s" % (len(fails), "; ".join(fails)[:300])
    _w("== creoson_full_test вердикт: %s" % v, True)
    return "\\n".join(out) + "\\nвердикт: %s" % v
'''
s = s[:start] + NEW + s[nxt:]
io.open(p, "w", encoding="utf-8").write(s)
print("[+] creoson_full_test: rename теперь на ЧИСТОЙ копии, до правок")