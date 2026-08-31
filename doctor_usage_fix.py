# -*- coding: utf-8 -*-
import io
p = r"D:\AI\tools\agent\usage_tools.py"
s = io.open(p, encoding="utf-8").read()
old = 'sqlite3.connect(str(core.BASE / "agent.sqlite"), timeout=20)'
new = 'core.db()'
if old not in s and 'c = core.db()' in s:
    print("[~] уже core.db()")
elif old in s:
    s = s.replace(old, new, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("[+] usage_tools переведён на общую БД")
else:
    print("[x] якорь не найден — кинь строку def _db из usage_tools")