# -*- coding: utf-8 -*-
import re
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")

ap = AG / "agent.py"; a = ap.read_text(encoding="utf-8"); ch = False
if "def _log(line): _log(line);" in a:
    a = a.replace("def _log(line): _log(line); LIVE.setdefault(client, []).append(line)",
                  "def _log(line): steps_log.append(line); LIVE.setdefault(client, []).append(line)", 1)
    ch = True; print("[+] рекурсия _log убрана")
if "'/ask')>=0" not in a:
    a2, n = re.subn(r"var bg=url\.indexOf\('/chat/poll'\)\s*>=0\|\|url\.indexOf\('/status'\)\s*>=0;",
                    lambda m: m.group(0) + "||url.indexOf('/ask')>=0;", a, count=1)
    if n: a = a2; ch = True; print("[+] 25с не убивает /ask и /ask_stream")
old_ch = "document.addEventListener('change',function(e){var r=e.target;if(r&&r.type=='range'&&r.getAttribute('data-cfg')){fetch('/setcfg',{method:'POST',headers:{'Content-Type':'application/json','X-Token':window.TK||''},body:JSON.stringify({key:r.getAttribute('data-cfg'), value:r.value})});}});"
new_ch = "document.addEventListener('change',function(e){var r=e.target;var k=r.getAttribute&&r.getAttribute('data-cfg');if(!k)return;if(r.type!='range'&&r.type!='checkbox')return;var v=(r.type=='checkbox')?(r.checked?1:0):r.value;fetch('/setcfg',{method:'POST',headers:{'Content-Type':'application/json','X-Token':window.TK||''},body:JSON.stringify({key:k,value:v})});});"
if old_ch in a: a = a.replace(old_ch, new_ch, 1); ch = True; print("[+] чекбоксы сохраняются")
else: print("[~] change-обработчик не найден — проверь вручную")
if "cwd=str(core.BASE)" in a:
    a = a.replace("cwd=str(core.BASE)", 'cwd=r"D:\\AI\\tools\\agent"'); ch = True; print("[+] cwd = папка агента")
if ch: ap.write_text(a, encoding="utf-8")

up = AG / "usage_tools.py"; u = up.read_text(encoding="utf-8")
if "core.read_roots()" in u:
    u = u.replace("core.read_roots()", "(__import__('scanner').read_roots())", 1)
    up.write_text(u, encoding="utf-8"); print("[+] usage: корни из kb_roots.txt")

sp = AG / "settings.py"; s = sp.read_text(encoding="utf-8")
s2 = re.sub(r',\s*"auto_mode"\s*\]', ']', s)
if s2 != s: sp.write_text(s2, encoding="utf-8"); print("[+] auto_mode глобальный")

# самопроверка: печатаем дисковую правду
a2 = (AG / "agent.py").read_text(encoding="utf-8")
m = re.search(r"def _log\(line\):.*", a2)
print("CHECK _log:", m.group(0).strip() if m else "-")
print("CHECK bg:", [l.strip() for l in a2.splitlines() if "var bg=" in l])
print("CHECK cwd:", [l.strip() for l in a2.splitlines() if "cwd=" in l])
print("CHECK checkbox:", "r.type=='checkbox'" in a2)
u2 = (AG / "usage_tools.py").read_text(encoding="utf-8")
print("CHECK roots:", [l.strip() for l in u2.splitlines() if "read_roots" in l][:2])
print("ГОТОВО: .\\AI_RESTART.bat")