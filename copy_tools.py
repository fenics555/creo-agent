# -*- coding: utf-8 -*-
r"""COPY v2: копия детали/семейства под новым именем.
ОС-копия версионных файлов -> валидация в Creo (open/regenerate/save/erase).
Оригиналы не трогаем; библиотека/стандарт не копируются.
Чертежи по умолчанию НЕ копируются (async не relink). family=1 по умолчанию."""
import os, re, shutil
from pathlib import Path
import creo_tools as CT

def _wd():
    d = CT.creo_call("creo", "pwd", {}, 10)
    if not CT.ok(d): return ""
    dd = d.get("data") or {}
    s = dd.get("directory") if isinstance(dd, dict) else str(dd or "")
    return s.replace("/", "\\").rstrip("\\") or ""

def _latest(wd, base):
    best, bv = None, -1
    for p in Path(wd).glob(base + ".*"):
        v = p.name.rsplit(".", 1)[-1]
        if v.isdigit() and int(v) > bv: bv, best = int(v), p
    return best

def _plan(wd, old, new, family, drawings):
    items = []
    def add(b_old, b_new):
        src = _latest(wd, b_old)
        if src: items.append((src.name, b_new + ".1"))
    for ext in (".prt", ".asm"):
        if _latest(wd, old + ext): add(old + ext, new + ext); break
    if drawings:
        if _latest(wd, old + ".drw"): add(old + ".drw", new + ".drw")
    if family:
        for p in sorted(Path(wd).glob("*<%s>.prt.*" % old)):
            b = re.sub(r"<%s>" % re.escape(old), "<%s>" % new, p.name, flags=re.I)
            items.append((p.name, re.sub(r"\.\d+$", "", b) + ".1"))
        if drawings:
            for p in sorted(Path(wd).glob("*<%s>.drw.*" % old)):
                b = re.sub(r"<%s>" % re.escape(old), "<%s>" % new, p.name, flags=re.I)
                items.append((p.name, re.sub(r"\.\d+$", "", b) + ".1"))
    seen = set(); out = []
    for s, d in items:
        if d not in seen: seen.add(d); out.append((s, d))
    return out

def tool_copy_model(old="", new="", family=1, drawings=0, dry_run=1, **kw):
    old = re.sub(r"\.(prt|asm|drw)(\.\d+)?$", "", (old or "").strip(), flags=re.I)
    new = re.sub(r"\.(prt|asm|drw)(\.\d+)?$", "", (new or "").strip(), flags=re.I)
    if not old or not new:
        return "используй: copy_model old=<базовое> new=<новое> [family=1] [drawings=0] [dry_run=0]"
    if not re.match(r"^[A-Za-z0-9_\-]+$", new):
        return "новое имя: только латиница/цифры/_-, без пробелов"
    wd = _wd()
    if not wd: return "не определил рабочую папку Creo"
    plan = _plan(wd, old, new, str(family) in ("1","true","да"), str(drawings) in ("1","true","да"))
    if not plan:
        return "в %s нет файлов %s (generic/экземпляры)" % (wd, old)
    conf = set()
    for s, d in plan:
        if list(Path(wd).glob(re.sub(r"\.\d+$", "", d) + ".*")): conf.add(d)
    if str(dry_run) in ("1","true","да"):
        out = ["ПЛАН копии %s -> %s (%d файлов):" % (old, new, len(plan))]
        out += ["- %s -> %s%s" % (s, d, "  [КОНФЛИКТ]" if d in conf else "") for s, d in plan]
        if conf: out.append("Конфликты: цель уже существует — эти файлы НЕ будут скопированы.")
        out.append("Выполнить: copy_model old=%s new=%s dry_run=0" % (old, new))
        return "\n".join(out)
    done, skip, errs = [], [], []
    for s, d in plan:
        base = re.sub(r"\.\d+$", "", d)
        if list(Path(wd).glob(base + ".*")): skip.append(d); continue
        try:
            shutil.copy2(Path(wd) / s, Path(wd) / d); done.append(d)
        except Exception as e:
            errs.append("%s: %s" % (d, str(e)[:60]))
    rep = ""
    for ext in (".prt", ".asm"):
        if list(Path(wd).glob(new + ext + ".*")):
            jo = CT.creo_call("file", "open", {"file": new + ext, "display": False}, 30)
            if CT.ok(jo):
                CT.creo_call("file", "regenerate", {"file": new + ext}, 30)
                CT.creo_call("file", "save", {"file": new + ext}, 20)
                CT.creo_call("file", "erase", {"file": new + ext}, 15)
                rep = "валидация %s: open/regenerate/save OK" % (new + ext)
            else:
                rep = "валидация %s: open ERR %s" % (new + ext, CT.errmsg(jo)[:80])
            break
    return "копия: сделано %d, пропущено(конфликт) %d, ошибок %d. %s%s" % (
        len(done), len(skip), len(errs), rep,
        ("; ошибки: " + "; ".join(errs)) if errs else "")

TOOLS = [
    {"name": "copy_model", "desc": "Копия детали/семейства под новым именем (ОС-копия + валидация в Creo). dry_run=1 — план", "params": {"old": "старое базовое", "new": "новое базовое", "family": "1 копировать экземпляры", "drawings": "1 копировать чертежи", "dry_run": "1 план / 0 выполнить"}, "approval": True, "fn": tool_copy_model},
]
