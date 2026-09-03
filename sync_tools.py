# -*- coding: utf-8 -*-
import re, subprocess, datetime
import core
def _git(args):
    try:
        r = subprocess.run(["git"] + args, cwd=str(core.REPO), capture_output=True, text=True, timeout=180)
        return (r.stdout or r.stderr).strip()[:800] or "ок"
    except Exception as e: return "git ошибка: %s" % e
def tool_fleet_pull(**kw): return _git(["pull", "--rebase"])
def tool_fleet_commit(msg="", **kw):
    _git(["add", "-A"]); return _git(["commit", "-m", msg or "автокоммит %s" % datetime.datetime.now().strftime("%d.%m %H:%M")])
def tool_fleet_push(**kw): return _git(["push"])
def tool_fleet_sync(msg="", **kw): return "\n".join([tool_fleet_commit(msg), tool_fleet_push()])
def tool_case_save(title="", text="", **kw):
    if not (title and text): return "укажи title и text"
    nm = re.sub(r"[^A-Za-zА-Яа-я0-9_.-]+", "_", title.strip())[:50] or "case"
    d = core.REPO / "Решения"; d.mkdir(parents=True, exist_ok=True)
    p = d / ("CASE_%s_%s.md" % (datetime.datetime.now().strftime("%y%m%d"), nm))
    p.write_text("# %s\n\n%s\n" % (title, text), encoding="utf-8")
    return "кейс: %s" % p.name
TOOLS = [
 {"name": "fleet_pull", "desc": "Флот: забрать решения", "params": {}, "approval": False, "fn": tool_fleet_pull},
 {"name": "fleet_commit", "desc": "Флот: коммит", "params": {"msg": "сообщение"}, "approval": True, "fn": tool_fleet_commit},
 {"name": "fleet_push", "desc": "Флот: пуш", "params": {}, "approval": True, "fn": tool_fleet_push},
 {"name": "fleet_sync", "desc": "Флот: коммит+пуш", "params": {"msg": "сообщение"}, "approval": True, "fn": tool_fleet_sync},
 {"name": "case_save", "desc": "Сохранить кейс в репо", "params": {"title": "заголовок", "text": "текст"}, "approval": False, "fn": tool_case_save},
]
