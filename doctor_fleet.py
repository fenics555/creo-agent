# -*- coding: utf-8 -*-
import io
ap = r"D:\AI\tools\agent\agent.py"
s = io.open(ap, encoding="utf-8").read()
old = "        else:\n            b = PAGE.encode()"
new = '''        elif p == "/fleet/info":
            import os as _os
            tail = ""
            try:
                jf = core.REPO / "Трейлы" / "TRAIL_JOURNAL.md"
                if jf.exists():
                    tail = "\\n".join(jf.read_text(encoding="utf-8", errors="ignore").splitlines()[-8:])
            except Exception:
                tail = ""
            self._j({"host": HOSTNAME, "user": _os.environ.get("USERNAME", ""),
                     "model": settings.get("llm_model"), "blocks": len(TR.BLOCKS),
                     "tools": len(TR.TOOLS), "trails": tail})
        else:
            b = PAGE.encode()'''
if "/fleet/info" in s: print("[~] маршрут уже есть")
elif old in s:
    s = s.replace(old, new, 1)
    io.open(ap, "w", encoding="utf-8").write(s)
    print("[+] маршрут /fleet/info добавлен")
else: print("[x] якорь не найден")