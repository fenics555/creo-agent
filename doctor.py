# -*- coding: utf-8 -*-
import re, json
from pathlib import Path
AG = Path(__file__).resolve().parent
BASE = AG.parent

# 1) users.py: убрать хвост TOOLS (users — не блок, реестр его не читает)
up = AG / "users.py"
s = up.read_text(encoding="utf-8")
i = s.find("def tool_role_tools_search")
if i >= 0:
    j = s.find("\nTOOLS", i)
    if j >= 0:
        up.write_text(s[:j] + "\n", encoding="utf-8")
        print("[+] users.py: хвост TOOLS убран (функции остались)")
else:
    print("[~] users.py: role-функции не найдены")

# 2) role_tools.py: настоящий блок ДОСТУПЫ+
rt = AG / "role_tools.py"
if not rt.exists():
    rt.write_text('# -*- coding: utf-8 -*-\nr"""Права ролей на инструменты."""\nimport users\nTOOLS = [\n {"name": "role_tools_show", "desc": "Админка: карта инструментов для роли (разрешено/запрещено)", "params": {"role": "роль"}, "approval": False, "fn": users.tool_role_tools_show},\n {"name": "role_tools_set", "desc": "Админка: запретить/разрешить роли инструмент", "params": {"role": "роль", "tool": "имя инструмента", "deny": "1 запрет / 0 разрешить"}, "approval": True, "fn": users.tool_role_tools_set},\n {"name": "role_tools_search", "desc": "Поиск инструментов по роли и слову", "params": {"role": "роль", "q": "слово"}, "approval": False, "fn": users.tool_role_tools_search},\n]\n', encoding="utf-8")
    print("[+] role_tools.py: блок создан")

# 3) diagnostic_tools: CT на уровень модуля, внутренние импорты убрать
dp = AG / "diagnostic_tools.py"
s = dp.read_text(encoding="utf-8")
changed = False
if not re.search(r"(?m)^import creo_tools as CT", s):
    idx = s.find("\nimport ")
    if idx >= 0:
        s = s[:idx+1] + "import creo_tools as CT\n" + s[idx+1:]
        changed = True
s2 = re.sub(r"(?m)^[ \t]+import creo_tools as CT[ \t]*\n", "", s)
if s2 != s:
    s = s2; changed = True
if changed:
    dp.write_text(s, encoding="utf-8")
    print("[+] diagnostic_tools: CT исправлен (UnboundLocalError уйдёт)")

# 4) kb_roots/kb_exclude -> config.json; после этого файлы удаляемы
cfg = AG / "data" / "config.json"
d = {}
if cfg.exists():
    try: d = json.loads(cfg.read_text(encoding="utf-8"))
    except Exception: d = {}
rf, ef = BASE / "kb_roots.txt", BASE / "kb_exclude.txt"
if rf.exists() and not d.get("scan_roots"):
    d["scan_roots"] = [l.strip() for l in rf.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
if ef.exists() and not d.get("scan_exclude"):
    d["scan_exclude"] = [l.strip() for l in ef.read_text(encoding="utf-8").splitlines() if l.strip() and not l.startswith("#")]
cfg.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
print("[+] config.json: scan_roots/scan_exclude перенесены -> kb_*.txt можно удалять")
print("ГОТОВО: .\\AI_RESTART.bat, затем creoson_full_test")