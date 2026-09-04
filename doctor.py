# -*- coding: utf-8 -*-
import json, re
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")

# 1) стриминг ВЫКЛ -> чат по чистой дороге v12
cp = AG / "data" / "config.json"; d = json.loads(cp.read_text(encoding="utf-8"))
if d.get("stream_tokens", True):
    d["stream_tokens"] = False
    cp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[+] stream_tokens=False")

# 2) PERSONAL_KEYS в [] -> крутилки/модель пишут глобально и РЕАЛЬНО работают
sp = AG / "settings.py"; s = sp.read_text(encoding="utf-8")
m = re.search(r"PERSONAL_KEYS = \[[^\]]*\]", s)
if m and m.group(0) != "PERSONAL_KEYS = []":
    s = s.replace(m.group(0), "PERSONAL_KEYS = []", 1)
    sp.write_text(s, encoding="utf-8"); print("[+] PERSONAL_KEYS=[]")

# 3) agent.py: склейка без пробелов + ПРАВДА с диска (скинь мне эти строки)
ap = AG / "agent.py"; a = ap.read_text(encoding="utf-8")
if '" ".join(parts)' in a:
    a = a.replace('" ".join(parts)', '"".join(parts)', 1)
    ap.write_text(a, encoding="utf-8"); print("[+] join без пробелов")
print("GROUND join:", [l.strip() for l in a.split("\n") if "join(parts)" in l])
print("GROUND nudge:", [l.strip()[:100] for l in a.split("\n") if "не в формате" in l])
print("GROUND setm:", [l.strip() for l in a.split("\n") if "setmodel" in l][:2])
print("ГОТОВО: .\\AI_RESTART.bat + Ctrl+F5")