# -*- coding: utf-8 -*-
import json
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")
cfg = json.loads((AG / "data" / "config.json").read_text(encoding="utf-8"))
sp = AG / "settings.py"
s = sp.read_text(encoding="utf-8")

import re
reg_keys = set(re.findall(r'\(\s*"[^"]+",\s*"([^"]+)",', s))

def grp(k):
    if k.startswith("web_"): return "Web"
    if k in ("creoson_url", "creoson_dir", "pdf_out", "backup_dir", "trail_dirs"): return "Пути"
    if k.startswith("scan_"): return "Сканер"
    return "Главное"

def typ(v):
    if isinstance(v, bool): return "bool"
    if isinstance(v, int): return "int"
    if isinstance(v, float): return "float"
    if isinstance(v, list): return "list"
    return "str"

def lit(v):
    if isinstance(v, bool): return "True" if v else "False"
    if isinstance(v, (int, float)): return repr(v)
    return json.dumps(v, ensure_ascii=False)

added = []
lines = []
for k, v in cfg.items():
    if k in reg_keys: continue
    lines.append('    ("%s", "%s", "%s", "%s", %s, "Из config.json (авто-регистрация).", True),'
                 % (grp(k), k, k, typ(v), lit(v)))
    added.append(k)

if lines:
    i = s.find("def _ensure")
    j = s.rfind("]", 0, i)
    s = s[:j] + "\n".join(lines) + "\n" + s[j:]
    sp.write_text(s, encoding="utf-8")
    print("[+] settings: авто-регистрация ключей: %s" % ", ".join(added))
else:
    print("[~] settings: все ключи config.json уже в REGISTRY")
print("ПРОВЕРКА: в чате settings_show — должны появиться steps_max и прочие.")