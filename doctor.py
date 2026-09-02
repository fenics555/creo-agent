# -*- coding: utf-8 -*-
import io
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")

up = AG / "users.py"; u = up.read_text(encoding="utf-8")
MARK = "# == ROLE PERMS =="
if MARK in u:
    print("[~] users.py: role perms уже есть")
else:
    u += '''

# == ROLE PERMS ==
def _perms_db():
    import core
    c = core.db()
    c.execute("CREATE TABLE IF NOT EXISTS role_deny(role TEXT, tool TEXT, UNIQUE(role, tool))")
    c.commit()
    return c

def role_denied(role, tool):
    try:
        c = _perms_db()
        r = c.execute("SELECT 1 FROM role_deny WHERE role=? AND tool=?", (role or "", tool or "")).fetchone()
        c.close(); return bool(r)
    except Exception:
        return False

def role_deny_set(role, tool, deny):
    c = _perms_db()
    if deny: c.execute("INSERT OR IGNORE INTO role_deny(role, tool) VALUES(?,?)", (role, tool))
    else: c.execute("DELETE FROM role_deny WHERE role=? AND tool=?", (role, tool))
    c.commit(); c.close()

def role_deny_list(role):
    c = _perms_db()
    r = [x[0] for x in c.execute("SELECT tool FROM role_deny WHERE role=?", (role or "",))]
    c.close(); return r

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
    return "\\n".join(out)

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
    return "\\n".join(out) or ("по '%s' ничего" % q)

TOOLS += [
    {"name": "role_tools_show", "desc": "Админка: показать карту инструментов для роли (✅ разрешено / ⛔ запрещено)", "params": {"role": "роль (по умолч. Инженер)"}, "approval": False, "fn": tool_role_tools_show},
    {"name": "role_tools_set", "desc": "Админка: запретить/разрешить роли конкретный инструмент", "params": {"role": "роль", "tool": "имя инструмента", "deny": "1 запрет / 0 разрешить"}, "approval": True, "fn": tool_role_tools_set},
    {"name": "role_tools_search", "desc": "Поиск инструментов по роли и ключевому слову", "params": {"role": "роль", "q": "слово"}, "approval": False, "fn": tool_role_tools_search},
]
'''
    up.write_text(u, encoding="utf-8")
    print("[+] users.py: deny-лист ролей + 3 админ-инструмента")

print("ГОТОВО: .\\AI_RESTART.bat")
print("Проверка в чате: role_tools_show role=Инженер -> role_tools_set role=Инженер tool=copy_part deny=1")
print("Принуждение на сервере и страница в панели — следующим доктором (кинь agent.py + свежий users.py).")