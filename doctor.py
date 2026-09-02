# -*- coding: utf-8 -*-
import re
from pathlib import Path
ap = Path(r"D:\AI\tools\agent\agent.py")
s = ap.read_text(encoding="utf-8")

NEW = """(function(){if(window.__slfix)return;window.__slfix=1;
var busy=false;
function sync(r){var lab=r.parentNode.querySelector('[data-v]')||r.nextElementSibling;if(lab&&String(lab.textContent)!==String(r.value))lab.textContent=r.value;}
document.addEventListener('input',function(e){var r=e.target;if(r&&r.type=='range'&&r.getAttribute('data-cfg'))sync(r);});
document.addEventListener('change',function(e){var r=e.target;if(r&&r.type=='range'&&r.getAttribute('data-cfg')){fetch('/setcfg',{method:'POST',headers:{'Content-Type':'application/json','X-Token':window.TK||''},body:JSON.stringify({key:r.getAttribute('data-cfg'),value:r.value})});}});
var mo=new MutationObserver(function(){if(busy)return;busy=true;try{document.querySelectorAll('input[type=range][data-cfg]').forEach(function(r){var want=parseFloat(r.getAttribute('data-val')||r.value);if(!isNaN(want)){if(parseFloat(r.max)<want)r.max=want;if(String(r.value)!==String(want))r.value=want;sync(r);}});}finally{busy=false;}});
mo.observe(document.body,{childList:true,subtree:true});
window.addEventListener('unhandledrejection',function(){var sp=document.getElementById('spin');if(sp)sp.style.display='none';});})();"""

n = re.sub(r"\(function\(\)\{if\(window\.__slfix\)return;.*?mo\.observe\(document\.body,\{childList:true,subtree:true\}\);\}\)\(\);",
           NEW, s, count=1, flags=re.S)
if n != s:
    ap.write_text(n, encoding="utf-8")
    print("[+] agent: __slfix вылечен (guard + сравнение перед записью)")
else:
    print("[x] не нашёл блок __slfix — покажи хвост PAGE")
print("ГОТОВО: .\\AI_RESTART.bat, затем в браузере Ctrl+F5")