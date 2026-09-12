# -*- coding: utf-8 -*-
r"""ФЛОТ-ПАМЯТЬ: git-синхронизация creo-repo (решения становятся общими)."""
import subprocess
import core
def _run(args):
    try:
        r = subprocess.run(["git"] + args, cwd=str(core.REPO), capture_output=True, text=True, timeout=120)
        return (r.stdout or r.stderr).strip()[:800] or "ок"
    except Exception as e:
        return "git ошибка: %s" % e
def tool_git_status(**kw): return _run(["status", "--short"])
def tool_git_commit(msg="", **kw):
    _run(["add", "-A"])
    return _run(["commit", "-m", msg or "автокоммит агента: новое решение"])
def tool_git_push(**kw): return _run(["push"])
def tool_git_pull(**kw): return _run(["pull", "--rebase"])
TOOLS = [
 {"name": "git_status", "desc": "Флот: что изменилось в creo-repo", "params": {}, "approval": False, "fn": tool_git_status},
 {"name": "git_commit", "desc": "Флот: закоммитить новые решения/скиллы", "params": {"msg": "сообщение"}, "approval": True, "fn": tool_git_commit},
 {"name": "git_push", "desc": "Флот: раздать решения всем машинам", "params": {}, "approval": True, "fn": tool_git_push},
 {"name": "git_pull", "desc": "Флот: забрать решения с других машин", "params": {}, "approval": False, "fn": tool_git_pull},
]
