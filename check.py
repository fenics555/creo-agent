# -*- coding: utf-8 -*-
import io, os, re
os.chdir(r"D:\AI\tools\agent")
a = io.open("agent.py", encoding="utf-8").read()
s = io.open("settings.py", encoding="utf-8").read()
b = io.open("behavior_tools.py", encoding="utf-8").read()
print("=== agent.py ===")
print("ask defs:", a.count("def ask("))
print("_one defs:", a.count("def _one(oa):"))
print("think parse:", a.count("think_text = mt.group"))
print("think_rule:", a.count("think_rule ="))
print("night log:", a.count("night start:"))
print("/feedback:", a.count('p == "/feedback"'))
print("fb buttons:", a.count('data-act="fb"'))
print("=== settings.py ===")
print("think_mode REGISTRY:", '"think_mode"' in s)
print("think_mode B:", bool(re.search(r'"think_mode"\s*:\s*\(\s*0\s*,\s*2\s*,\s*1\s*\)', s)))
print("=== behavior_tools.py ===")
if "kind, payload, args = agent.parse_model" in b:
    print("PROBLEM: 3-значная распаковка (нужно 4)")
elif "agent.parse_model" in b:
    print("OK: распаковка не 3-значная")
else:
    print("parse_model не найден")
