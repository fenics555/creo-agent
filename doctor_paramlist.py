# -*- coding: utf-8 -*-
import io

ct = r"D:\AI\tools\agent\creo_tools.py"
s = io.open(ct, encoding="utf-8").read()

def rep(old, new, tag):
    global s
    if new in s: print("[~] %s: уже" % tag); return
    if old not in s: print("[x] %s: якорь не найден" % tag); return
    s = s.replace(old, new, 1); print("[+] %s" % tag)

rep('        pl = d.get("param_list") if isinstance(d, dict) else d',
    '        pl = (d.get("param_list") or d.get("paramlist")) if isinstance(d, dict) else d',
    "_param_list: paramlist")

rep('have = set(p.get("name") for p in ((jp.get("data") or {}).get("param_list") or [])) if ok(jp) else set()',
    'have = set(p.get("name") for p in ((jp.get("data") or {}).get("param_list") or (jp.get("data") or {}).get("paramlist") or [])) if ok(jp) else set()',
    "аудит: paramlist")

rep('def _flex_list(d):',
    'def _kids(n):\n    if not isinstance(n, dict):\n        return []\n    return n.get("children") or n.get("components") or n.get("models") or n.get("paths") or n.get("submodels") or []\n\ndef _flex_list(d):',
    "хелпер _kids")

rep('            for ch in (node.get("children") or []): stack.append((ch, lvl + 1))',
    '            for ch in _kids(node): stack.append((ch, lvl + 1))',
    "bom: всеядный обход")

rep('def tool_open_errors',
    'def tool_bom_raw(name="", **kw):\n    nm = name or tool_get_active()\n    j = creo_call("bom", "get_paths", {"file": nm, "paths": False, "top_level": False, "exclude_inactive": True}, 30)\n    return json.dumps(j, ensure_ascii=False)[:900]\n\ndef tool_open_errors',
    "tool_bom_raw")

rep('    {"name": "creo_audit_folder",',
    '    {"name": "creo_bom_raw", "desc": "Сырой JSON ответа bom:get_paths (диагностика)", "params": {"name": "сборка"}, "approval": False, "fn": tool_bom_raw},\n    {"name": "creo_audit_folder",',
    "регистрация creo_bom_raw")

io.open(ct, "w", encoding="utf-8").write(s)

sp = r"D:\AI\tools\agent\spec_tools.py"
t = io.open(sp, encoding="utf-8").read()
def reps(old, new, tag):
    global t
    if new in t: print("[~] spec %s: уже" % tag); return
    if old not in t: print("[x] spec %s: якорь не найден" % tag); return
    t = t.replace(old, new, 1); print("[+] spec %s" % tag)

reps('    return (j.get("data") or {}).get("param_list") or []',
     '    return (j.get("data") or {}).get("param_list") or (j.get("data") or {}).get("paramlist") or []',
     "_params_of: paramlist")
reps('seen, comps, stack = set(), [], list(root.get("children") or [])',
     'seen, comps, stack = set(), [], list(CT._kids(root))',
     "bom корень")
reps('        stack.extend(node.get("children") or [])',
     '        stack.extend(CT._kids(node))',
     "bom обход")
io.open(sp, "w", encoding="utf-8").write(t)
print("ГОТОВО: .\\AI_RESTART.bat")