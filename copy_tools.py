# -*- coding: utf-8 -*-
r"""COPY: копия детали/сборки (семейство+чертёж) через временную папку.
Папка — через проверенный CT.tool_pwd(). Последовательность как в creoson_full_test."""
import re, shutil, tempfile
from pathlib import Path
import creo_tools as CT

def _wd():
    wd = CT.tool_pwd()
    return wd if (wd and re.match(r"^[A-Za-z]:[\\/]", wd)) else ""

def _strip(s):
    return re.sub(r"\.(prt|asm|drw)(\.\d+)?$", "", (s or "").strip(), flags=re.I)

def _files_for(wd, old):
    out = []
    for ext in ("prt", "asm"):
        best, bv = None, -1
        for p in Path(wd).glob("%s.%s.*" % (old, ext)):
            v = p.name.rsplit(".", 1)[-1]
            if v.isdigit() and int(v) > bv: bv, best = int(v), p
        if best: out.append(best)
    for p in sorted(Path(wd).glob("*<%s>.prt.*" % old)) + sorted(Path(wd).glob("%s.drw.*" % old)):
        out.append(p)
    return out

def _newname(fn, old, new):
    fn = re.sub(r"^%s\." % re.escape(old), new + ".", fn, flags=re.I)
    fn = re.sub(r"<%s>\." % re.escape(old), "<%s>." % new, fn, flags=re.I)
    return fn

def tool_copy_part(old="", new="", dry_run=True, **kw):
    old, new = _strip(old), _strip(new)
    if not old or not new: return "нужны old и new (базовые имена без расширения)"
    if not re.match(r"^[A-Za-z0-9_\-]+$", new): return "new: только латиница/цифры/_-"
    wd = _wd()
    if not wd: return "не узнал рабочую папку; сейчас в Creo: %s" % CT.tool_pwd()
    files = _files_for(wd, old)
    if not files: return "в %s нет %s.prt/.asm, семейства или чертежа" % (wd, old)
    if str(dry_run) in ("1", "True", "true"):
        out = ["ПЛАН копии %s -> %s в %s:" % (old, new, wd)]
        out += ["- %s -> %s" % (p.name, _newname(p.name, old, new)) for p in files]
        out.append("выполнить: copy_part old=%s new=%s dry_run=0" % (old, new))
        return "\n".join(out)
    tmp = Path(tempfile.mkdtemp(prefix="creo_copy_"))
    notes = []
    try:
        for p in files:
            j = CT.creo_call("file", "backup", {"file": p.name, "dirname": str(tmp), "target_dir": str(tmp)}, 30)
            if not CT.ok(j): notes.append("backup %s: %s" % (p.name, CT.errmsg(j)))
        CT.creo_call("creo", "cd", {"dirname": str(tmp)}, 15)
        for p in files:
            base = re.sub(r"\.\d+$", "", p.name)
            src = tmp / p.name
            if src.exists():
                try: src.rename(tmp / (_newname(base, old, new) + ".1"))
                except Exception as ex: notes.append("rename %s: %s" % (p.name, ex))
        mains = list(tmp.glob(new + ".prt.*")) + list(tmp.glob(new + ".asm.*"))
        if mains:
            cand = new + (".prt" if ".prt." in mains[0].name else ".asm")
            CT.creo_call("file", "open", {"file": cand, "display": False}, 30)
            CT.creo_call("file", "regenerate", {"file": cand}, 30)
            CT.creo_call("file", "save", {"file": cand}, 20)
            CT.creo_call("file", "erase", {"file": cand}, 15)
        CT.creo_call("creo", "cd", {"dirname": wd}, 15)
        copied = 0
        for p in tmp.glob("*.*"):
            dst = Path(wd) / p.name
            if dst.exists():
                notes.append("конфликт, не перезаписан: %s" % p.name); continue
            shutil.copy2(p, dst); copied += 1
        return "копия готова: %s -> %s, файлов: %d%s" % (old, new, copied, ("; " + "; ".join(notes)) if notes else "")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

TOOLS = [
    {"name": "copy_part", "desc": "Копия детали/сборки с семейством и чертежом через временную папку (dry_run=1 - план)", "params": {"old": "старое базовое", "new": "новое базовое", "dry_run": "1 план / 0 выполнить"}, "approval": True, "fn": tool_copy_part},
]
