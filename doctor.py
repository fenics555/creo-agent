# -*- coding: utf-8 -*-
import json
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")

# 1) config: убрать «ремонт» из исключений
cp = AG / "data" / "config.json"
d = json.loads(cp.read_text(encoding="utf-8")) if cp.exists() else {}
se = d.get("scan_exclude") or []
se2 = [x for x in se if x.strip().lower() != "ремонт"]
if len(se2) != len(se):
    d["scan_exclude"] = se2
    cp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print("[+] config: 'ремонт' убран из scan_exclude")
else:
    print("[~] config: 'ремонт' не найден")

# 2) usage_tools: уступать GIL, чтобы веб не висел при сборке
up = AG / "usage_tools.py"
s = up.read_text(encoding="utf-8")
old = '            STATE["done"] += 1'
new = '            STATE["done"] += 1\n            if STATE["done"] % 20 == 0: time.sleep(0.001)'
if "time.sleep(0.001)" not in s and old in s:
    up.write_text(s.replace(old, new, 1), encoding="utf-8")
    print("[+] usage_tools: GIL-уступка при построении")
else:
    print("[~] usage_tools: уже/якорь не найден")

# 3) agent.py: спиннер с таймаутом, не крутится на poll
ap = AG / "agent.py"
a = ap.read_text(encoding="utf-8")
oldw = "(function(){var sp=document.getElementById('spin');if(!sp)return;var of=window.fetch;window.fetch=function(){sp.style.display='inline-block';return of.apply(this,arguments).finally(function(){sp.style.display='none';});};})();"
neww = "(function(){var sp=document.getElementById('spin');if(!sp)return;var of=window.fetch;window.fetch=function(u){var url=String(u);var bg=url.indexOf('/chat/poll')>=0||url.indexOf('/status')>=0;if(!bg)sp.style.display='inline-block';var p=of.apply(this,arguments);var t=new Promise(function(r,j){setTimeout(function(){j(new Error('таймаут 25с: '+url))},25000)});return Promise.race([p,t]).finally(function(){if(!bg)sp.style.display='none';});};})();"
if oldw in a:
    a = a.replace(oldw, neww, 1); print("[+] agent: спиннер с таймаутом")
elif "таймаут 25с" not in a:
    i = a.rfind("</script>")
    a = a[:i] + neww + a[i:]; print("[+] agent: обёртка вставлена")
oldi = "if(TK)init();else showLogin();"
newi = "if(TK){Promise.resolve().then(init).catch(function(e){addMsg('ошибка инициализации: '+e,true)})}else showLogin();"
if oldi in a:
    a = a.replace(oldi, newi, 1); print("[+] agent: init с обработкой ошибки")
ap.write_text(a, encoding="utf-8")
print("ГОТОВО: .\\AI_RESTART.bat, затем в чате: scan_run (перескан без 'ремонт')")