# -*- coding: utf-8 -*-
import io, re
AG = r"D:\AI\tools\agent"

# 1) copy_tools.py целиком: cd только в try/finally
COPY = '''# -*- coding: utf-8 -*-
r"""COPY: копия детали/чертежа через временную папку. Рабочая папка Creo ВСЕГДА возвращается."""
import os, re, shutil, tempfile
from pathlib import Path
import creo_tools as CT
ok, errmsg, cc = CT.ok, CT.errmsg, CT.creo_call

def _wd():
    d = cc("creo", "pwd", {})
    if not ok(d): return ""
    dd = d.get("data")
    return (dd.get("directory") if isinstance(dd, dict) else str(dd or "")) or ""

def _strip(s):
    return re.sub(r"\\.(prt|asm|drw)(\\.\\d+)?$", "", s, flags=re.I)

def _latest(wd, base, ext):
    best, bv = None, -1
    for p in Path(wd).glob("%s.%s.*" % (base, ext)):
        v = p.name.rsplit(".", 1)[-1]
        if v.isdigit() and int(v) > bv: bv, best = int(v), p
    return best

def tool_copy_part(old="", new="", dry_run=True, **kw):
    old = _strip((old or "").strip()); new = _strip((new or "").strip())
    if not old or not new: return "нужны old и new (базовые имена без расширения)"
    if not re.match(r"^[A-Za-z0-9_\\-]+$", new): return "new: только латиница/цифры/_-"
    wd = _wd()
    if not wd: return "не узнал рабочую папку Creo"
    pairs = []
    for ext in ("prt", "asm", "drw"):
        src = _latest(wd, old, ext)
        if src: pairs.append((src, new + "." + ext))
    if not pairs: return "в %s нет %s.prt/.asm/.drw" % (wd, old)
    if str(dry_run) in ("1", "True", "true"):
        out = ["ПЛАН копии %s -> %s в %s:" % (old, new, wd)]
        out += ["- %s -> %s" % (s.name, d) for s, d in pairs]
        out.append("выполнить: copy_part old=%s new=%s dry_run=0" % (old, new))
        return "\\n".join(out)
    tmp = Path(tempfile.mkdtemp(prefix="creo_copy_"))
    notes = []
    try:
        for src, dst in pairs:
            shutil.copy2(src, tmp / src.name)
        cc("creo", "cd", {"dirname": str(tmp)}, 15)
        for src, dst in pairs:
            os.rename(tmp / src.name, tmp / (dst + ".1"))
        part_new = next((d for s, d in pairs if d.endswith(".prt")), "")
        if part_new:
            cc("file", "open", {"file": part_new, "display": False}, 30)
            cc("file", "regenerate", {"file": part_new}, 30)
            cc("file", "save", {"file": part_new}, 20)
            cc("file", "erase", {"file": part_new}, 15)
        moved = 0
        for p in tmp.glob("*.*"):
            dst = Path(wd) / p.name
            if dst.exists():
                notes.append("конфликт, не перезаписан: %s" % p.name); continue
            shutil.copy2(p, dst); moved += 1
        return "копия готова: %s -> %s, файлов: %d%s" % (old, new, moved, ("; " + "; ".join(notes)) if notes else "")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        if wd: cc("creo", "cd", {"dirname": wd}, 15)

TOOLS = [
    {"name": "copy_part", "desc": "Копия детали/чертежа через временную папку (dry_run=1 - план). Рабочая папка всегда возвращается", "params": {"old": "старое базовое", "new": "новое базовое", "dry_run": "1 план / 0 выполнить"}, "approval": True, "fn": tool_copy_part},
]
'''
io.open(AG + r"\copy_tools.py", "w", encoding="utf-8").write(COPY)
print("[+] copy_tools.py: cd обёрнут в finally")

# 2) diagnostic_tools: обернуть creoson_full_test в try/finally с возвратом папки
dp = AG + r"\diagnostic_tools.py"
s = io.open(dp, encoding="utf-8").read()
m = re.search(r"(def tool_creoson_full_test\([^)]*\):\n)(.*?)(?=\ndef [a-zA-Z_]|\Z)", s, re.S)
if m and "finally:" not in m.group(2):
    body = m.group(2)
    ind = "    "
    wrapped = ind + "wd0 = CT.tool_pwd()\n" + ind + "try:\n"
    wrapped += re.sub(r"(?m)^(.)", ind + r"\1", body)
    wrapped += ind + "finally:\n" + ind + "    if wd0: CT.creo_call(\"creo\", \"cd\", {\"dirname\": wd0}, 15)\n"
    s = s[:m.start(2)] + wrapped + s[m.end(2):]
    io.open(dp, "w", encoding="utf-8").write(s)
    print("[+] diagnostic_tools: creoson_full_test всегда возвращает папку")
else:
    print("[~] diagnostic_tools: уже есть finally или функция не найдена")
print("ГОТОВО: .\\AI_RESTART.bat")