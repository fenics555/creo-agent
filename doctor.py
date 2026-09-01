# -*- coding: utf-8 -*-
import io, re
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")

# 1) learn_tools: relations приходит списком — приводим к строке
lp = AG / "learn_tools.py"
s = lp.read_text(encoding="utf-8")
old = 'if not rels or rels == "отношений нет" or rels.startswith("ошибка"):'
new = ('if isinstance(rels, list): rels = "\\n".join(str(x) for x in rels)\n'
       '    if not rels or rels == "отношений нет" or str(rels).startswith("ошибка"):')
if "isinstance(rels, list)" in s: print("[~] learn_tools: уже")
elif old in s:
    lp.write_text(s.replace(old, new, 1), encoding="utf-8"); print("[+] learn_tools: список -> строка")
else: print("[x] learn_tools: якорь не найден")

# 2) COPY-блок v2: копия детали с семейством через временную папку
COPY = '''# -*- coding: utf-8 -*-
r"""COPY v2: копия детали (в т.ч. с таблицей семейств) через временную папку.
ОС-копия последних версий под новыми именами -> open нового generic в Creo (cd temp) ->
regenerate -> save -> перенос в рабочую папку (конфликты не перезаписываются) -> возврат cd.
Чертежи и сборки - следующая версия (нужен relink в сессии)."""
import re, shutil, tempfile
from pathlib import Path
import creo_tools as CT
ok, errmsg, cc = CT.ok, CT.errmsg, CT.creo_call

def _wd():
    d = cc("creo", "pwd", {}, 10)
    if not ok(d): return ""
    dd = d.get("data")
    return (dd.get("directory") if isinstance(dd, dict) else str(dd or "")) or ""

def _latest(pdir, stem, ext):
    best, bv = None, -1
    for p in Path(pdir).glob("%s.%s.*" % (stem, ext)):
        v = p.name.rsplit(".", 1)[-1]
        if v.isdigit() and int(v) > bv: bv, best = int(v), p
    if best is None:
        q = Path(pdir) / ("%s.%s" % (stem, ext))
        if q.exists(): best = q
    return best

def _plan_files(wd, old):
    out, seen = [], set()
    g = _latest(wd, old, "prt")
    if g: out.append((g, "generic")); seen.add(g)
    for p in sorted(Path(wd).glob("*<%s>.prt.*" % old)) + sorted(Path(wd).glob("*<%s>.prt" % old)):
        if p not in seen: seen.add(p); out.append((p, "instance"))
    return out

def _new_base(old, new, fname):
    base = re.sub(r"\\.prt(\\.\\d+)?$", "", fname, flags=re.I)
    if base.lower() == old.lower(): return new
    tail = "<%s>" % old.lower()
    if base.lower().endswith(tail): return base[:-len(tail)] + "<%s>" % new
    return base

def tool_copy_part(old="", new="", dry_run=True, **kw):
    old = re.sub(r"\\.(prt|asm)(\\.\\d+)?$", "", (old or "").strip(), flags=re.I)
    new = re.sub(r"\\.(prt|asm)(\\.\\d+)?$", "", (new or "").strip(), flags=re.I)
    if not old or not new: return "нужны old и new (базовые имена без расширения)"
    if not re.match(r"^[A-Za-z0-9_\\-]+$", new): return "new: только латиница/цифры/_-"
    wd = _wd()
    if not wd: return "не узнал рабочую папку Creo"
    files = _plan_files(wd, old)
    if not files: return "в %s нет %s.prt и семейства" % (wd, old)
    if str(dry_run) in ("1", "True", "true"):
        out = ["ПЛАН копии %s -> %s (%d файлов):" % (old, new, len(files))]
        out += ["- %s [%s] -> %s.prt.1" % (p.name, k, _new_base(old, new, p.name)) for p, k in files]
        out.append("выполнить: copy_part old=%s new=%s dry_run=0" % (old, new))
        return "\\n".join(out)
    tmp = Path(tempfile.mkdtemp(prefix="creo_copy_"))
    notes = []
    try:
        for p, k in files: shutil.copy2(p, tmp / p.name)
        for p, k in files:
            src = tmp / p.name
            if src.exists(): src.rename(tmp / (_new_base(old, new, p.name) + ".prt.1"))
        cc("creo", "cd", {"dirname": str(tmp)}, 15)
        gnew = _new_base(old, new, old + ".prt")
        jo = cc("file", "open", {"file": gnew + ".prt", "display": False}, 30)
        if not ok(jo): return "не открылась копия %s: %s" % (gnew, errmsg(jo))
        cc("file", "regenerate", {"file": gnew + ".prt"}, 30)
        cc("file", "save", {"file": gnew + ".prt"}, 20)
        cc("file", "erase", {"file": gnew + ".prt"}, 15)
        cc("creo", "cd", {"dirname": wd}, 15)
        moved = 0
        for p in tmp.glob("*.prt.*"):
            dst = Path(wd) / p.name
            if dst.exists(): notes.append("конфликт, не перезаписан: %s" % dst.name); continue
            shutil.copy2(p, dst); moved += 1
        cc("file", "erase_not_displayed", {}, 15)
        return "копия готова: %s -> %s, файлов в рабочей папке: %d%s" % (
            old, new, moved, ("; " + "; ".join(notes)) if notes else "")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

TOOLS = [
    {"name": "copy_part", "desc": "Копия детали с таблицей семейств через временную папку (dry_run=1 - план)", "params": {"old": "старое базовое имя", "new": "новое базовое имя", "dry_run": "1 план / 0 выполнить"}, "approval": True, "fn": tool_copy_part},
]
'''
(AG / "copy_tools.py").write_text(COPY, encoding="utf-8")
print("[+] copy_tools.py v2: копия детали с семейством")
print("ГОТОВО: .\\AI_RESTART.bat, затем .\\GIT_SYNC.bat")