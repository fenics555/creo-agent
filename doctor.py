# -*- coding: utf-8 -*-
import io
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")

# 1) role_tools.py: TOOLS += без определения -> TOOLS =
rt = AG / "role_tools.py"
if rt.exists():
    s = rt.read_text(encoding="utf-8")
    if "TOOLS += [" in s and "TOOLS = [" not in s:
        rt.write_text(s.replace("TOOLS += [", "TOOLS = [", 1), encoding="utf-8")
        print("[+] role_tools: TOOLS =")
    else:
        print("[~] role_tools: уже ок")
else:
    print("[~] role_tools.py нет")

ap = AG / "agent.py"
a = ap.read_text(encoding="utf-8")
ch = False

# 2) buildPanel защитный: не падать на битом ответе
if "function buildPanel(p){var h=" in a and "p=p||{actions" not in a:
    a = a.replace("function buildPanel(p){var h=",
                  "function buildPanel(p){p=p||{actions:[],models:[],chips:[],groups:[]};var h=", 1); ch = True
for old, new in [("p.actions.forEach", "(p.actions||[]).forEach"),
                 ("p.models.forEach", "(p.models||[]).forEach"),
                 ("p.chips.forEach", "(p.chips||[]).forEach"),
                 ("p.groups.forEach", "(p.groups||[]).forEach")]:
    if old in a: a = a.replace(old, new); ch = True

# 3) /panel не 500, а всегда валидный JSON
old_p = """elif p == "/panel":
    d = panel.build()"""
new_p = """elif p == "/panel":
    try:
        d = panel.build()
    except Exception as e:
        d = {"actions": [], "models": [], "chips": [], "groups": [], "error": str(e)}"""
if old_p in a: a = a.replace(old_p, new_p, 1); ch = True

# 4) /settings не роняет страницу
old_s = """elif p == "/settings":
    self._j({"items": settings.list_ui()})"""
new_s = """elif p == "/settings":
    try:
        self._j({"items": settings.list_ui()})
    except Exception:
        self._j({"items": []})"""
if old_s in a: a = a.replace(old_s, new_s, 1); ch = True

if ch:
    ap.write_text(a, encoding="utf-8")
    print("[+] agent: панель/настройки небьющиеся")
else:
    print("[~] agent: правки уже стоят")
print("ГОТОВО: .\\AI_RESTART.bat, затем в браузере Ctrl+F5")