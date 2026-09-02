# -*- coding: utf-8 -*-
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")
p = AG / "usage_tools.py"
s = p.read_text(encoding="utf-8")
ch = False
if "SC.read_roots()" in s:
    s = s.replace("SC.read_roots()", "core.read_roots()"); ch = True
if "SC._pats()" in s:
    s = s.replace("SC._pats()", "core.load_exclude_patterns()"); ch = True
if ch:
    p.write_text(s, encoding="utf-8")
    print("[+] usage_tools: корни и исключения теперь из config.json (не из удалённых kb_*.txt)")
else:
    print("[~] usage_tools: уже на core")
print("ГОТОВО: .\\AI_RESTART.bat, затем usage_build full=1")