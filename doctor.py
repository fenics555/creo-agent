# -*- coding: utf-8 -*-
import io
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")

# 1) settings.py: структурированный список для панели
sp = AG / "settings.py"
s = sp.read_text(encoding="utf-8")
if "def list_ui" not in s:
    s += '''

def list_ui():
    d = _raw()
    B = {"creativity": (0, 100, 1), "auto_temperature": (0, 100, 1), "top_p": (0, 1, 0.05),
         "num_ctx": (1024, 32768, 1024), "num_predict": (256, 8192, 256),
         "log_days": (1, 365, 1), "image_days": (1, 60, 1), "history_days": (1, 365, 1),
         "client_days": (1, 365, 1), "top_chunks": (1, 12, 1), "chunk_chars": (200, 2000, 100),
         "chunk_size": (500, 4000, 250), "chunk_overlap": (0, 1000, 50),
         "repo_boost": (0.5, 3, 0.1), "repo_boost_min_sim": (0, 1, 0.05),
         "vision_gpu": (0, 64, 1), "max_file_mb": (1, 100, 1), "retention": (1, 30, 1),
         "audit_limit": (1, 100, 1), "steps_max": (1, 16, 1),
         "web_quick_links": (0, 100, 1), "web_deep_pages": (0, 200, 5)}
    out = []
    for space, k, name, typ, defl, desc, ui in REGISTRY:
        if not ui: continue
        v = d.get(k, defl)
        e = {"space": space, "key": k, "name": name, "type": typ, "value": v, "desc": desc}
        if typ in ("int", "float") and k in B:
            lo, hi, st = B[k]; e["min"], e["max"], e["step"] = lo, hi, st; e["kind"] = "range"
        elif typ == "bool": e["kind"] = "check"
        else: e["kind"] = "text"
        out.append(e)
    return out
'''
    sp.write_text(s, encoding="utf-8")
    print("[+] settings: list_ui()")
else:
    print("[~] settings: list_ui уже есть")

# 2) agent.py: эндпоинт + ползунки в панели
ap = AG / "agent.py"
a = ap.read_text(encoding="utf-8")
ch = False
if '"/settings"' not in a:
    old = '        elif p == "/fleet/info":'
    new = '        elif p == "/settings":\n            self._j({"items": settings.list_ui()})\n        elif p == "/fleet/info":'
    if old in a: a = a.replace(old, new, 1); ch = True

JS_FN = """function buildSettings(s){var h='<div class="grp"><h4 data-act="fold">▸  НАСТРОЙКИ (ползунки)</h4><div class="gbody">';
s.items.forEach(function(it){h+='<div class="tool"><small>'+esc(it.space)+' · '+esc(it.name)+'</small>';
if(it.kind=='range'){h+='<input type="range" data-cfg="'+att(it.key)+'" min="'+it.min+'" max="'+it.max+'" step="'+it.step+'" value="'+it.value+'" style="width:100%"><b data-v="'+att(it.key)+'"> '+it.value+'</b>';}
else if(it.kind=='check'){h+='<input type="checkbox" data-cfg="'+att(it.key)+'" '+(it.value?'checked':'')+'>';}
else{h+='<input data-cfg="'+att(it.key)+'" value="'+att(String(it.value))+'" style="width:100%;background:#232b36;color:#dfe6ee;border:1px solid #334052;border-radius:6px;padding:4px">';}
h+='</div>';});
h+='</div></div>';panel.innerHTML+=h;}
"""
if "function buildSettings" not in a:
    if "function init(){" in a: a = a.replace("function init(){", JS_FN + "function init(){", 1); ch = True
if "J('/settings').then(buildSettings)" not in a:
    old = "J('/panel').then(buildPanel)})}"
    new = "J('/panel').then(function(p){buildPanel(p);J('/settings').then(buildSettings)})})}"
    if old in a: a = a.replace(old, new, 1); ch = True
if "addEventListener('change'" not in a:
    old = "qinp.addEventListener('keydown',function(e){if(e.key=='Enter')send()});"
    new = old + """
document.addEventListener('change',function(e){var el=e.target.closest('[data-cfg]');if(!el)return;var k=el.getAttribute('data-cfg');var v=el.type=='checkbox'?(el.checked?1:0):el.value;J('/setcfg',{token:TK,key:k,value:v}).then(function(){var b=document.querySelector('[data-v="'+k+'"]');if(b)b.textContent=v;});});
document.addEventListener('input',function(e){var el=e.target.closest('[data-cfg]');if(!el||el.type!='range')return;var b=document.querySelector('[data-v="'+el.getAttribute('data-cfg')+'"]');if(b)b.textContent=el.value;});"""
    if old in a: a = a.replace(old, new, 1); ch = True
if ch:
    ap.write_text(a, encoding="utf-8")
    print("[+] agent: ползунки настроек в боковой панели")
else:
    print("[~] agent: ползунки уже есть")
print("ГОТОВО: .\\AI_RESTART.bat")