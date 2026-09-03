# -*- coding: utf-8 -*-
import shutil
from pathlib import Path
p = Path(r"D:\AI\repo\SKILL_agent_protocol.md")
if p.exists():
    t = p.read_text(encoding="utf-8", errors="ignore")
    print("ГОЛОВА ФАЙЛА:", t[:400].replace("\n", " | "))
    if "[TOOL:" not in t or ("ОДИН БЛОК" not in t and "ФОРМАТ" not in t):
        shutil.move(str(p), str(p) + ".bak")
        print("[+] SKILL_agent_protocol.md -> .bak; включится DEFAULT_PROTO")
    else:
        print("[=] файл похож на протокол, не трогаю")
else:
    print("[=] файла нет, работает DEFAULT_PROTO")
print("ГОТОВО: .\\AI_RESTART.bat + Ctrl+F5")