# -*- coding: utf-8 -*-
import io
ap = r"D:\AI\tools\agent\agent.py"
s = io.open(ap, encoding="utf-8").read()
old = "J('/profile').then(function(u){"
new = "J('/profile',{token:TK}).then(function(u){"
if new in s: print("[~] уже исправлено")
elif old in s:
    s = s.replace(old, new, 1)
    io.open(ap, "w", encoding="utf-8").write(s)
    print("[+] showpro теперь POST с токеном")
else: print("[x] якорь не найден")