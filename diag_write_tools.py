# -*- coding: utf-8 -*-
r"""Диагностика пишущих операций: отдельный лог ВСЕХ вызовов CREOSON +
безопасный тест на копии активной детали. Оригинал не трогается."""
import os, re, json, time
from pathlib import Path
import core
import creo_tools as CT

LOGF = Path(core.BASE) / "diag_creoson.log"
DIAG_DIR = Path(core.BASE) / "diag_test"

def _w(line):
    try:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (time.strftime("%m-%d %H:%M:%S"), line))
    except Exception:
        pass

# отдельный лог: каждый запрос/ответ CREOSON любого блока
_orig_raw = CT.creo_raw
def _logged_raw(cmd, fn, data=None, t=15):
    _w(">> %s:%s %s" % (cmd, fn, json.dumps(data or {}, ensure_ascii=False)[:200]))
    j = _orig_raw(cmd, fn, data, t)
    _w("<< %s:%s %s | %s" % (cmd, fn, "OK" if CT.ok(j) else "ERR",
                             json.dumps(j.get("data") if CT.ok(j) else j.get("status"), ensure_ascii=False)[:200]))
    return j
CT.creo_raw = _logged_raw
_w("== diag_write_tools: все вызовы CREOSON логируются в %s ==" % LOGF.name)

def tool_write_test(**kw):
    out = ["ТЕСТ ПИШУЩИХ на копии (оригинал не трогается):"]
    DIAG_DIR.mkdir(parents=True, exist_ok=True)
    _w("== write_test START ==")
    jp = CT.creo_call("creo", "pwd", {})
    if not CT.ok(jp):
        return "не узнал pwd: %s" % CT.errmsg(jp)
    d = jp.get("data")
    orig_dir = d.get("directory") if isinstance(d, dict) else str(d)
    act = CT.tool_get_active()
    src = act if act.lower().endswith(".prt") else ""
    if not src:
        jl = CT.creo_call("file", "list", {})
        src = next((x for x in CT._flex_list(jl.get("data")) if x.lower().endswith(".prt")), "")
    if not src:
        return "не нашёл деталь для теста"
    base = re.sub(r"\.prt(\.\d+)?$", "", src, flags=re.I)
    out.append("исходная: %s" % src)
    jb = CT.creo_call("file", "backup", {"file": src, "dirname": str(DIAG_DIR)}, 30)
    if not CT.ok(jb):
        return "backup не удался: %s" % CT.errmsg(jb)
    cands = sorted(DIAG_DIR.glob(base + ".prt*"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not cands:
        return "backup не оставил файл в %s" % DIAG_DIR
    copy_name = "diagtest_%d" % int(time.time())
    try:
        os.rename(cands[0], DIAG_DIR / (copy_name + ".prt"))
        _w("OS rename %s -> %s.prt" % (cands[0].name, copy_name))
    except Exception as e:
        return "OS rename: %s" % e
    out.append("копия: %s.prt" % copy_name)
    jcd = CT.creo_call("creo", "cd", {"dirname": str(DIAG_DIR)})
    if not CT.ok(jcd):
        return "cd не удался: %s" % CT.errmsg(jcd)
    try:
        jo = CT.creo_call("file", "open", {"file": copy_name + ".prt", "display": False}, 30)
        out.append("open копии: %s" % ("OK" if CT.ok(jo) else "ERR " + CT.errmsg(jo)[:70]))
        jps = CT.creo_call("parameter", "set", {"file": copy_name + ".prt", "name": "DIAG_TEST", "value": "ok_" + time.strftime("%H%M%S"), "type": "STRING"}, 20)
        out.append("parameter:set DIAG_TEST: %s" % ("OK" if CT.ok(jps) else "ERR " + CT.errmsg(jps)[:70]))
        jrs = CT.creo_call("file", "relations_set", {"file": copy_name + ".prt", "relations": "DIAG_REL = 42"}, 20)
        out.append("relations_set DIAG_REL=42: %s" % ("OK" if CT.ok(jrs) else "ERR " + CT.errmsg(jrs)[:70]))
        jrg = CT.creo_call("file", "regenerate", {"file": copy_name + ".prt"}, 30)
        out.append("regenerate: %s" % ("OK" if CT.ok(jrg) else "ERR " + CT.errmsg(jrg)[:70]))
        jpl = CT.creo_call("parameter", "list", {"file": copy_name + ".prt"}, 20)
        have = []
        if CT.ok(jpl):
            dd = jpl.get("data") or {}
            have = [p.get("name") for p in (dd.get("paramlist") or dd.get("param_list") or [])]
        out.append("DIAG_TEST в параметрах после записи: %s" % ("DIAG_TEST" in have))
        jrn = CT.creo_call("file", "rename", {"file": copy_name + ".prt", "new_name": copy_name + "_ren"}, 20)
        out.append("rename копии: %s" % ("OK" if CT.ok(jrn) else "ERR " + CT.errmsg(jrn)[:70]))
        cur = (copy_name + "_ren") if CT.ok(jrn) else copy_name
        jsv = CT.creo_call("file", "save", {"file": cur + ".prt"}, 20)
        out.append("save: %s" % ("OK" if CT.ok(jsv) else "ERR " + CT.errmsg(jsv)[:70]))
        je = CT.creo_call("file", "erase", {"file": cur + ".prt"}, 20)
        out.append("erase: %s" % ("OK" if CT.ok(je) else "ERR " + CT.errmsg(je)[:70]))
    finally:
        CT.creo_call("creo", "cd", {"dirname": orig_dir})
        for p in list(DIAG_DIR.glob("diagtest_*")) + list(DIAG_DIR.glob(base + ".prt*")):
            try:
                p.unlink(); _w("OS del %s" % p.name)
            except Exception:
                pass
    _w("== write_test END ==")
    out.append("полный лог запросов/ответов: %s" % LOGF)
    return "\n".join(out)

TOOLS = [
    {"name": "creoson_write_test", "desc": "ТЕСТ пишущих операций на копии детали: backup→open→параметр/relations→regenerate→rename→save→erase→удаление. Лог: diag_creoson.log", "params": {}, "approval": True, "fn": tool_write_test},
]