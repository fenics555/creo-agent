# -*- coding: utf-8 -*-
import io
ap = r"D:\AI\tools\agent\agent.py"
s = io.open(ap, encoding="utf-8").read()

old_role = """else if(a=='do_role'){var lg=el.getAttribute('data-login');var sel=document.querySelector('.rsel[data-login="'+lg+'"]');J('/admin/users',{token:TK,op:'role',login:lg,role:sel.value}).then(function(r){alert(r.msg||'ок')})}"""
new_role = """else if(a=='do_role'){var lgn=el.getAttribute('data-login');var sel=document.querySelector('.rsel[data-login="'+lgn+'"]');J('/admin/users',{token:TK,op:'role',login:lgn,role:sel.value}).then(function(r){alert(r.msg||'ок')})}"""

old_res = """else if(a=='do_resetpw'){var lg=el.getAttribute('data-login');var nw=prompt('Новый пароль для '+lg+' (мин 4):');if(nw)J('/admin/users',{token:TK,op:'resetpw',login:lg,pw:nw}).then(function(r){alert(r.msg||'ок')})}"""
new_res = """else if(a=='do_resetpw'){var lgn=el.getAttribute('data-login');var nw=prompt('Новый пароль для '+lgn+' (мин 4):');if(nw)J('/admin/users',{token:TK,op:'resetpw',login:lgn,pw:nw}).then(function(r){alert(r.msg||'ок')})}"""

if 'var lgn=' in s:
    print("[~] уже переименовано")
else:
    for old, new, tag in ((old_role, new_role, "do_role"), (old_res, new_res, "do_resetpw")):
        if old in s:
            s = s.replace(old, new, 1); print("[+] %s: lg→lgn" % tag)
        else:
            print("[x] %s: якорь не найден" % tag)
    io.open(ap, "w", encoding="utf-8").write(s)
print("ГОТОВО")