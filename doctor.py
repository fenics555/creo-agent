# -*- coding: utf-8 -*-
import sys, importlib
from pathlib import Path
AG = Path(r"D:\AI\tools\agent"); sys.path.insert(0, str(AG))
sp = AG / "scanner.py"; s = sp.read_text(encoding="utf-8")
if "# v14-fix-excl" not in s:
    s += r'''
# v14-fix-excl: is_excluded/_pats — понимают Path и читают kb_exclude.txt
import fnmatch as _fm2
from pathlib import Path as _P2
def _pats():
    try:
        p = _P2(__file__).resolve().parent / "kb_exclude.txt"
        out = []
        if p.exists():
            for l in p.read_text(encoding="utf-8").splitlines():
                l = l.strip()
                if l and not l.startswith("#"): out.append(l)
        return out
    except Exception:
        return []
def is_excluded(path, pats):
    st = str(path).lower().replace("/", "\\")
    for pat in (pats or []):
        q = pat.lower().replace("/", "\\")
        if "*" in q:
            if _fm2.fnmatch(st.split("\\")[-1], q) or _fm2.fnmatch(st, q): return True
        elif q in st:
            return True
    return False
'''
    sp.write_text(s, encoding="utf-8")
    print("[+] scanner.py: is_excluded/_pats исправлены")

import scanner; importlib.reload(scanner)
pats = scanner._pats()
print("pats:", len(pats), "пример:", pats[:3])
print("is_excluded(md):", scanner.is_excluded(Path(r"D:\AI\repo\SKILL_agent_protocol.md"), pats))
print("is_excluded(bak):", scanner.is_excluded(Path(r"Z:\PTC\Work\x\file.bak"), pats))
n = 0
for r in scanner.read_roots():
    rp = Path(r)
    if not rp.exists(): continue
    for f in rp.rglob("*"):
        try:
            if f.is_file() and f.suffix.lower() in scanner.EXTS and not scanner.is_excluded(f, pats):
                n += 1
        except Exception as e:
            print("EXC:", e); break
print("кандидатов на индекс:", n)
print("ДАЛЬШЕ: в панели index_run (или python -c \"import scanner; scanner.index_all()\"), через 5-10 мин index_state")