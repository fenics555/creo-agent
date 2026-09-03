# -*- coding: utf-8 -*-
import re
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")
ap = AG / "agent.py"; a = ap.read_text(encoding="utf-8"); ch = False

if "def _log(line): _log(line);" in a:
    a = a.replace("def _log(line): _log(line); LIVE.setdefault(client, []).append(line)",
                  "def _log(line): steps_log.append(line); LIVE.setdefault(client, []).append(line)", 1)
    ch = True; print("[+] _log: рекурсия убрана")

i = a.find('_SYS_CACHE["v"] = p + ')
if i >= 0:
    j = a.find("\n", i)
    if "return _SYS_CACHE" not in a[j+1:j+40]:
        a = a[:j+1] + '    return _SYS_CACHE["v"]\n' + a[j+1:]
        ch = True; print("[+] build_system: return возвращён")

GOOD_SEND = r'''function send(){var q=qinp.value;if(!q)return;qinp.value='';addMsg(esc(q),true);var d=addMsg('🤔 думаю...');var sp=document.getElementById('spin');if(sp)sp.style.display='inline-block';
var TKI=0,ST2=setInterval(function(){J('/livetoks?last='+TKI).then(function(g){(g.toks||[]).forEach(function(t){TKI++;var s=d.querySelector('.stream')||(function(){var e=document.createElement('div');e.className='stream';d.appendChild(e);return e})();s.textContent+=t;chat.scrollTop=chat.scrollHeight;});});},120);
var LV=0,LT=setInterval(function(){J('/livesteps?last='+LV).then(function(g){(g.lines||[]).forEach(function(l){LV++;var lg=d.querySelector('.live')||(function(){var e=document.createElement('div');e.className='log live';d.appendChild(e);return e})();lg.textContent+='· '+l+'\n';chat.scrollTop=chat.scrollHeight;});});},700);
J('/ask',{token:TK,q:q,image:IMG}).then(function(r){clearInterval(LT);clearInterval(ST2);if(sp)sp.style.display='none';if(r&&r.error){localStorage.removeItem('tk');TK='';showLogin();d.innerHTML='⚠ нужен вход';return}IMG=null;render(d,r)}).catch(function(e){clearInterval(LT);clearInterval(ST2);if(sp)sp.style.display='none';d.innerHTML='ошибка: '+esc(e)})}
'''
a2, n = re.subn(r"function send\(\)\{[\s\S]*?\nfunction render\(", GOOD_SEND + "function render(", a, count=1)
if n: a = a2; ch = True; print("[+] send(): заменена на проверенную")

GOOD_WRAP = r'''(function(){var sp=document.getElementById('spin');if(!sp)return;var of=window.fetch;window.fetch=function(u){var url=String(u);var bg=url.indexOf('/chat/poll')>=0||url.indexOf('/status')>=0||url.indexOf('/ask')>=0;if(!bg)sp.style.display='inline-block';var p=of.apply(this,arguments);var t=new Promise(function(r,j){setTimeout(function(){j(new Error('таймаут 300с: '+url))},300000)});return Promise.race([p,t]).finally(function(){if(!bg)sp.style.display='none';});};})();'''
a2, n = re.subn(r"\(function\(\)\{var sp=document\.getElementById\('spin'\)[\s\S]*?\}\)\(\);", GOOD_WRAP, a, count=1)
if n: a = a2; ch = True; print("[+] fetch-обёртка: 300с, /ask вне гонки")

if "cwd=str(core.BASE)" in a:
    a = a.replace("cwd=str(core.BASE)", 'cwd=r"D:\\AI\\tools\\agent"')
    ch = True; print("[+] /rescan,/scan: cwd = папка агента")

if ch: ap.write_text(a, encoding="utf-8")
s = ap.read_text(encoding="utf-8")
print("CHECK _log:", [l.strip() for l in s.split("\n") if "def _log" in l])
print("CHECK return:", [l.strip() for l in s.split("\n") if "return _SYS_CACHE" in l])
print("CHECK legacy(должно False):", "function legacy" in s)
print("CHECK bg:", [l.strip() for l in s.split("\n") if "var bg=" in l][0][:140])
print("CHECK cwd:", [l.strip() for l in s.split("\n") if "cwd=" in l])
print("ГОТОВО: .\\AI_RESTART.bat + Ctrl+F5")