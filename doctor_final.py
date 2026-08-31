# -*- coding: utf-8 -*-
import io
ap = r"D:\AI\tools\agent\agent.py"
s = io.open(ap, encoding="utf-8").read()

def rep(old, new, tag, all_=False):
    global s
    if new in s and not all_:
        print("[~] %s: уже" % tag); return
    if old not in s:
        print("[x] %s: якорь не найден" % tag); return
    s = s.replace(old, new) if all_ else s.replace(old, new, 1)
    print("[+] %s" % tag)

# --- вход/админка: тени и методы ---
rep("J('/login',{login:lg.value,pw:pw.value})",
    "J('/login',{login:document.getElementById('lg').value,pw:document.getElementById('pw').value})", "login без тени lg")
rep("""else if(a=='do_role'){var lg=el.getAttribute('data-login');var sel=document.querySelector('.rsel[data-login="'+lg+'"]');J('/admin/users',{token:TK,op:'role',login:lg,role:sel.value}).then(function(r){alert(r.msg||'ок')})}""",
    """else if(a=='do_role'){var lgn=el.getAttribute('data-login');var sel=document.querySelector('.rsel[data-login="'+lgn+'"]');J('/admin/users',{token:TK,op:'role',login:lgn,role:sel.value}).then(function(r){alert(r.msg||'ок')})}""", "do_role lgn")
rep("""else if(a=='do_resetpw'){var lg=el.getAttribute('data-login');var nw=prompt('Новый пароль для '+lg+' (мин 4):');if(nw)J('/admin/users',{token:TK,op:'resetpw',login:lg,pw:nw}).then(function(r){alert(r.msg||'ок')})}""",
    """else if(a=='do_resetpw'){var lgn=el.getAttribute('data-login');var nw=prompt('Новый пароль для '+lgn+' (мин 4):');if(nw)J('/admin/users',{token:TK,op:'resetpw',login:lgn,pw:nw}).then(function(r){alert(r.msg||'ок')})}""", "do_resetpw lgn")
rep("else if(a=='showpro'){J('/profile').then(function(u){",
    "else if(a=='showpro'){J('/profile',{token:TK}).then(function(u){", "profile POST")

# --- чат: импорт, маршруты, кнопка, панель, JS ---
rep("import users\n", "import users\nimport chat_tools\n", "импорт chat_tools")
rep('        elif p == "/admin/users":',
    '        elif p == "/chat/send":\n            self._j(chat_tools.chat_send(cl, b.get("text")))\n        elif p == "/chat/poll":\n            self._j({"msgs": chat_tools.chat_poll(b.get("last") or 0)})\n        elif p == "/admin/users":', "маршруты чата")
rep('<button data-act="showpro">👤</button> <button data-act="logout">',
    '<button data-act="showpro">👤</button><button data-act="showchat">💬</button> <button data-act="logout">', "кнопка 💬")
rep("<script>", '''<div id="chatbox" style="display:none;position:fixed;top:44px;left:0;bottom:0;width:340px;background:#171d26;border-right:1px solid #243040;padding:10px;z-index:6;flex-direction:column;gap:8px">
<b>💬 КОМАНДА</b><div id="cmsg" style="flex:1;overflow:auto;display:flex;flex-direction:column;gap:6px"></div>
<div style="display:flex;gap:6px"><input id="cin" placeholder="Сообщение всем..." style="flex:1;background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:8px">
<button data-act="chatsend" style="background:#2b4a6f;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer">➤</button></div>
</div>
<script>''', "чат-панель HTML")
rep("qinp.addEventListener('keydown',function(e){if(e.key=='Enter')send()});",
    "var CLAST=0,CTMR=null,NEWMSG=0;\n"
    "function chatBadge(){var b=document.querySelector('[data-act=\"showchat\"]');if(b)b.textContent=NEWMSG>0?'💬'+NEWMSG:'💬'}\n"
    "function chatRender(ms){var box=document.getElementById('cmsg');ms.forEach(function(m){if(m.id<=CLAST)return;CLAST=m.id;var d=document.createElement('div');d.style.cssText='background:#202834;border-radius:6px;padding:6px 8px';d.innerHTML='<b style=\"color:#7cc0f4\">'+esc(m.name)+'</b> <small style=\"color:#8fa3b8\">'+esc(m.ts)+'</small><br>'+esc(m.text);box.appendChild(d)});box.scrollTop=box.scrollHeight}\n"
    "function chatPoll(){J('/chat/poll',{token:TK,last:CLAST}).then(function(r){chatRender(r.msgs||[])})}\n"
    "setInterval(function(){if(TK&&document.getElementById('chatbox').style.display!='flex'){J('/chat/poll',{token:TK,last:CLAST}).then(function(r){var ms=r.msgs||[];if(ms.length){NEWMSG+=ms.length;chatBadge()}})}},15000);\n"
    "qinp.addEventListener('keydown',function(e){if(e.key=='Enter')send()});\n"
    "lg.addEventListener('keydown',function(e){if(e.key=='Enter')document.querySelector('[data-act=\"login\"]').click()});\n"
    "pw.addEventListener('keydown',function(e){if(e.key=='Enter')document.querySelector('[data-act=\"login\"]').click()});\n"
    "document.getElementById('cin').addEventListener('keydown',function(e){if(e.key=='Enter')document.querySelector('[data-act=\"chatsend\"]').click()});",
    "чат-JS и Enter")
rep("else if(a=='chip'){qinp.value=el.getAttribute('data-val');send()}});",
    "else if(a=='chip'){qinp.value=el.getAttribute('data-val');send()}\n"
    "else if(a=='showchat'){var cb=document.getElementById('chatbox');if(cb.style.display=='flex'){cb.style.display='none';if(CTMR){clearInterval(CTMR);CTMR=null}}else{cb.style.display='flex';CLAST=0;document.getElementById('cmsg').innerHTML='';chatPoll();if(CTMR)clearInterval(CTMR);CTMR=setInterval(chatPoll,5000);NEWMSG=0;chatBadge()}}\n"
    "else if(a=='chatsend'){var t=document.getElementById('cin').value;J('/chat/send',{token:TK,text:t}).then(function(r){if(r.ok){document.getElementById('cin').value='';chatPoll()}})}});",
    "ветки чата в обработчике")

# --- панель: свёрнута, треугольники ---
rep('<div class="gbody">', '<div class="gbody" style="display:none">', "группы свёрнуты", True)
rep('data-act="fold">▾ ', 'data-act="fold">▸ ', "треугольники ▸", True)
rep("else if(a=='fold'){var b=el.nextElementSibling;b.style.display=b.style.display=='none'?'block':'none'}",
    "else if(a=='fold'){var b=el.nextElementSibling;var hid=b.style.display=='none';b.style.display=hid?'block':'none';el.textContent=(hid?'▾':'▸')+el.textContent.slice(1)}", "fold треугольник")
io.open(ap, "w", encoding="utf-8").write(s)

# --- ctl.py ---
cp = r"D:\AI\tools\agent\ctl.py"
c = io.open(cp, encoding="utf-8").read()
lines = c.splitlines(True)
out, ch = [], False
for ln in lines:
    if "powershell -NoProfile -WindowStyle Hidden" in ln and "agent.py" in ln:
        ind = ln.index("subprocess.Popen")
        ln = ln[:ind] + "subprocess.Popen('cmd /c cd /d %s && python agent.py >> %sagent_console.log 2>&1' % (AG, TOOLS), shell=True, creationflags=0x08000000)\n"
        ch = True
    out.append(ln)
c = "".join(out)
print("[+] ctl: hidden без powershell" if ch else "[~] ctl hidden уже ок")
for old, new, tag in (
    ('cmd /k "cd /d %s && python agent.py"', 'cmd /c "cd /d %s && python agent.py"', "ctl /k→/c"),
    ('elif "restart" in a: down(); up("--browser" in a)', 'elif "restart" in a: down(); up("--browser" in a, "--hidden" in a)', "restart hidden"),
    ("'start \"CREOSON\" /D \"%s\" creoson_run.bat'", "'start \"CREOSON\" /MIN /D \"%s\" creoson_run.bat'", "creoson /MIN")):
    if new in c: print("[~] %s: уже" % tag)
    elif old in c: c = c.replace(old, new, 1); print("[+] %s" % tag)
    else: print("[x] %s: якорь не найден" % tag)
io.open(cp, "w", encoding="utf-8").write(c)

io.open(r"D:\AI\tools\agent\AI_RESTART.bat", "w").write(
    "@echo off\ntaskkill /F /IM python.exe >nul 2>&1\ntimeout /t 2 /nobreak >nul\npython D:\\AI\\tools\\agent\\ctl.py up --hidden\n")
print("[+] AI_RESTART.bat")
print("ВСЁ: .\\AI_RESTART.bat, затем Ctrl+Shift+R")