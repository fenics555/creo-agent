# -*- coding: utf-8 -*-
"""PAGE/panel UI agent v14 (auto-split agent.py 2026-09-11). Change here, not agent.py."""
PAGE = r"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>АГЕНТ v14</title>
<style>body{margin:0;background:#14181f;color:#dfe6ee;font:14px/1.5 Segoe UI,sans-serif}
#top{position:fixed;top:0;left:0;right:0;background:#1b222b;padding:8px 14px;display:flex;gap:10px;align-items:center;z-index:5}
#top b{color:#6db3f2}#chat{margin:52px 300px 70px 12px;padding:8px;overflow-y:auto}
#panel{position:fixed;top:44px;right:0;bottom:0;width:292px;background:#171d26;overflow-y:auto;padding:8px}
.msg{max-width:760px;margin:10px 0;padding:10px 14px;border-radius:10px;background:#202834;white-space:pre-wrap}
.msg.me{margin-left:auto;background:#2b4a6f}
.think{background:#1a2129;border:1px solid #2c3644;border-radius:8px;padding:6px 10px;margin-bottom:4px;color:#9fb0c3;cursor:pointer}
.thinkbody{background:#1a2129;border:1px solid #2c3644;border-radius:8px;padding:6px 10px;margin-bottom:8px;color:#9fb0c3;white-space:pre-wrap}
.log{color:#8fa3b8;font-size:12px;margin:6px 0;white-space:pre-wrap}
#inp{position:fixed;bottom:0;left:0;right:292px;background:#1b222b;padding:8px;display:flex;gap:8px}
#q{flex:1;background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:8px;padding:10px}
button{background:#2b4a6f;color:#fff;border:0;border-radius:8px;padding:8px 14px;cursor:pointer}
.spin{display:inline-block;width:16px;height:16px;border:2px solid #6db3f2;border-top-color:transparent;border-radius:50%;animation:rot .8s linear infinite;vertical-align:middle;margin-left:8px}
@keyframes rot{to{transform:rotate(360deg)}}
.grp{border:1px solid #243040;border-radius:8px;margin:6px 0;padding:6px}
.grp h4{margin:2px 0 6px;color:#6db3f2;cursor:pointer}
.tool{background:#202834;border-radius:6px;padding:6px;margin:4px 0;cursor:pointer}
.tool b{color:#7cc0f4}.tool small{display:block;color:#8fa3b8}
#login{position:fixed;inset:0;background:#0009;display:none;align-items:center;justify-content:center;z-index:9}
#login div{background:#1b222b;padding:24px;border-radius:12px;display:flex;flex-direction:column;gap:10px}
#login input{background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:8px;padding:10px}</style></head>
<body>
<div id="top"><b>АГЕНТ v14</b><span id="hdr"></span><span style="flex:1"></span>
<button data-act="chip" data-val="guide">❓</button><button data-act="wizard">🧙</button><button data-act="showlog">Лог</button><button data-act="panel">Панель</button><button data-act="showpro">👤</button><button data-act="showchat">💬</button><button data-act="logout">Выйти</button></div>
<div id="chat"></div><div id="panel"></div>
<div id="inp"><input id="q" placeholder="Задача для АГЕНТА... (Enter) | Ctrl+V — вставить скриншот"><button data-act="snap">📷</button><button data-act="send">Спросить</button><span id="spin" class="spin" style="display:none"></span></div>
<div id="login"><div style="position:relative"><button data-act="closelogin" style="position:absolute;top:6px;right:6px;background:#334052;color:#fff;border:0;border-radius:6px;padding:2px 8px;cursor:pointer">✕</button>
<input id="lg" placeholder="логин"><input id="pw" type="password" placeholder="пароль"><button data-act="login">Войти</button><button data-act="reg">Регистрация</button></div></div>
<div id="wiz" style="display:none;position:fixed;inset:0;background:#0009;align-items:center;justify-content:center;z-index:11">
<div style="background:#1b222b;padding:20px;border-radius:12px;width:430px;display:flex;flex-direction:column;gap:9px;border:1px solid #334052">
<b>🧙 МАСТЕР ОПЕРАЦИЙ</b>
<small style="color:#8fa3b8">Копия сборки (сначала план)</small>
<input id="w_old" placeholder="старое имя (old)" style="background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:8px">
<input id="w_new" placeholder="новое имя (new)" style="background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:8px">
<label style="color:#8fa3b8"><input type="checkbox" id="w_dry" checked> только план (dry_run)</label>
<button data-act="w_copy" style="background:#2b4a6f;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer">📋 Сделать копию</button>
<hr style="border-color:#243040">
<button data-act="w_audit" style="background:#2b4a6f;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer">🔍 Аудит папки Creo</button>
<button data-act="w_usage" style="background:#2b4a6f;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer">🧩 Пересобрать «где используется»</button>
<button data-act="w_night" style="background:#2b4a6f;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer">🌙 Ночной прогон</button>
<button data-act="w_close" style="background:#334052;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer">Закрыть</button>
</div></div>
<div id="pro" style="display:none;position:fixed;inset:0;background:#0009;align-items:center;justify-content:center;z-index:10">
<div style="background:#1b222b;padding:24px;border-radius:12px;width:340px;display:flex;flex-direction:column;gap:10px;border:1px solid #334052">
<b>👤 ПРОФИЛЬ</b><span id="proinfo" style="color:#9fb0c3;font-size:13px"></span>
<input id="pname" placeholder="Новое имя" style="background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:8px">
<button data-act="savename" style="background:#2b4a6f;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer">Сохранить имя</button>
<input id="pold" type="password" placeholder="Старый пароль" style="background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:8px">
<input id="pnew" type="password" placeholder="Новый пароль (мин 4)" style="background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:8px">
<button data-act="savepw" style="background:#2b4a6f;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer">Сменить пароль</button>
<button id="adm_btn" data-act="openadm" style="display:none;background:#4a6f2b;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer;margin-top:6px">👥 Админка</button>
<button data-act="closepro" style="background:#334052;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer">Закрыть</button>
</div></div>
<div id="adm" style="display:none;position:fixed;inset:0;background:#0009;align-items:center;justify-content:center;z-index:10">
<div style="background:#1b222b;padding:24px;border-radius:12px;width:520px;max-height:80%;overflow:auto;display:flex;flex-direction:column;gap:8px;border:1px solid #334052">
<b>👥 АДМИНКА: пользователи</b><div id="ulist" style="max-height:40%;overflow:auto"></div>
<div style="display:flex;gap:6px;flex-wrap:wrap">
<input id="nlog" placeholder="логин" style="background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:8px">
<input id="npw" type="password" placeholder="пароль" style="background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:8px">
<select id="nrole" style="background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:8px"></select>
<button data-act="adduser" style="background:#2b4a6f;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer">+ добавить</button>
</div>
<button data-act="closeadm" style="background:#334052;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer;margin-top:6px">Закрыть</button>
</div></div>
<div id="chatbox" style="display:none;position:fixed;top:44px;left:0;bottom:0;width:340px;background:#171d26;border-right:1px solid #243040;padding:10px;z-index:6;flex-direction:column;gap:8px">
<b>💬 КОМАНДА</b><div id="cmsg" style="flex:1;overflow:auto;display:flex;flex-direction:column;gap:6px"></div>
<div style="display:flex;gap:6px"><input id="cin" placeholder="Сообщение всем..." style="flex:1;background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:8px">
<button data-act="chatsend" style="background:#2b4a6f;color:#fff;border:0;border-radius:6px;padding:8px;cursor:pointer">➤</button></div>
</div>
<script>
var TK=localStorage.getItem('tk')||'',IMG=null,CURM='';
var chat=document.getElementById('chat'),panel=document.getElementById('panel'),
qinp=document.getElementById('q'),login=document.getElementById('login'),
hdr=document.getElementById('hdr'),lg=document.getElementById('lg'),pw=document.getElementById('pw');
function J(u,b){return fetch(u,{method:b?'POST':'GET',headers:{'Content-Type':'application/json','X-Token':TK||''},body:b?JSON.stringify(b):undefined}).then(function(r){return r.json()})}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function att(s){return esc(s).replace(/"/g,'&quot;')}
function addMsg(html,me){var d=document.createElement('div');d.className='msg'+(me?' me':'');d.innerHTML=html;chat.appendChild(d);chat.scrollTop=chat.scrollHeight;return d}
function showLogin(){login.style.display='flex';hdr.textContent='';panel.innerHTML=''}
function send(){var q=qinp.value;if(!q)return;qinp.value='';addMsg(esc(q),true);var d=addMsg('🤔 думаю...');var sp=document.getElementById('spin');if(sp)sp.style.display='inline-block';
var TKI=0,ST2=setInterval(function(){J('/livetoks?last='+TKI).then(function(g){(g.toks||[]).forEach(function(t){TKI++;var s=d.querySelector('.stream')||(function(){var e=document.createElement('div');e.className='stream';d.appendChild(e);return e})();s.textContent+=t;chat.scrollTop=chat.scrollHeight;});});},120);
var LV=0,LT=setInterval(function(){J('/livesteps?last='+LV).then(function(g){(g.lines||[]).forEach(function(l){LV++;var lg=d.querySelector('.live')||(function(){var e=document.createElement('div');e.className='log live';d.appendChild(e);return e})();lg.textContent+=String.fromCharCode(10)+'· '+l;chat.scrollTop=chat.scrollHeight;});});},700);
var THI=0,THB=null,TT=setInterval(function(){J('/livethink?last='+THI).then(function(g){(g.toks||[]).forEach(function(t){THI++;if(!THB){THB=document.createElement('div');THB.className='thinkbody';d.appendChild(THB);}THB.textContent+=t;chat.scrollTop=chat.scrollHeight;});});},700);
J('/ask',{token:TK,q:q,image:IMG}).then(function(r){d._query=q;clearInterval(LT);clearInterval(ST2);clearInterval(TT);if(sp)sp.style.display='none';if(r&&r.error){localStorage.removeItem('tk');TK='';showLogin();d.innerHTML='⚠ нужен вход';return}IMG=null;render(d,r)}).catch(function(e){clearInterval(LT);clearInterval(ST2);clearInterval(TT);if(sp)sp.style.display='none';d.innerHTML='ошибка: '+esc(e)})}
function render(d,r){var h='';
if(r.think)h+='<div class="think" data-act="think">🧠 размышления (клик)</div><div class="thinkbody" style="display:block">'+esc(r.think)+'</div>';
if(r.log&&r.log.length&&(window.CFG||{}).show_steps!==0)h+='<div class="log">🔎 ХОД РАБОТЫ:\n'+r.log.map(esc).join('\n')+'</div>';
h+='<div>'+esc(String(r.answer).replace(/<\/?think>/g,''))+'</div>';
d._r=r;
if(String(r.answer).indexOf('[СОГЛАСОВАНИЕ]')<0)h+='<div style="margin-top:6px"><button data-act="fb" data-ok="1">✅ попал</button> <button data-act="fb" data-ok="0">❌ не попал</button></div>';
var m=String(r.answer).match(/id (\d+)/);
if(String(r.answer).indexOf('[СОГЛАСОВАНИЕ]')>=0&&m)h+='<div style="margin-top:8px"><button data-act="appr" data-pid="'+m[1]+'" data-ok="1">✅ выполнить</button> <button data-act="appr" data-pid="'+m[1]+'" data-ok="0">❌ отмена</button></div>';
d.innerHTML=h;chat.scrollTop=chat.scrollHeight}
function buildPanel(p){p=p||{actions:[],models:[],chips:[],groups:[]};var h='<div class="grp"><h4 data-act="fold">▸ ⚙ ДЕЙСТВИЯ (без ИИ)</h4><div class="gbody" style="display:none">';
(p.actions||[]).forEach(function(a){h+='<div class="tool" data-act="act" data-val="'+a.endpoint+'"><b>'+esc(a.label)+'</b></div>'});h+='</div></div>';
h+='<div class="grp"><h4 data-act="fold">▸ 🧠 МОДЕЛЬ ИИ (клик — смена)</h4><div class="gbody" style="display:none">';
(p.models||[]).forEach(function(m){h+='<div class="tool" data-act="setm" data-val="'+att(m)+'">'+esc(m)+(m==CURM?' ←':'')+'</div>'});h+='</div></div>';
h+='<div class="grp"><h4 data-act="fold">▸ ⚡ БЫСТРЫЕ ЗАДАЧИ</h4><div class="gbody" style="display:none">';
(p.chips||[]).forEach(function(c){h+='<div class="tool" data-act="chip" data-val="'+att(c)+'">'+esc(c)+'</div>'});h+='</div></div>';
(p.groups||[]).forEach(function(g){h+='<div class="grp"><h4 data-act="fold">▸ '+esc(g.title)+' ('+g.tools.length+')</h4><div class="gbody" style="display:none">';
g.tools.forEach(function(t){h+='<div class="tool" data-act="chip" data-val="'+att(t.name)+'"><b>'+esc(t.name)+(t.approval?' 🔒':'')+'</b><small>'+esc(t.desc)+'</small></div>'});h+='</div></div>'});
panel.innerHTML=h}
function buildSettings(s){var h='<div class="grp"><h4 data-act="fold">▸ НАСТРОЙКИ (ползунки)</h4><div class="gbody" style="display:none">';
s.items.forEach(function(it){(window.CFG=window.CFG||{})[it.key]=it.value;h+='<div class="tool"><small>'+esc(it.space)+' · '+esc(it.name)+'</small>';
if(it.kind=='range'){h+='<input type="range" data-cfg="'+att(it.key)+'" min="'+it.min+'" max="'+it.max+'" step="'+it.step+'" value="'+it.value+'" style="width:100%"><b data-v="'+att(it.key)+'"> '+it.value+'</b>';}
else if(it.kind=='check'){h+='<input type="checkbox" data-cfg="'+att(it.key)+'" '+(it.value?'checked':'')+'>';}
else{h+='<input data-cfg="'+att(it.key)+'" value="'+att(String(it.value))+'" style="width:100%;background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:4px">';}
h+='</div>';});
h+='</div></div>';panel.innerHTML+=h;}
function init(){J('/status').then(function(s){CURM=s.model;hdr.textContent=s.host+(s.user?' | '+(s.user.display_name||s.user.login):'')+' | '+s.model+' | блоков: '+s.blocks;J('/panel').then(function(p){buildPanel(p);J('/settings').then(buildSettings)})})}
document.addEventListener('click',function(e){var el=e.target.closest('[data-act]');if(!el)return;var a=el.getAttribute('data-act');
if(a=='think'){var n=el.nextElementSibling;n.style.display=n.style.display=='none'?'block':'none'}
else if(a=='fold'){var b=el.nextElementSibling;var hid=b.style.display=='none';b.style.display=hid?'block':'none';el.textContent=(hid?'▾':'▸')+el.textContent.slice(1)}
else if(a=='send')send();
else if(a=='wizard'){document.getElementById('wiz').style.display='flex'}
else if(a=='w_close'){document.getElementById('wiz').style.display='none'}
else if(a=='w_copy'){var o=document.getElementById('w_old').value,n=document.getElementById('w_new').value;if(!o||!n){alert('заполни old и new');return}document.getElementById('wiz').style.display='none';qinp.value='copy_model old='+o+' new='+n+' dry_run='+(document.getElementById('w_dry').checked?1:0);send()}
else if(a=='w_audit'){document.getElementById('wiz').style.display='none';qinp.value='creo_audit_folder';send()}
else if(a=='w_usage'){document.getElementById('wiz').style.display='none';qinp.value='usage_build full=1';send()}
else if(a=='w_night'){document.getElementById('wiz').style.display='none';qinp.value='nightly_run';send()}
else if(a=='snap')J('/snap',{token:TK}).then(function(r){addMsg(esc(r.msg||'ок'))});
else if(a=='showlog')J('/log').then(function(r){addMsg('<div class="log">'+esc(r.log)+'</div>')});
else if(a=='panel')panel.style.display=panel.style.display=='none'?'block':'none';
else if(a=='logout'){localStorage.removeItem('tk');localStorage.removeItem('usr');TK='';showLogin()}
else if(a=='showpro'){J('/profile',{token:TK}).then(function(u){document.getElementById('proinfo').textContent=(u.display_name||'')+' · '+(u.role||'')+' · '+u.login;document.getElementById('pname').value=u.display_name||'';document.getElementById('pro').style.display='flex';document.getElementById('adm_btn').style.display=u.can_manage?'block':'none'})}
else if(a=='closepro'){document.getElementById('pro').style.display='none'}
else if(a=='savename'){var v=document.getElementById('pname').value;J('/setname',{token:TK,name:v}).then(function(r){alert(r.msg||'ок');if(r.ok){document.getElementById('pro').style.display='none';init()}})}
else if(a=='savepw'){J('/setpw',{token:TK,old:document.getElementById('pold').value,'new':document.getElementById('pnew').value}).then(function(r){alert(r.msg||'ок');if(r.ok){document.getElementById('pold').value='';document.getElementById('pnew').value=''}})}
else if(a=='openadm'){document.getElementById('pro').style.display='none';document.getElementById('adm').style.display='flex';J('/admin/users',{token:TK,op:'list'}).then(function(r){var out='';(r.users||[]).forEach(function(u){out+='<div style="padding:6px;background:#202834;border-radius:6px;margin:3px 0;display:flex;gap:6px;align-items:center"><b>'+esc(u.display_name)+'</b> <small style="color:#8fa3b8">('+esc(u.login)+')</small> ';out+='<select class="rsel" data-login="'+att(u.login)+'" style="background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:4px;padding:4px">';(r.roles||[]).forEach(function(role){out+='<option'+(role===u.role?' selected':'')+'>'+esc(role)+'</option>'});out+='</select> ';out+='<button data-act="do_role" data-login="'+att(u.login)+'" style="background:#2b4a6f;color:#fff;border:0;border-radius:4px;padding:4px 8px;cursor:pointer">роль</button> ';out+='<button data-act="do_resetpw" data-login="'+att(u.login)+'" style="background:#6f4a2b;color:#fff;border:0;border-radius:4px;padding:4px 8px;cursor:pointer">сброс pw</button> <button data-act="do_del" data-login="'+att(u.login)+'" style="background:#6f2b2b;color:#fff;border:0;border-radius:4px;padding:4px 8px;cursor:pointer">удалить</button></div>'});document.getElementById('ulist').innerHTML=out||'(пусто)';var sel=document.getElementById('nrole');if(sel)sel.innerHTML=(r.roles||[]).map(function(x){return '<option>'+esc(x)+'</option>'}).join('')})}
else if(a=='closeadm'){document.getElementById('adm').style.display='none'}
else if(a=='do_role'){var lgn=el.getAttribute('data-login');var sel=document.querySelector('.rsel[data-login="'+lgn+'"]');J('/admin/users',{token:TK,op:'role',login:lgn,role:sel.value}).then(function(r){alert(r.msg||'ок')})}
else if(a=='do_del'){var lgn=el.getAttribute('data-login');if(!confirm('Удалить пользователя '+lgn+'?'))return;J('/admin/users',{token:TK,op:'delete',login:lgn}).then(function(r){alert(r.msg||'ок');if(r.ok){document.getElementById('adm').style.display='none';setTimeout(function(){document.getElementById('adm').style.display='flex';document.querySelector('[data-act="openadm"]').click()},100)}})}
else if(a=='do_resetpw'){var lgn=el.getAttribute('data-login');var nw=prompt('Новый пароль для '+lgn+' (мин 4):');if(nw)J('/admin/users',{token:TK,op:'resetpw',login:lgn,pw:nw}).then(function(r){alert(r.msg||'ок')})}
else if(a=='adduser'){J('/admin/users',{token:TK,op:'add',login:document.getElementById('nlog').value,pw:document.getElementById('npw').value,role:document.getElementById('nrole').value}).then(function(r){alert(r.msg||'ок');if(r.ok){document.getElementById('nlog').value='';document.getElementById('npw').value='';document.getElementById('adm').style.display='none';setTimeout(function(){document.getElementById('adm').style.display='flex';document.querySelector('[data-act="openadm"]').click()},100)}})}
else if(a=='closelogin'){login.style.display='none'}
else if(a=='login')J('/login',{login:document.getElementById('lg').value,pw:document.getElementById('pw').value}).catch(function(e){alert('сервер недоступен: '+e);throw e}).then(function(r){if(r.ok){TK=r.token;localStorage.setItem('tk',TK);localStorage.setItem('usr',lg.value);login.style.display='none';init();if(!localStorage.getItem('seen_guide')){localStorage.setItem('seen_guide','1');setTimeout(function(){qinp.value='guide';send()},400)}}else alert('неверный логин или пароль')});
else if(a=='reg')J('/register',{login:lg.value,pw:pw.value}).then(function(r){alert(r.msg||'ок')});
else if(a=='appr'){var sp2=document.getElementById('spin');if(sp2)sp2.style.display='inline-block';J('/approve',{token:TK,pid:el.getAttribute('data-pid'),ok:el.getAttribute('data-ok')=='1'}).then(function(r){if(sp2)sp2.style.display='none';addMsg(esc((r.res||'')+((r.answer&&r.answer!==r.res)?'\n\n'+r.answer:'')))});}
else if(a=='fb'){var okv=el.getAttribute('data-ok')=='1';var cm=okv?'':prompt('Короткий комментарий (почему не попал):','');if(!okv&&cm===null)return;var dd=el.closest('.msg');var rr=dd&&dd._r?dd._r:{};var tool='';if(rr.log&&rr.log.length){var mm=String(rr.log[rr.log.length-1]).match(/^([A-Za-z0-9_]+)\(/);if(mm)tool=mm[1]}J('/feedback',{token:TK,query:dd&&dd._query?dd._query:'',think:rr.think||'',tool:tool,result:rr.answer||'',ok:okv?1:0,comment:cm||''}).then(function(fb){el.parentNode.innerHTML='<span style="color:#8fa3b8">оценка сохранена</span>'})}
else if(a=='setm')J('/setmodel',{token:TK,model:el.getAttribute('data-val')}).then(function(){init()});
else if(a=='act'){var ep=el.getAttribute('data-val');if(ep=='/log'){J('/log').then(function(r){addMsg('<div class="log">'+esc(r.log)+'</div>')})}else J(ep,{token:TK}).then(function(r){addMsg('<div class="log">'+esc(JSON.stringify(r).slice(0,800))+'</div>')})}
else if(a=='chip'){qinp.value=el.getAttribute('data-val');send()}
else if(a=='showchat'){var cb=document.getElementById('chatbox');if(cb.style.display=='flex'){cb.style.display='none';if(CTMR){clearInterval(CTMR);CTMR=null}}else{cb.style.display='flex';CLAST=0;document.getElementById('cmsg').innerHTML='';chatPoll();if(CTMR)clearInterval(CTMR);CTMR=setInterval(chatPoll,5000);NEWMSG=0;chatBadge()}}
else if(a=='closechat'){document.getElementById('chatbox').style.display='none';if(CTMR){clearInterval(CTMR);CTMR=null}}
else if(a=='chatsend'){var t=document.getElementById('cin').value;J('/chat/send',{token:TK,text:t}).then(function(r){if(r.ok)document.getElementById('cin').value='';chatPoll()})}});
var CLAST=0,CTMR=null;
function chatRender(ms){var box=document.getElementById('cmsg');ms.forEach(function(m){if(m.id<=CLAST)return;CLAST=m.id;var d=document.createElement('div');d.style.cssText='background:#202834;border-radius:6px;padding:6px 8px';d.innerHTML='<b style="color:#7cc0f4">'+esc(m.name)+'</b> <small style="color:#8fa3b8">'+esc(m.ts)+'</small><br>'+esc(m.text);box.appendChild(d)});box.scrollTop=box.scrollHeight}
function chatPoll(){J('/chat/poll',{token:TK,last:CLAST}).then(function(r){chatRender(r.msgs||[])})}
var NEWMSG=0;
function chatBadge(){var b=document.querySelector('[data-act="showchat"]');if(b)b.textContent=NEWMSG>0?'💬'+NEWMSG:'💬'}
setInterval(function(){if(document.getElementById('chatbox').style.display!='flex'&&TK){J('/chat/poll',{token:TK,last:CLAST}).then(function(r){var ms=r.msgs||[];if(ms.length){NEWMSG+=ms.length;chatBadge()}})}},15000)
qinp.addEventListener('keydown',function(e){if(e.key=='Enter')send()});
document.addEventListener('paste',function(e){var it=null,items=e.clipboardData.items;for(var i=0;i<items.length;i++){if(items[i].type.indexOf('image')==0){it=items[i];break}}if(!it)return;var f=it.getAsFile();var rd=new FileReader();rd.onload=function(){IMG=rd.result.split(',')[1];addMsg('📷 скриншот прикреплён',true)};rd.readAsDataURL(f)});
lg.addEventListener('keydown',function(e){if(e.key=='Enter')document.querySelector('[data-act="login"]').click()});
pw.addEventListener('keydown',function(e){if(e.key=='Enter')document.querySelector('[data-act="login"]').click()});
document.getElementById('cin').addEventListener('keydown',function(e){if(e.key=='Enter')document.querySelector('[data-act="chatsend"]').click()});
if(TK){Promise.resolve().then(init).catch(function(e){addMsg('ошибка инициализации: '+e,true)})}else showLogin();
(function(){var sp=document.getElementById('spin');if(!sp)return;var of=window.fetch;window.fetch=function(u){var url=String(u);var bg=url.indexOf('/chat/poll')>=0||url.indexOf('/status')>=0||url.indexOf('/ask')>=0;if(!bg)sp.style.display='inline-block';var p=of.apply(this,arguments);var t=new Promise(function(r,j){setTimeout(function(){j(new Error('таймаут 900с: '+url))},900000)});return Promise.race([p,t]).finally(function(){if(!bg)sp.style.display='none';});};})();
(function(){if(window.__slfix)return;window.__slfix=1;
var busy=false;
function sync(r){var lab=r.parentNode.querySelector('[data-v]')||r.nextElementSibling;if(lab&&String(lab.textContent)!==String(r.value))lab.textContent=r.value;}
document.addEventListener('input',function(e){var r=e.target;if(r&&r.type=='range'&&r.getAttribute('data-cfg'))sync(r);});
document.addEventListener('change',function(e){var r=e.target;var k=r.getAttribute&&r.getAttribute('data-cfg');if(!k)return;if(r.type!='range'&&r.type!='checkbox')return;var v=(r.type=='checkbox')?(r.checked?1:0):r.value;fetch('/setcfg',{method:'POST',headers:{'Content-Type':'application/json','X-Token':window.TK||''},body:JSON.stringify({key:k,value:v})});});
var mo=new MutationObserver(function(){if(busy)return;busy=true;try{document.querySelectorAll('input[type=range][data-cfg]').forEach(function(r){var want=parseFloat(r.getAttribute('data-val')||r.value);if(!isNaN(want)){if(parseFloat(r.max)<want)r.max=want;if(String(r.value)!==String(want))r.value=want;sync(r);}});}finally{busy=false;}});
mo.observe(document.body,{childList:true,subtree:true});
window.addEventListener('unhandledrejection',function(){var sp=document.getElementById('spin');if(sp)sp.style.display='none';});})();
/*lm-deco*/(function(){var N=['авто','авто+токены','отладка','полный'];function dec(){var b=document.querySelector('[data-v="log_mode"]');if(!b)return;var v=parseInt(b.textContent,10);var w=v+' · '+(N[v]||'');if(b.textContent!=w)b.textContent=w;}document.addEventListener('input',function(e){var t=e.target;if(t&&t.getAttribute&&t.getAttribute('data-cfg')=='log_mode')setTimeout(dec,0);});setInterval(dec,1000);dec();})();
</script></body></html>"""
