var NAME_RE = new RegExp("[A-Za-z0-9_.-]+?[.](?:prt|asm|drw)", "gi");
var PDF_NAME_RE = /[A-Za-z0-9_.-]+\.pdf/gi;

var DETAILS_RE = /\[DETAILS:([A-Za-z0-9_]+)(?:\|([^\]]*))?\]([\s\S]*?)\[\/DETAILS\]/g;
var TAGS_RE = /\[\/?(ANSWER|TOOL)[^\]]*\]/g;
var foldKey = /[^A-Za-z0-9_а-яА-ЯёЁ]/gi;

var TK=localStorage.getItem('tk')||'',IMG=null,CURM='',MODELS=[],REG=[],LAY=localStorage.getItem('lay')||'v2';
var chat=document.getElementById('chat'),panel=document.getElementById('panel'),
qinp=document.getElementById('q'),login=document.getElementById('login'),
hdr=document.getElementById('hdr'),lg=document.getElementById('lg'),pw=document.getElementById('pw');
function J(u,b){return fetch(u,{method:b?'POST':'GET',headers:{'Content-Type':'application/json','X-Token':TK||''},body:b?JSON.stringify(b):undefined}).then(function(r){return r.json()})}
function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
function att(s){return esc(s).replace(new RegExp('"', 'g'),'&quot;')}

function addMsg(html,me){var d=document.createElement('div');d.className='msg'+(me?' me':'');var t=new Date().toLocaleTimeString([], {hour:'2-digit',minute:'2-digit',hour12:false});d.innerHTML='<small style="color:#A6A8AB;margin-right:5px;">'+t+'</small>'+html;chat.appendChild(d);chat.scrollTop=chat.scrollHeight;return d}
function showLogin(){login.style.display='flex';hdr.textContent='';panel.innerHTML=''}
function send(){var q=qinp.value;if(!q)return;qinp.value='';addMsg(esc(q),true);var d=addMsg('🤔 думаю...');var sp=document.getElementById('spin');if(sp)sp.style.display='inline-block';
var TKI=0,ST2=setInterval(function(){J('/livetoks?last='+TKI).then(function(g){(g.toks||[]).forEach(function(t){TKI++;var s=d.querySelector('.stream')||(function(){var e=document.createElement('div');e.className='stream';d.appendChild(e);return e})();s.textContent+=t;chat.scrollTop=chat.scrollHeight;});});},120);
var LV=0,LT=setInterval(function(){J('/livesteps?last='+LV).then(function(g){(g.lines||[]).forEach(function(l){LV++;var lg=d.querySelector('.live')||(function(){var e=document.createElement('div');e.className='log live';d.appendChild(e);return e})();lg.textContent+=String.fromCharCode(10)+'· '+l;chat.scrollTop=chat.scrollHeight;});});},700); // 10 = newline
var THI=0,THB=null,TT=setInterval(function(){J('/livethink?last='+THI).then(function(g){(g.toks||[]).forEach(function(t){THI++;if(!THB){THB=document.createElement('div');THB.className='thinkbody';d.appendChild(THB);}THB.textContent+=t;chat.scrollTop=chat.scrollHeight;});});},700);
J('/ask',{token:TK,q:q,image:IMG}).then(function(r){d._query=q;clearInterval(LT);clearInterval(ST2);clearInterval(TT);if(sp)sp.style.display='none';if(r&&r.error){localStorage.removeItem('tk');TK='';showLogin();d.innerHTML='⚠ нужен вход';return}IMG=null;render(d,r)}).catch(function(e){clearInterval(LT);clearInterval(ST2);clearInterval(TT);if(sp)sp.style.display='none';d.innerHTML='ошибка: '+esc(e)})}
function render(d,r){var h='';render._dseen={};
if(r.think)h+='<div class="think" data-act="think">🧠 размышления (клик)</div><div class="thinkbody" style="display:none">'+esc(r.think)+'</div>';
if(r.log&&r.log.length&&(window.CFG||{}).show_steps!==0)h+=`<div class="log">🔎 ХОД РАБОТЫ:
${r.log.map(esc).join(String.fromCharCode(10))}</div>`; // 10 = newline
var atxt=esc(String(r.answer).replace(new RegExp('[<][/]?think[>]', 'g'),''));
atxt=atxt.replace(DETAILS_RE, function(m,k,l,t){var lbl=l||'подробнее';if(!render._dseen)render._dseen={};if(render._dseen[k])return '';render._dseen[k]=1;return '<button class="sec" data-act="details-toggle" data-val="'+k+'" style="margin:2px">'+lbl+'</button>'+(t?'<div class="details-content" style="display:none; margin-left:10px; border-left:2px solid #555; padding-left:5px">'+t+'</div>':'');});
h+='<div>'+atxt+'</div><div class="pdfrow"></div>';
d._r=r;
if(String(r.answer).indexOf('[СОГЛАСОВАНИЕ]')<0)h+='<div style="margin-top:6px"><button data-act="fb" data-ok="1">✅ попал</button> <button data-act="fb" data-ok="0" class="sec">❌ не попал</button></div>';
var m=String(r.answer).match(new RegExp("id ([0-9]+)"));

if(String(r.answer).indexOf('[СОГЛАСОВАНИЕ]')>=0&&m)h+='<div style="margin-top:8px"><button data-act="appr" data-pid="'+m[1]+'" data-ok="1">✅ выполнить</button> <button data-act="appr" data-pid="'+m[1]+'" data-ok="0" class="sec">❌ отмена</button></div>';
d.innerHTML=h;scanPdf(d,String(r.answer||''));chat.scrollTop=chat.scrollHeight}
function badgeHtml(st){if(st=='актуален')return '<span class="badge" style="background:#86BC43">PDF актуален</span>';
if(st=='УСТАРЕЛ')return '<span class="badge" style="background:#E8912D">⚠ PDF устарел — обнови!</span>';
if(st=='нет чертежа')return '<span class="badge" style="background:#3E4043">нет чертежа</span>';
if(st=='нет pdf')return '<span class="badge" style="background:#3E4043">нет pdf</span>';return ''}
function addPdfBlock(row,nm){var box=document.createElement('div');box.className='pdfblk';box.innerHTML='<span class="nm">'+esc(nm)+'</span> <span style="color:#A6A8AB">…</span>';row.appendChild(box);
Promise.all([J('/pdfstatus?name='+encodeURIComponent(nm)).catch(function(){return{}}),J('/pdfpages?name='+encodeURIComponent(nm)).catch(function(){return{}})]).then(function(rr){var st=(rr[0]||{}).status||'';var pp=rr[1]||{};var h='<span class="nm">'+esc(nm)+'</span> <button class="sec" data-act="pdfthumb" data-val="'+att(nm)+'" style="padding:3px 8px">👁</button>'+badgeHtml(st);
if(pp.pages)h+=' <button class="sec" data-act="pdfref" data-val="'+att(nm)+'" style="padding:3px 8px">🔄 Обновить PDF</button>';
h+='<div>';var n=Math.min(pp.pages||0,8);for(var i=1;i<=n;i++){h+='<img class="thumb" data-act="lbx" src="/pdfimg?name='+encodeURIComponent(nm)+'&page='+i+'" width="84" height="60">'}h+='</div>';
box.innerHTML=h;
if(new RegExp("[.][a-zA-Z][a-zA-Z][a-zA-Z]$", "i").test(nm)){J('/children?name='+encodeURIComponent(nm)).catch(function(){return{}}).then(function(cc){var ch=(cc&&cc.children)||[];if(!ch.length)return;var s='<div style="font-size:12px;color:#A6A8AB">Состав: '+ch.length+' детей: ';ch.slice(0,12).forEach(function(c){s+='<span class="pin" data-act="childname" data-val="'+att(c)+'">'+esc(c)+'</span>'});s+='</div>';box.innerHTML+=s;});}})}
function scanPdf(d,ans){var row=d.querySelector('.pdfrow');if(!row)return;var mm=ans.match(NAME_RE)||[];var un=[];
mm.forEach(function(n){n=n.toLowerCase();if(un.indexOf(n)<0&&un.length<6)un.push(n)});
un.forEach(function(nm){addPdfBlock(row,nm)})}
var foldKey = new RegExp("[^A-Za-z0-9_а-яА-ЯёЁ]", "gi");
function buildPanel(p){p=p||{actions:[],models:[],chips:[],groups:[]};MODELS=p.models||[];
var h='<div class="grp"><h4 data-act="fold" data-fkey="state">▸ 🖥 СОСТОЯНИЕ АГЕНТА</h4><div class="gbody" style="display:none"><div class="mono" id="pstate" style="font-size:12px;color:#A6A8AB;white-space:pre-wrap">…</div></div></div>';
h+='<div class="grp"><input id="psearch" placeholder="поиск инструмента…"><small id="pfound" style="color:#A6A8AB"></small></div>';
h+='<div class="grp"><h4 data-act="fold">▸ ⚙ ДЕЙСТВИЯ (без ИИ)</h4><div class="gbody" style="display:none">';
(p.actions||[]).forEach(function(a){h+='<div class="tool" data-act="act" data-val="'+a.endpoint+'"><b>'+esc(a.label)+'</b></div>'});h+='</div></div>';
h+='<div class="grp"><h4 data-act="fold">▸ 🧠 МОДЕЛЬ ИИ (клик — смена)</h4><div class="gbody" style="display:none">';
(p.models||[]).forEach(function(m){h+='<div class="tool" data-act="setm" data-val="'+att(m)+'">'+esc(m)+(m==CURM?' ←':'')+'</div>'});h+='</div></div>';
h+='<div class="grp"><h4 data-act="fold">▸ ⚡ БЫСТРЫЕ ЗАДАЧИ</h4><div class="gbody" style="display:none">';
(p.chips||[]).forEach(function(c){h+='<div class="tool" data-act="chip" data-val="'+att(c)+'">'+esc(c)+'</div>'});h+='</div></div>';
h+='<div class="grp"><h4 data-act="fold">▸ 🧹 ОЧИСТКА</h4><div class="gbody" style="display:none"><div class="tool" data-act="open_purge"><b style="color:#4C8FD6">🧹 Мастер очистки</b></div></div></div>';
h+='<div class="grp"><h4 data-act="fold">▸ 📈 ХОД РАБОТ ДОМА</h4><div class="gbody" style="display:none"><div class="log jobsline" style="max-height:200px;overflow:auto">…</div><button class="sec" data-act="jobsload" style="padding:4px 9px;margin-top:6px">Обновить</button></div></div>';
h+='<div class="grp"><h4>📌 ЗАКРЕПЫ</h4>';['creo_get_active','models_find','search_kb','trail_problems','calc','creo_session'].forEach(function(n){h+='<span class="pin" data-act="chip" data-val="'+n+'">'+n+'</span>'});h+='</div>';
var FOLD=JSON.parse(localStorage.getItem('panel_fold')||'{}');
(p.groups||[]).forEach(function(g){var ti=g.title||'';var key=ti.replace(foldKey, "");
var open=FOLD[key];
h+='<div class="grp" data-gkey="'+key+'"><h4 data-act="fold" data-fkey="'+key+'">'+(open?'▾':'▸')+' '+esc(ti)+' ('+g.tools.length+')</h4><div class="gbody" style="display:'+(open?'block':'none')+'">';
g.tools.forEach(function(tl){h+='<div class="tool" data-act="chip" data-val="'+att(tl.name)+'" data-desc="'+att(tl.desc||'')+'"><b>'+((tl.icon||'')?tl.icon+' ':'')+esc(tl.name)+(tl.approval?' 🔒':'')+'</b><small>'+esc(tl.desc||'')+'</small></div>'});h+='</div></div>'});
panel.innerHTML=h;
var si=document.getElementById('psearch');if(si)si.addEventListener('input',function(){var q=si.value.toLowerCase();var n=0;
panel.querySelectorAll('.grp[data-gkey]').forEach(function(gr){var vis=0;gr.querySelectorAll('.tool').forEach(function(tl){var hit=!q||((tl.getAttribute('data-val')||'')+(tl.getAttribute('data-desc')||'')).toLowerCase().indexOf(q)>=0;tl.style.display=hit?'':'none';if(hit)vis++});n+=vis;gr.style.display=(q&&!vis)?'none':''});
var f=document.getElementById('pfound');if(f)f.textContent=q?('найдено: '+n):''});
loadReg();rlJobs()}
function buildSettings(s){var MK=['llm_model','model_fast','model_trail','model_vision','model_index'];
var hasMV=false;s.items.forEach(function(it){if(it.key=='model_vision')hasMV=true});
var skip=function(it){return it.key=='model_chat'||(it.key=='vision_model'&&hasMV)};
var find=function(k){var r=null;s.items.forEach(function(it){if(it.key==k)r=it});return r};
var h='<div class="grp"><h4 data-act="fold" data-fkey="settings">▸ ⚙ НАСТРОЙКИ</h4><div class="gbody" data-gkey="settings" style="display:none"><h4 style="color:#4C8FD6">Модели и роли</h4>';
MK.forEach(function(k){var it=find(k);if(!it)return;
h+='<div class="tool"><small>'+esc(it.name)+'</small><select data-cfg="'+att(k)+'" style="width:100%">';
if(k!='llm_model')h+='<option value=""'+(String(it.value)==''?' selected':'')+'>— как чат —</option>';
MODELS.forEach(function(m){h+='<option value="'+att(m)+'"'+(m==String(it.value)?' selected':'')+'>'+esc(m)+'</option>'});
if(MODELS.indexOf(String(it.value))<0&&String(it.value)!='')h+='<option selected>'+esc(String(it.value))+'</option>';
h+='</select></div>';});
h+='<h4 style="color:#4C8FD6">Параметры</h4>';
s.items.forEach(function(it){if(MK.indexOf(it.key)>=0||skip(it))return;
(window.CFG=window.CFG||{})[it.key]=it.value;h+='<div class="tool"><small>'+esc(it.space)+' · '+esc(it.name)+'</small>';
if(it.kind=='range'){h+=`<div class="row"><input type="range" data-cfg="${att(it.key)}" min="${it.min}" max="${it.max}" step="${it.step}" value="${it.value}"><b data-v="${att(it.key)}"> ${it.value}</b></div>`;}
else if(it.kind=='check'){h+=`<input type="checkbox" data-cfg="${att(it.key)}" ${it.value?'checked':''}>`;}
else{h+=`<input data-cfg="${att(it.key)}" value="${att(String(it.value))}" style="width:100%">`;}
h+='</div>';});
h+='</div></div>';panel.querySelectorAll('.grp').forEach(g=>{if(g.textContent.includes('НАСТРОЙКИ'))g.remove()});panel.innerHTML+=h}
/* ==== ВАРИАНТ 2 (выбран 24.09.2026): рабочая зона «Программы»/«Базы» + ход работ ==== */
function rlNeed(){return '<div class="grp" style="border-color:#E8912D"><h4 style="color:#E8912D">⚠ нужен перезапуск агента</h4><small style="color:#A6A8AB">Маршруты /api/programs, /api/bases, /api/jobs появятся после AI_RESTART.bat. Пока вариант можно смотреть во временном предпросмотре: http://127.0.0.1:8799/</small></div>'}
function rlProgCard(p){var kk=(p.klass=='Ж')?'#E8912D':(p.klass=='Г'?'#8AA8E8':'#86BC43');
var run=p.run?'<button data-act="prun" data-val="'+att(p.id)+'" style="padding:4px 9px">Запустить</button>':'<small style="color:#A6A8AB">запуск — своим окном</small>';
return '<div class="grp" style="margin:8px 0"><h4><span style="color:'+(p.pid?'#86BC43':'#8A8C90')+'">●</span> '+esc(p.title)+' <small style="color:'+kk+'">класс '+esc(p.klass)+'</small></h4>'
+'<small style="color:#A6A8AB">движок: '+esc(p.engine)+'</small><br><small style="color:#A6A8AB">'+(p.window?('окно: '+esc(p.cwd)+' / '+esc(p.window)):'окна нет — зовёт агент')+'</small><br>'
+'<small style="color:#A6A8AB">'+esc(p.status)+'</small><div class="row" style="margin-top:6px">'+run
+'<button class="sec" data-act="pstate" data-val="'+att(p.id)+'" style="padding:4px 9px">Журнал</button></div>'
+'<div class="log" id="pst_'+att(p.id)+'" style="display:none"></div></div>'}
function rlJobs(){var els=document.querySelectorAll('.jobsline');if(!els.length)return;
J('/api/jobs').then(function(d){els.forEach(function(e){e.textContent=((d||{}).lines)||'журнал пуст'})})
.catch(function(){els.forEach(function(e){e.textContent='нужен перезапуск агента (AI_RESTART.bat)'})})}
function showZone(v){var z=document.getElementById('zone');if(!z)return;
if(v=='chat'){z.style.display='none';chat.style.display='block';return}
chat.style.display='none';z.style.display='block';
if(v=='prog'){z.innerHTML='<div class="grp">⏳ читаю список программ дома…</div>';
J('/api/programs').then(function(d){if(!d||!d.programs){z.innerHTML=rlNeed();return}
var h='<div class="grp"><h4>🧰 ПРОГРАММЫ ДОМА <small style="color:#A6A8AB">список от '+esc(d.updated||'')+'</small></h4>'
+'<small style="color:#A6A8AB">Отдельные программы — для человека (своё окно). Программы Creo — живая сессия (JLINK). '
+'Программы для ИИ — движки, их зовёт агент. Устаревшее — в _legacy, запуск оттуда запрещён.</small></div>';
(d.groups||[]).forEach(function(g){var ps=(d.programs||[]).filter(function(p){return p.group==g.id});if(!ps.length)return;
h+='<div class="grp"><h4>'+(g.icon||'')+' '+esc(g.title)+' <small style="color:#A6A8AB">('+ps.length+')</small></h4>'
+'<small style="color:#A6A8AB">'+esc(g.note||'')+'</small>'+ps.map(rlProgCard).join('')+'</div>'});
z.innerHTML=h}).catch(function(){z.innerHTML=rlNeed()})}
else if(v=='base'){z.innerHTML='<div class="grp">⏳ читаю базы дома…</div>';
J('/api/bases').then(function(d){if(!d||!d.bases){z.innerHTML=rlNeed();return}
var h='<div class="grp"><h4>🗄 БАЗЫ ДОМА</h4><small style="color:#A6A8AB">Свои базы можно обновлять кнопкой; чужие — только чтение.</small></div>'
+'<div class="grp"><table class="reg-t"><tr><td><b>База</b></td><td>Размер</td><td>Таблиц</td><td>Обновлена</td><td>Статус</td><td></td></tr>';
(d.bases||[]).forEach(function(b){var own=/своя/.test(b.kind);
h+='<tr><td><b>'+esc(b.name)+'</b><br><small style="color:#A6A8AB">'+esc(b.path)+'</small><br><small style="color:#A6A8AB">'+esc(b.what)+'</small></td>'
+'<td>'+b.mb+' МБ</td><td>'+esc(b.tables)+'</td><td>'+esc(b.mtime)+'</td><td>'+esc(b.kind)+'</td>'
+'<td>'+(own?'<button data-act="bupd" style="padding:4px 9px">Обновить</button>':'')+'</td></tr>'});
h+='</table></div><div class="grp"><h4 style="color:#4C8FD6">📈 ХОД РАБОТ ДОМА</h4>'
+'<div class="log jobsline" style="max-height:240px;overflow:auto">…</div>'
+'<button class="sec" data-act="jobsload" style="padding:4px 9px;margin-top:6px">Обновить</button></div>';
z.innerHTML=h;rlJobs()}).catch(function(){z.innerHTML=rlNeed()})}}
setInterval(rlJobs,60000); // ход работ дома: тихое обновление, если блок открыт

/* ==== ВИД ОКНА: v1 вкладки сверху · v2 боковое меню · v3 пульт (личная настройка ui_layout) ==== */
function applyLayout(v,save){if(v!='v1'&&v!='v2'&&v!='v3')v='v2';LAY=v;document.body.className='lay-'+v;localStorage.setItem('lay',v);
document.querySelectorAll('.lay').forEach(function(x){x.classList.toggle('on',x.getAttribute('data-val')==v)});
if(save)J('/setcfg',{token:TK,key:'ui_layout',value:v});
var z=document.getElementById('zone');
if(v=='v3'){zonePult()}
else if(z&&z.classList.contains('pult')){z.classList.remove('pult');z.style.display='none';chat.style.display='block'}}
function fillPstate(){var el=document.getElementById('pstate');var s=window.ST;if(!el||!s)return;
el.innerHTML='хост: '+esc(s.host||'')+'\nмодель: '+esc(s.model||'')+'\nпользователь: '+esc((s.user&&(s.user.display_name||s.user.login))||'нет входа')
+'\nрежим: '+(s.mode==2?'собеседник':'инженер')+'\nOllama: '+(s.up_ollama?'жива':'молчит')+' · CREOSON: '+(s.up_creoson?'жив':'молчит')
+'\nблоков: '+s.blocks+' · инструментов: '+s.tools}
function zonePult(){var z=document.getElementById('zone');if(!z)return;chat.style.display='block';
z.classList.add('pult');z.style.display='grid';
z.innerHTML='<div class="grp" id="zp1">⏳ программы…</div><div class="grp" id="zp2">⏳ базы…</div>'
+'<div class="grp pultwide"><h4 style="color:#4C8FD6">📈 ХОД РАБОТ ДОМА</h4><div class="log jobsline" style="max-height:150px;overflow:auto">…</div>'
+'<button class="sec" data-act="jobsload" style="padding:4px 9px;margin-top:6px">Обновить</button></div>';
J('/api/programs').then(function(d){var e=document.getElementById('zp1');if(!e)return;
if(!d||!d.programs){e.innerHTML=rlNeed();return}
var h='<h4>🧰 ПРОГРАММЫ ДОМА</h4>';
(d.groups||[]).forEach(function(g){var ps=(d.programs||[]).filter(function(p){return p.group==g.id});if(!ps.length)return;
h+='<div class="grp" style="margin:6px 0"><h4>'+(g.icon||'')+' '+esc(g.title)+' <small style="color:#A6A8AB">('+ps.length+')</small></h4>'+ps.map(rlProgCard).join('')+'</div>'});
e.innerHTML=h}).catch(function(){var e=document.getElementById('zp1');if(e)e.innerHTML=rlNeed()});
J('/api/bases').then(function(d){var e=document.getElementById('zp2');if(!e)return;
if(!d||!d.bases){e.innerHTML=rlNeed();return}
var h='<h4>🗄 БАЗЫ ДОМА</h4><table class="reg-t"><tr><td><b>База</b></td><td>Мб</td><td>Табл.</td><td>Обновлена</td><td></td></tr>';
(d.bases||[]).forEach(function(b){var own=/своя/.test(b.kind);
h+='<tr><td><b>'+esc(b.name)+'</b><br><small style="color:#A6A8AB">'+esc(b.kind)+'</small></td><td>'+b.mb+'</td><td>'+esc(b.tables)
+'</td><td>'+esc(b.mtime)+'</td><td>'+(own?'<button data-act="bupd" style="padding:3px 8px">Обновить</button>':'')+'</td></tr>'});
e.innerHTML=h+'</table>'}).catch(function(){var e=document.getElementById('zp2');if(e)e.innerHTML=rlNeed()});
rlJobs()}
applyLayout(LAY); // вид применяем сразу, ещё до ответа агента (без мигания)
function loadReg(){J('/pdfregistry').catch(function(){return{}}).then(function(rr){if(!rr||!rr.rows||!rr.rows.length)return;REG=rr.rows;
var h='<div class="grp" data-gkey="reg"><h4 data-act="fold">▸  PDF-РЕЕСТР ('+rr.rows.length+')</h4><div class="gbody" style="display:none">';
h+='<small id="reghdr" style="color:#A6A8AB"></small><div class="row"><label><input type="checkbox" id="regstale"> только устаревшие</label><button id="regall" class="sec" style="padding:4px 8px">Обновить все устаревшие</button></div>';
h+='<div id="regtbl" style="max-height:300px;overflow:auto"></div></div></div>';
panel.innerHTML+=h;renderReg();
document.getElementById('regstale').addEventListener('change',renderReg);
document.getElementById('regall').addEventListener('click',function(){var st=REG.filter(function(r){return r.verdict=='УСТАРЕЛ'});
if(!st.length){alert('устаревших нет');return}
if(!confirm(`План обновления:
${st.map(r=>r.name).join(String.fromCharCode(10))} // 10 = newline
Каждое обновление попросит согласование отдельно.`))return;
(function nx(i){if(i>=st.length)return;qinp.value='pdf_refresh name='+st[i].name;send();setTimeout(function(){nx(i+1)},2000)})(0)})})}
function renderReg(){var box=document.getElementById('regtbl');if(!box)return;var st=document.getElementById('regstale').checked;
var rows=REG.filter(function(r){return !st||r.verdict=='УСТАРЕЛ'});
var hd=document.getElementById('reghdr');if(hd)hd.textContent='показано '+rows.length+' из '+REG.length;
var h='<table class="reg-t">';rows.forEach(function(r){var col=r.verdict=='УСТАРЕЛ'?'op-warn':r.verdict=='актуален'?'op-ok':'op-info';
var dir=String(r.dir||'').split(String.fromCharCode(92)).slice(-2).join(String.fromCharCode(92)); // 92 = backslash
h+='<tr><td>'+esc(r.name)+'</td><td style="color:#A6A8AB">'+esc(dir)+'</td><td class="'+col+'">'+esc(r.verdict)+'</td></tr>'});
box.innerHTML=h+'</table>'}
function setSt(id,on){if(on===undefined)return;var e=document.getElementById('st_'+id);if(e)e.className='stc'+(on?' ok':' bad')}
function init(){J('/status').then(function(s){CURM=s.model;hdr.textContent=s.host+(s.user?' | '+(s.user.display_name||s.user.login):'')+' | '+s.model+' | блоков: '+s.blocks+' · инструментов: '+(s.tools||0);setSt('oll',s.up_ollama);setSt('creo',s.up_creoson);setSt('ag',s.up_agent);window.ST=s;if(s.ui_layout&&s.ui_layout!=LAY)applyLayout(s.ui_layout);var mb=document.querySelector('[data-act="mode"]');if(mb){mb.textContent=(s.mode==2?'💬 Собеседник':'🛠 Инженер');}qinp.placeholder='Задача для АГЕНТА... (Enter) | Ctrl+V — вставить скриншот | chat <вопрос> — разовый режим собеседника';J('/panel').then(function(p){buildPanel(p);fillPstate();J('/settings').then(buildSettings)})}).then(function(){initModal();})}
function initModal(){var modal=document.createElement('div');modal.id='pdf-modal';modal.style.cssText='display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:9999;justify-content:center;align-items:center;flex-direction:column;cursor:zoom-in';modal.innerHTML='<div style="position:relative"><span id="pdf-modal-close" style="position:absolute;top:-30px;right:0;color:white;font-size:24px;cursor:pointer">✖</span><img src="" style="max-width:90%;max-height:80%;border:2px solid #555;cursor:zoom-in" data-act="pdf-enlarge"></div><div style="color:white;margin-top:10px;font-size:12px">клик для увеличения/открытия, Esc для закрытия</div>';document.body.appendChild(modal);modal.addEventListener('click',function(e){if(e.target===modal||e.target.id==='pdf-modal-close')modal.style.display='none'});modal.querySelector('img').addEventListener('click',function(e){e.stopPropagation();var nm=this.getAttribute('data-nm');window.open('/'+nm,'_blank')});document.addEventListener('keydown',function(e){if(e.key==='Escape'&&modal.style.display==='flex')modal.style.display='none'});}
document.addEventListener('click',function(e){var el=e.target.closest('[data-act]');if(!el)return;var a=el.getAttribute('data-act');
if(a=='think'){var n=el.nextElementSibling;n.style.display=n.style.display=='none'?'block':'none'}
else if(a=='fold'){var b=el.nextElementSibling;var hid=b.style.display=='none';b.style.display=hid?'block':'none';el.textContent=(hid?'▾':'▸')+el.textContent.replace(/[▾▸]/,'');var fk=el.getAttribute('data-fkey');if(fk){var F=JSON.parse(localStorage.getItem('panel_fold')||'{}');F[fk]=hid?1:0;localStorage.setItem('panel_fold',JSON.stringify(F))}}
else if(a=='send')send();
else if(a=='wizard'){document.getElementById('wiz').style.display='flex'}
else if(a=='open_purge'){document.getElementById('wiz_purge').style.display='flex'}
else if(a=='w_close'){document.getElementById('wiz').style.display='none'}
else if(a=='w_prev'){var o=document.getElementById('w_old').value,n=document.getElementById('w_new').value;if(!o||!n){alert('заполни old и new');return}var out=document.getElementById('w_out');out.innerHTML='<small style="color:#A6A8AB">считаю план…</small>';J('/wiz_preview',{token:TK,old:o,new:n,template:document.getElementById('w_tpl').value,family:document.getElementById('w_family').checked?1:0,drawings:document.getElementById('w_draw').checked?1:0}).then(function(r){if(r.error){out.innerHTML='<span style="color:#C64E4E">'+esc(r.error)+'</span>';return}var h='<table style="width:100%;font-size:12px;border-collapse:collapse">';(r.rows||[]).forEach(function(w){h+='<tr><td style="padding:2px 4px;color:#A6A8AB">'+esc(w.old)+'</td><td style="padding:2px 4px">→ '+esc(w.new)+'</td></tr>'});h+='</table><small style="color:#A6A8AB">будет переименовано: '+(r.total||0)+'</small>';out.innerHTML=h}).catch(function(e){out.innerHTML='<span style="color:#C64E4E">ошибка: '+esc(e)+'</span>'})}
else if(a=='w_copy'){var o=document.getElementById('w_old').value,n=document.getElementById('w_new').value;if(!o||!n){alert('заполни old и new');return}var tp=document.getElementById('w_tpl').value.replace(new RegExp('[^A-Za-z0-9_{}\\-]','g'),'');document.getElementById('wiz').style.display='none';qinp.value='copy_model old='+o+' new='+n+(tp?' template='+tp:'')+' family='+(document.getElementById('w_family').checked?1:0)+' drawings='+(document.getElementById('w_draw').checked?1:0)+' dry_run='+(document.getElementById('w_dry').checked?1:0);send()}
else if(a=='w_rprev'){var o=document.getElementById('w_old').value,n=document.getElementById('w_rnew').value;if(!o||!n){alert('заполни «старое имя (old)» и «новое имя модели»');return}var out=document.getElementById('w_out');out.innerHTML='<small style="color:#A6A8AB">считаю план…</small>';J('/wiz_rename_preview',{token:TK,old:o,new:n,drawings:document.getElementById('w_rdraw').checked?1:0}).then(function(r){if(r.error){out.innerHTML='<span style="color:#C64E4E">'+esc(r.error)+'</span>';return}var h='<table style="width:100%;font-size:12px;border-collapse:collapse">';(r.rows||[]).forEach(function(w){h+='<tr><td style="padding:2px 4px;color:#A6A8AB">'+esc(w.old)+'</td><td style="padding:2px 4px">→ '+esc(w.new)+'</td><td style="padding:2px 4px;color:#8A8C90">'+esc(w.kind||'')+'</td></tr>'});h+='</table><small style="color:#A6A8AB">папка: '+esc(r.wd||'')+'<br>сборки-владельцы: '+esc((r.parents||[]).join(', ')||'в базе usage не найдены')+'</small>';out.innerHTML=h}).catch(function(e){out.innerHTML='<span style="color:#C64E4E">ошибка: '+esc(e)+'</span>'})}
else if(a=='w_rename'){var o=document.getElementById('w_old').value,n=document.getElementById('w_rnew').value;if(!o||!n){alert('заполни «старое имя (old)» и «новое имя модели»');return}document.getElementById('wiz').style.display='none';qinp.value='rename_model old_name='+o+' new_name='+n+' drawings='+(document.getElementById('w_rdraw').checked?1:0)+' parents='+(document.getElementById('w_rpar').checked?1:0)+' dry_run='+(document.getElementById('w_dry').checked?1:0);send()}
else if(a=='w_audit'){document.getElementById('wiz').style.display='none';qinp.value='creo_audit_folder';send()}
else if(a=='w_usage'){document.getElementById('wiz').style.display='none';qinp.value='usage_build full=1';send()}
else if(a=='w_night'){document.getElementById('wiz').style.display='none';qinp.value='nightly_run';send()}
else if(a=='snap')J('/snap',{token:TK}).then(function(r){addMsg(esc(r.msg||'ок'))});
else if(a=='showlog'){fetch('/log',{headers:{'X-Token':TK||''}}).then(r=>r.text()).then(t=>addMsg('<div class="log">'+esc(t)+'</div>'))}
else if(a=='panel')panel.style.display=panel.style.display=='none'?'block':'none';
/* ==== ВАРИАНТ 2: рейл (рабочие зоны), запуск движков, ход работ ==== */
else if(a=='rl'){var vz=el.getAttribute('data-val');document.querySelectorAll('#rail .item,#tabs .item').forEach(function(x){if(x.getAttribute('data-act')=='rl')x.classList.toggle('on',x.getAttribute('data-val')==vz)});var zp=document.getElementById('zone');if(zp&&zp.classList.contains('pult')){zp.classList.remove('pult');zp.style.display='none'}showZone(vz)}
else if(a=='lay'){applyLayout(el.getAttribute('data-val'),true)}
else if(a=='jobsload'){rlJobs()}
else if(a=='prun'){el.disabled=true;J('/prog_run',{token:TK,prog_id:el.getAttribute('data-val')}).then(function(r){el.disabled=false;var host=el.parentElement;host.insertAdjacentHTML('beforeend','<small style="color:#A6A8AB"> '+esc(((r||{}).text)||'?')+'</small>')}).catch(function(e){el.disabled=false;alert('ошибка: '+e)})}
else if(a=='pstate'){var pid2=el.getAttribute('data-val');J('/prog_state',{token:TK,prog_id:pid2,tail:14}).then(function(r){var e2=document.getElementById('pst_'+pid2);if(e2){e2.style.display='block';e2.textContent=((r||{}).text)||'?'}}).catch(function(){var e2=document.getElementById('pst_'+pid2);if(e2){e2.style.display='block';e2.textContent='нужен перезапуск агента (AI_RESTART.bat)'}})}
else if(a=='bupd'){if(!confirm('Обновить индекс дома (harvest) в фоне? Обычно ~20 секунд.'))return;J('/prog_run',{token:TK,prog_id:'harvest'}).then(function(r){alert(((r||{}).text)||'?');rlJobs()})}
else if(a=='logout'){localStorage.removeItem('tk');localStorage.removeItem('usr');TK='';showLogin()}
else if(a=='showpro'){J('/profile',{token:TK}).then(function(u){document.getElementById('proinfo').textContent=(u.display_name||'')+' · '+(u.role||'')+' · '+u.login;document.getElementById('pname').value=u.display_name||'';document.getElementById('pro').style.display='flex';document.getElementById('adm_btn').style.display=u.can_manage?'block':'none'})}
else if(a=='closepro'){document.getElementById('pro').style.display='none'}
else if(a=='savename'){var v=document.getElementById('pname').value;J('/setname',{token:TK,name:v}).then(function(r){alert(r.msg||'ок');if(r.ok){document.getElementById('pro').style.display='none';init()}})}
else if(a=='savepw'){J('/setpw',{token:TK,old:document.getElementById('pold').value,'new':document.getElementById('pnew').value}).then(function(r){alert(r.msg||'ок');if(r.ok){document.getElementById('pold').value='';document.getElementById('pnew').value=''}})}
else if(a=='openadm'){document.getElementById('pro').style.display='none';document.getElementById('adm').style.display='flex';J('/admin/users',{token:TK,op:'list'}).then(function(r){var out='';(r.users||[]).forEach(function(u){out+='<div style="padding:6px;background:#2C2D30;border-radius:6px;margin:3px 0;display:flex;gap:6px;align-items:center"><b>'+esc(u.display_name)+'</b> <small style="color:#A6A8AB">('+esc(u.login)+')</small> ';out+='<select class="rsel" data-login="'+att(u.login)+'">';(r.roles||[]).forEach(function(role){out+='<option'+(role===u.role?' selected':'')+'>'+esc(role)+'</option>'});out+='</select> ';out+='<button data-act="do_role" data-login="'+att(u.login)+'" style="padding:4px 8px">роль</button> ';out+='<button data-act="do_resetpw" data-login="'+att(u.login)+'" style="padding:4px 8px;background:#6f4a2b">сброс pw</button> <button data-act="do_del" data-login="'+att(u.login)+'" style="padding:4px 8px;background:#6f2b2b">удалить</button></div>'});document.getElementById('ulist').innerHTML=out||'(пусто)';var sel=document.getElementById('nrole');if(sel)sel.innerHTML=(r.roles||[]).map(function(x){return '<option>'+esc(x)+'</option>'}).join('')})}
else if(a=='closeadm'){document.getElementById('adm').style.display='none'}
else if(a=='do_role'){var lgn=el.getAttribute('data-login');var sel=document.querySelector('.rsel[data-login="'+lgn+'"]');J('/admin/users',{token:TK,op:'role',login:lgn,role:sel.value}).then(function(r){alert(r.msg||'ок')})}
else if(a=='do_del'){var lgn=el.getAttribute('data-login');if(!confirm('Удалить пользователя '+lgn+'?'))return;J('/admin/users',{token:TK,op:'delete',login:lgn}).then(function(r){alert(r.msg||'ок');if(r.ok){document.getElementById('adm').style.display='none';setTimeout(function(){document.getElementById('adm').style.display='flex';document.querySelector('[data-act="openadm"]').click()},100)}})}
else if(a=='do_resetpw'){var lgn=el.getAttribute('data-login');var nw=prompt('Новый пароль для '+lgn+' (мин 4):');if(nw)J('/admin/users',{token:TK,op:'resetpw',login:lgn,pw:nw}).then(function(r){alert(r.msg||'ок')})}
else if(a=='adduser'){J('/admin/users',{token:TK,op:'add',login:document.getElementById('nlog').value,pw:document.getElementById('npw').value,role:document.getElementById('nrole').value}).then(function(r){alert(r.msg||'ок');if(r.ok){document.getElementById('nlog').value='';document.getElementById('npw').value='';document.getElementById('adm').style.display='none';setTimeout(function(){document.getElementById('adm').style.display='flex';document.querySelector('[data-act="openadm"]').click()},100)}})}
else if(a=='closelogin'){login.style.display='none'}
else if(a=='login')J('/login',{login:lg.value,pw:pw.value}).catch(function(e){alert('сервер недоступен: '+e);throw e}).then(function(r){if(r.ok){TK=r.token;localStorage.setItem('tk',TK);localStorage.setItem('usr',lg.value);login.style.display='none';init();if(!localStorage.getItem('seen_guide')){localStorage.setItem('seen_guide','1');setTimeout(function(){qinp.value='guide';send()},400)}}else alert('неверный логин или пароль')});
else if(a=='reg')J('/register',{login:lg.value,pw:pw.value}).then(function(r){alert(r.msg||'ок')});
else if(a=="appr"){var sp2=document.getElementById("spin");if(sp2)sp2.style.display="inline-block";J("/approve",{token:TK,pid:el.getAttribute("data-pid"),ok:el.getAttribute("data-ok")=="1"}).then(function(r){if(sp2)sp2.style.display="none";var msgEl=el.closest(".msg");var okf=!/^отменено/.test(r.res||"")&&!/^согласование устарело/.test(r.res||"");if(msgEl){var btns=msgEl.querySelector("button[data-act='appr']");if(btns)btns.parentElement.remove();var lg2=msgEl.querySelector(".log");if(!lg2){lg2=document.createElement('div');lg2.className='log';msgEl.appendChild(lg2)}lg2.textContent+=(lg2.textContent?String.fromCharCode(10):'')+(okf?'✅ выполнено: ':'❌ отмена: ')+(r.res||'')}if(okf&&r.answer&&r.answer!==r.res){var d2=addMsg('');render(d2,r)}});} // 10 = newline
else if(a=='fb'){var okv=el.getAttribute('data-ok')=='1';var cm=okv?'':prompt('Короткий комментарий (почему не попал):','');if(!okv&&cm===null)return;var dd=el.closest('.msg');var rr=dd&&dd._r?dd._r:{};var tool='';if(rr.log&&rr.log.length){var mm=String(rr.log[rr.log.length-1]).match(new RegExp('^([A-Za-z0-9_]+)' + String.fromCharCode(40)));if(mm)tool=mm[1]}J('/feedback',{token:TK,query:dd&&dd._query?dd._query:'',think:rr.think||'',tool:tool,result:rr.answer||'',ok:okv?1:0,comment:cm||''}).then(function(fb){el.parentNode.innerHTML='<span style="color:#A6A8AB">оценка сохранена</span>'})} // 40 = left
else if(a=='mode'){var mb=document.querySelector('[data-act="mode"]');var curText=mb.textContent;var isEng=curText.includes('Инженер');var nextMode=isEng?2:1;var nextText=(isEng?'💬 Собеседник':'🛠 Инженер');J('/setcfg',{method:'POST',headers:{'Content-Type':'application/json','X-Token':TK||''},body:JSON.stringify({key:'chat_mode',value:nextMode})}).then(function(){mb.textContent=nextText;qinp.placeholder='Задача для АГЕНТА... (Enter) | Ctrl+V — вставить скриншот | chat <вопрос> — разовый режим собеседника';});}
else if(a=='setm')J('/setmodel',{token:TK,model:el.getAttribute('data-val')}).then(function(){init()});
else if(a=='act'){var ep=el.getAttribute('data-val');if(ep=='/log'){fetch('/log',{headers:{'X-Token':TK||''}}).then(r=>r.text()).then(t=>addMsg('<div class="log">'+esc(t)+'</div>'))}else J(ep,{token:TK}).then(function(r){addMsg('<div class="log">'+esc(JSON.stringify(r).slice(0,800))+'</div>')})}
else if(a=='chip'){qinp.value=el.getAttribute('data-val');send()}
else if(a=='details-toggle'){var k=el.getAttribute('data-val');J('/ask',{token:TK,q:'guide topic='+k}).then(function(r){var d2=addMsg('');render(d2,r)})}
else if(a=='pdfref'){qinp.value='pdf_refresh name='+el.getAttribute('data-val');send()}
else if(a=='pdfthumb'){var nm=el.getAttribute('data-val');var url='/pdfthumb?name='+encodeURIComponent(nm)+'&page=1&token='+TK;var modal=document.getElementById('pdf-modal');modal.querySelector('img').src=url;modal.style.display='flex';}

else if(a=='childname'){var row=el.closest('.msg').querySelector('.pdfrow');if(row)addPdfBlock(row,el.getAttribute('data-val'))}
else if(a=='lbx'){var lb=document.getElementById('lbx');lb.style.display='flex';lb.querySelector('img').src=el.getAttribute('src')}
else if(a=='showchat'){var cb=document.getElementById('chatbox');if(cb.style.display=='flex'){cb.style.display='none';if(CTMR){clearInterval(CTMR);CTMR=null}}else{cb.style.display='flex';CLAST=0;document.getElementById('cmsg').innerHTML='';chatPoll();if(CTMR)clearInterval(CTMR);CTMR=setInterval(chatPoll,5000);NEWMSG=0;chatBadge()}}
else if(a=='closechat'){document.getElementById('chatbox').style.display='none';if(CTMR){clearInterval(CTMR);CTMR=null}}
else if(a=='close_purge'){document.getElementById('wiz_purge').style.display='none'}
else if(a=='wiz_purge_preview'){var r=document.getElementById('wp_root').value,k=document.getElementById('wp_keep').value,o=document.getElementById('wp_out');if(!r){alert('укажи путь');return}var isNet=!/^[DE]:/i.test(r);if(isNet){if(!confirm("сетевой корень: скан медленный, перенос тронет сетевой диск"))return}o.innerHTML='<small style="color:#A6A8AB">'+(isNet?'считаю план… (сетевой корень может сканироваться минутами)':'считаю план…')+'</small>';J('/wiz_purge_preview',{token:TK,root:r,keep:k}).then(function(g){if(g.error){o.innerHTML='<span style="color:#C64E4E">'+esc(g.error)+'</span>';return}var table='<table style="width:100%;font-size:12px;border-collapse:collapse;margin-top:5px;"><tr style="color:#A6A8AB;text-align:left;"><th style="padding:2px 4px;">Старое</th><th style="padding:2px 4px;">Новое</th><th style="padding:2px 4px;">Версий</th></tr>';g.rows.forEach(function(row){table+='<tr><td style="padding:2px 4px;">'+esc(row.old)+'</td><td style="padding:2px 4px;">'+esc(row.new)+'</td><td style="padding:2px 4px;">'+row.versions+'</td></tr>'});table+='</table><p style="font-size:12px;margin-top:5px;">будет перенесено '+g.total+' файлов в backup</p>';o.innerHTML=table;}).catch(function(e){o.innerHTML='<span style="color:#C64E4E">ошибка: '+esc(e)+'</span>'})}
else if(a=='chatsend'){var t=document.getElementById('cin').value;J('/chat/send',{token:TK,text:t}).then(function(r){if(r.ok)document.getElementById('cin').value='';chatPoll()})}});
