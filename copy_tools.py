# -*- coding: utf-8 -*-
r"""Копия детали/сборки с чертежом и таблицей семейств: Backup во временную -> rename там -> перенос файлов."""
import os, re, json, shutil, tempfile, urllib.request
import core

CS = "http://127.0.0.1:8080/creoson"

def _cs(sid, command, function, data=None):
    body = {"command": command, "function": function, "data": data or {}}
    if sid: body["sessionId"] = sid
    req = urllib.request.Request(CS, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        return {"status": {"error": True, "message": str(e)}}

def _ok(r): return not (r.get("status") or {}).get("error")
def _dat(r): return r.get("data") or {}

def _connect():
    r = _cs(None, "connection", "connect", {})
    return _dat(r).get("sessionId") if _ok(r) else None

def _workdir(sid):
    d = _dat(_cs(sid, "creo", "pwd", {}))
    return d.get("directory") if isinstance(d, dict) else str(d or "")

def _family_instances(workdir, base):
    suf = "<%s>.prt" % base
    return sorted(f[: -len(suf)] for f in os.listdir(workdir)
                  if f.lower().endswith(suf.lower())) if os.path.isdir(workdir) else []

def _plan(sid, old, new):
    wd = _workdir(sid)
    if not wd or not os.path.isdir(wd):
        return wd, None, "рабочая папка Creo не читается: %s" % wd
    ext = next((e for e in ("prt", "asm") if os.path.exists(os.path.join(wd, old + "." + e))), "")
    if not ext:
        return wd, None, "в рабочей папке нет %s.prt/%s.asm" % (old, old)
    items = [(old + "." + ext, new + "." + ext, "generic")]
    drw = old + ".drw"
    if os.path.exists(os.path.join(wd, drw)):
        items.append((drw, new + ".drw", "drawing"))
    for inst in _family_instances(wd, old):
        items.append(("%s<%s>.prt" % (inst, old), "%s<%s>.prt" % (inst, new), "instance"))
    return wd, items, ""

def tool_copy_model(old="", new="", dry_run=True, **kw):
    old = (old or "").strip().lower(); new = (new or "").strip().lower()
    if not old or not new: return "нужны old и new (базовые имена, латиницей)"
    if not re.match(r"^[a-z0-9_\-]+$", new): return "new: только латиница/цифры/_-"
    if old == new: return "имена совпадают"
    sid = _connect()
    if not sid: return "CREOSON недоступен"
    wd, items, err = _plan(sid, old, new)
    if err: return err
    if str(dry_run) in ("1", "true", "True", "да"):
        out = ["ПЛАН (dry_run, ничего не меняется): папка %s" % wd]
        out += ["- %s  ->  %s  [%s]" % (s, d, k) for s, d, k in items]
        out.append("для выполнения: copy_model old=%s new=%s dry_run=0 (с согласованием)" % (old, new))
        return "\n".join(out)
    log = []
    tmp = tempfile.mkdtemp(prefix="creo_copy_")
    try:
        for s, d, k in items:
            r = _cs(sid, "file", "backup", {"file": s, "dirname": tmp})
            if not _ok(r): return "STOP backup %s: %s" % (s, r.get("status", {}).get("message"))
            log.append("backup %s" % s)
        r = _cs(sid, "creo", "cd", {"dirname": tmp})
        if not _ok(r): return "STOP cd temp: %s" % r.get("status", {}).get("message")
        order = sorted(items, key=lambda it: {"instance": 0, "generic": 1, "drawing": 2}[it[2]])
        for s, d, k in order:
            _cs(sid, "file", "open", {"file": s, "dirname": tmp, "display": False})
            r = _cs(sid, "file", "rename", {"file": s, "new_name": d.rsplit(".", 1)[0]})
            if not _ok(r): return "STOP rename %s: %s" % (s, r.get("status", {}).get("message"))
            log.append("rename %s -> %s" % (s, d))
            _cs(sid, "file", "save", {"file": d})
        _cs(sid, "creo", "cd", {"dirname": wd})
        copied, occupied = [], []
        for s, d, k in items:
            src = os.path.join(tmp, d)
            if not os.path.exists(src):
                src = next((os.path.join(tmp, f) for f in os.listdir(tmp)
                            if f.lower().startswith(d.rsplit(".", 1)[0] + ".") ), "")
            dst = os.path.join(wd, d)
            if os.path.exists(dst): occupied.append(d); continue
            if src and os.path.exists(src):
                shutil.copy2(src, dst + ".1" if not dst.lower().endswith(".1") else dst)
                copied.append(d)
        _cs(sid, "file", "erase_not_displayed", {})
        log.append("перенесено в рабочую папку: %s" % ", ".join(copied) or "ничего")
        if occupied: log.append("ВНИМАНИЕ, имя занято (не тронуто): %s" % ", ".join(occupied))
        return "\n".join(log)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

TOOLS = [
    {"name": "copy_model", "desc": "Копия детали/сборки с чертежом и таблицей семейств (dry_run=1 — только план)",
     "params": {"old": "исходное имя", "new": "новое имя", "dry_run": "1 план / 0 выполнять"},
     "approval": True, "fn": tool_copy_model},
]