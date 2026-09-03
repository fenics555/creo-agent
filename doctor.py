# -*- coding: utf-8 -*-
import re, json
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")

# 1) settings: auto_mode keluar из PERSONAL_KEYS -> пойдёт через set_val + автосброс
sp = AG / "settings.py"; s = sp.read_text(encoding="utf-8")
s2 = re.sub(r',\s*"auto_mode"\s*\]', ']', s)
if s2 != s: sp.write_text(s2, encoding="utf-8"); print("[+] settings: auto_mode -> глобальный (автосброс заработает)")

# 2) config: diag_web на локальный эндпоинт (зелёный вердикт)
cp = AG / "data" / "config.json"; d = json.loads(cp.read_text(encoding="utf-8")) if cp.exists() else {}
if d.get("web_test_url") != "http://127.0.0.1:8765/status":
    d["web_test_url"] = "http://127.0.0.1:8765/status"
    cp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8"); print("[+] config: web_test_url -> локальный /status")

# 3) agent JS: галочки сохраняются + авторежим обновляет панель + имена режимов логов
ap = AG / "agent.py"; a = ap.read_text(encoding="utf-8"); ch = False
old_sync = "function sync(r){var lab=r.parentNode.querySelector('[data-v]')||r.nextElementSibling;if(lab&&String(lab.textContent)!==String(r.value))lab.textContent=r.value;}"
new_sync = "var LMN=['авто','авто+токены','отладка','полный'];function sync(r){var lab=r.parentNode.querySelector('[data-v]')||r.nextElementSibling;if(!lab)return;var k=r.getAttribute('data-cfg');var txt=(k=='log_mode')?(r.value+' · '+LMN[+r.value]):r.value;if(String(lab.textContent)!=txt)lab.textContent=txt;}"
if old_sync in a: a = a.replace(old_sync, new_sync, 1); ch = True
old_ch = "document.addEventListener('change',function(e){var r=e.target;if(r&&r.type=='range'&&r.getAttribute('data-cfg')){fetch('/setcfg',{method:'POST',headers:{'Content-Type':'application/json','X-Token':window.TK||''},body:JSON.stringify({key:r.getAttribute('data-cfg'), value:r.value})});}});"
new_ch = "document.addEventListener('change',function(e){var r=e.target;var k=r.getAttribute&&r.getAttribute('data-cfg');if(!k)return;if(r.type!='range'&&r.type!='checkbox')return;var v=(r.type=='checkbox')?(r.checked?1:0):r.value;fetch('/setcfg',{method:'POST',headers:{'Content-Type':'application/json','X-Token':window.TK||''},body:JSON.stringify({key:k,value:v})}).then(function(){if(k=='auto_mode'){setTimeout(function(){J('/settings').then(function(s){var o=document.getElementById('setgrp');if(o)o.remove();buildSettings(s);});},300);}});});"
if old_ch in a: a = a.replace(old_ch, new_ch, 1); ch = True
old_bs = "function buildSettings(s){var h='<div class=\"grp\"><h4 data-act=\"fold\">▸ НАСТРОЙКИ (ползунки)</h4><div class=\"gbody\" style=\"display:none\">';"
new_bs = "function buildSettings(s){var o=document.getElementById('setgrp');if(o)o.remove();var h='<div class=\"grp\" id=\"setgrp\"><h4 data-act=\"fold\">▸ НАСТРОЙКИ (ползунки)</h4><div class=\"gbody\" style=\"display:block\">';"
if old_bs in a: a = a.replace(old_bs, new_bs, 1); ch = True
old_rg = "if(it.kind=='range'){h+='<input type=\"range\" data-cfg=\"'+att(it.key)+'\" min=\"'+it.min+'\" max=\"'+it.max+'\" step=\"'+it.step+'\" value=\"'+it.value+'\" style=\"width:100%\"><b data-v=\"'+att(it.key)+'\"> '+it.value+'</b>';}"
new_rg = "if(it.kind=='range'){h+='<input type=\"range\" data-cfg=\"'+att(it.key)+'\" min=\"'+it.min+'\" max=\"'+it.max+'\" step=\"'+it.step+'\" value=\"'+it.value+'\" style=\"width:100%\"><b data-v=\"'+att(it.key)+'\"> '+it.value+(it.key=='log_mode'?' · '+(LMN[it.value]||''):'')+'</b>';}"
if old_rg in a: a = a.replace(old_rg, new_rg, 1); ch = True
if ch: ap.write_text(a, encoding="utf-8"); print("[+] agent: галочки+автосброс+имена режимов")
print("ГОТОВО: .\\AI_RESTART.bat")