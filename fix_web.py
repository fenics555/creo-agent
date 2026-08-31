# -*- coding: utf-8 -*-
import io
ap = r"D:\AI\tools\agent\agent.py"
s = io.open(ap, encoding="utf-8").read()

old_j = "function J(u,b){return fetch(u,{method:b?'POST':'GET',headers:{'Content-Type':'application/json'},body:b?JSON.stringify(b):undefined}).then(function(r){return r.json()})}"
new_j = "function J(u,b){return fetch(u,{method:b?'POST':'GET',headers:{'Content-Type':'application/json','X-Token':TK||''},body:b?JSON.stringify(b):undefined}).then(function(r){return r.json()})}"
if new_j in s: print("[~] X-Token уже стоит")
elif old_j in s: s = s.replace(old_j, new_j, 1); print("[+] X-Token в J")
else: print("[x] якорь J не найден")

old_p = 'self._j(users.get_profile(cl) or {"error": "нет профиля"})'
new_p = ('__prof = users.get_profile(cl)\n'
         '            if __prof:\n'
         '                __prof = dict(__prof)\n'
         '                __prof["can_manage"] = users.can_manage_users(cl)\n'
         '            self._j(__prof or {"error": "нет профиля"})')
if 'can_manage"] = users.can_manage_users(cl)' in s: print("[~] /profile уже отдаёт can_manage")
elif old_p in s: s = s.replace(old_p, new_p, 1); print("[+] /profile: can_manage")
else: print("[x] якорь /profile не найден")

io.open(ap, "w", encoding="utf-8").write(s)
print("ГОТОВО: .\\AI_RESTART.bat, затем Ctrl+Shift+R")