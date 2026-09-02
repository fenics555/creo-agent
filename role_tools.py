# -*- coding: utf-8 -*-
r"""РОЛИ: карта прав ролей на инструменты (блок ДОСТУПЫ+)."""
from users import role_deny_list, role_deny_set

def tool_role_tools_show(role="Инженер", **kw):
    try:
        import tools_registry as TR
    except Exception:
        return "tools_registry не найден"
    denied = set(role_deny_list(role))
    out = ["РОЛЬ %s — доступ к инструментам (%d всего, %d запрещено):" % (role, len(TR.TOOLS), len(denied))]
    for t in sorted(TR.TOOLS, key=lambda x: x.get("name", "")):
        n = t.get("name", "?")
        out.append("%s %s  — %s" % ("⛔" if n in denied else "✅", n, t.get("desc", "")[:60]))
    return "\n".join(out)

def tool_role_tools_set(role="Инженер", tool="", deny=1, **kw):
    if not tool: return "укажи tool (имя инструмента)"
    deny = str(deny) in ("1", "true", "да", "on")
    role_deny_set(role, tool, deny)
    return "роль %s: %s -> %s" % (role, tool, ("ЗАПРЕЩЕНО" if deny else "разрешено"))

def tool_role_tools_search(role="Инженер", q="", **kw):
    try:
        import tools_registry as TR
    except Exception:
        return "tools_registry не найден"
    q = (q or "").strip().lower()
    denied = set(role_deny_list(role))
    out = []
    for t in TR.TOOLS:
        n = t.get("name", "")
        if q and q not in n.lower() and q not in (t.get("desc", "") or "").lower(): continue
        out.append("%s %s" % ("⛔" if n in denied else "✅", n))
    return "\n".join(out) or ("по '%s' ничего" % q)

TOOLS = [
    {"name": "role_tools_show", "desc": "Админка: показать карту инструментов для роли (✅ разрешено / ⛔ запрещено)", "params": {"role": "роль (по умолч. Инженер)"}, "approval": False, "fn": tool_role_tools_show},
    {"name": "role_tools_set", "desc": "Админка: запретить/разрешить роли конкретный инструмент", "params": {"role": "роль", "tool": "имя инструмента", "deny": "1 запрет / 0 разрешить"}, "approval": True, "fn": tool_role_tools_set},
    {"name": "role_tools_search", "desc": "Поиск инструментов по роли и ключевому слову", "params": {"role": "роль", "q": "слово"}, "approval": False, "fn": tool_role_tools_search},
]
