# -*- coding: utf-8 -*-
from users import role_deny_list, role_deny_set
def tool_role_tools_show(role="Инженер", **kw):
    try: import tools_registry as TR
    except Exception: return "tools_registry не найден"
    denied = set(role_deny_list(role))
    out = ["РОЛЬ %s (%d всего, %d запрещено):" % (role, len(TR.TOOLS), len(denied))]
    for t in sorted(TR.TOOLS, key=lambda x: x.get("name","")):
        n = t.get("name","?"); out.append("%s %s — %s" % ("⛔" if n in denied else "✅", n, t.get("desc","")[:60]))
    return "\n".join(out)
def tool_role_tools_set(role="Инженер", tool="", deny=1, **kw):
    if not tool: return "укажи tool"
    deny = str(deny) in ("1","true","да","on"); role_deny_set(role, tool, deny)
    return "роль %s: %s -> %s" % (role, tool, ("ЗАПРЕЩЕНО" if deny else "разрешено"))
def tool_role_tools_search(role="Инженер", q="", **kw):
    try: import tools_registry as TR
    except Exception: return "tools_registry не найден"
    q = (q or "").lower(); denied = set(role_deny_list(role)); out = []
    for t in TR.TOOLS:
        n = t.get("name","")
        if q and q not in n.lower() and q not in (t.get("desc","") or "").lower(): continue
        out.append("%s %s" % ("⛔" if n in denied else "✅", n))
    return "\n".join(out) or "ничего"
TOOLS = [
 {"name": "role_tools_show", "desc": "Карта инструментов для роли", "params": {"role": "роль"}, "approval": False, "fn": tool_role_tools_show},
 {"name": "role_tools_set", "desc": "Запретить/разрешить роли инструмент", "params": {"role": "роль", "tool": "имя", "deny": "1/0"}, "approval": True, "fn": tool_role_tools_set},
 {"name": "role_tools_search", "desc": "Поиск инструментов по роли", "params": {"role": "роль", "q": "слово"}, "approval": False, "fn": tool_role_tools_search},
]
