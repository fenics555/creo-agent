# -*- coding: utf-8 -*-
import io, re
p = r"D:\AI\tools\agent\creo_tools.py"
s = io.open(p, encoding="utf-8").read()
pat = re.compile(r"def tool_get_params\(.*?\n(?=def )", re.S)
new = '''def _name_variants(nm):
    base = re.sub(r"\\.(prt|asm|drw|mfg)(\\.\\d+)?$", "", str(nm), flags=re.I)
    out, seen = [str(nm), base, base.upper()], set()
    return [v for v in out if v and not (v in seen or seen.add(v))]

def _param_list(nm):
    for v in _name_variants(nm):
        j = creo_call("parameter", "list", {"file": v}, 20)
        if not ok(j):
            continue
        d = j.get("data")
        pl = d.get("param_list") if isinstance(d, dict) else d
        if pl:
            return pl
    return []

def tool_param_raw(name="", **kw):
    nm = name or tool_get_active()
    out = []
    for v in _name_variants(nm):
        j = creo_call("parameter", "list", {"file": v}, 20)
        out.append("%s -> %s" % (v, json.dumps(j, ensure_ascii=False)[:400]))
    return "\\n".join(out)

def tool_get_params(name="", **kw):
    nm = name or tool_get_active()
    pl = _param_list(nm)
    return "\\n".join("• %s (%s) = %s" % (p.get("name"), p.get("type"), p.get("value")) for p in pl) or "параметров нет"

'''
if "_param_list" in s:
    print("[~] уже patched")
elif pat.search(s):
    s = pat.sub(lambda m: new, s, count=1)
    anchor = '{"name": "creo_get_params"'
    if anchor in s:
        s = s.replace(anchor, '{"name": "creo_param_raw", "desc": "Сырой JSON ответа parameter:list (диагностика)", "params": {"name": "модель"}, "approval": False, "fn": tool_param_raw},\n    ' + anchor, 1)
    io.open(p, "w", encoding="utf-8").write(s)
    print("[+] параметры: варианты имени + creo_param_raw")
else:
    print("[x] tool_get_params не найдена")