# -*- coding: utf-8 -*-
import json, re
import creo_tools as CT

def tool_cs_diag(file="mvc-922_00_00_00.asm", **kw):
    base = re.sub(r"\.(prt|asm|drw)(\.\d+)?$", "", str(file), flags=re.I)
    out = []
    for variant in (str(file), base):
        j = CT.creo_call("parameter", "list", {"file": variant}, 20)
        d = j.get("data")
        if isinstance(d, dict):
            n = len(d.get("param_list") or [])
        elif isinstance(d, list):
            n = len(d)
        else:
            n = -1
        out.append("'%s' -> error=%s, параметров=%s, тип data=%s"
                   % (variant, (j.get("status") or {}).get("error"), n, type(d).__name__))
    j = CT.creo_call("parameter", "list", {"file": base}, 20)
    out.append("raw[:700]=" + json.dumps(j.get("data"), ensure_ascii=False)[:700])
    return "\n".join(out)

TOOLS = [
    {"name": "cs_diag", "desc": "Диагностика CREOSON: сырой ответ parameter:list (с расширением и без)", "params": {"file": "имя файла"}, "approval": False, "fn": tool_cs_diag},
]