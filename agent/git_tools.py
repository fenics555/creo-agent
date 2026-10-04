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
def _changed_files():
    """Список ИЗМЕНЁННЫХ файлов — чтобы добавлять только их (закон параллельной ноги)."""
    out = _run(["status", "--porcelain"])
    files = []
    for line in (out or "").splitlines():
        if len(line) > 3 and line[:2].strip():
            files.append(line[3:].strip().strip('"'))
    return files
def tool_git_commit(msg="", **kw):
    # ЖИВАЯ НАХОДКА 04.10.2026 (аудит настроек, раздел граблей): здесь стоял `git add -A` —
    # ПРЯМОЙ ЗАПРЕТ закона параллельной ноги (SKILL_parallel_legs.md п.3.1): в общем репозитории
    # он подметает ЧУЖИЕ правки соседней ноги под один коммит. Теперь добавляем только
    # перечисленные файлы, и если список пуст — честно говорим, что коммитить нечего.
    files = _changed_files()
    if not files:
        return "коммитить нечего: рабочее дерево чистое"
    _run(["add", "--"] + files)
    return _run(["commit", "-m", msg or "автокоммит агента: новое решение", "--"] + files)
def tool_git_push(**kw): return _run(["push"])
def tool_git_pull(**kw): return _run(["pull", "--rebase"])
TOOLS = [
 {"name": "git_status", "desc": "Флот: что изменилось в creo-repo", "params": {}, "approval": False, "fn": tool_git_status},
 {"name": "git_commit", "desc": "Флот: закоммитить новые решения/скиллы", "params": {"msg": "сообщение"}, "approval": True, "fn": tool_git_commit},
 {"name": "git_push", "desc": "Флот: раздать решения всем машинам", "params": {}, "approval": True, "fn": tool_git_push},
 {"name": "git_pull", "desc": "Флот: забрать решения с других машин", "params": {}, "approval": False, "fn": tool_git_pull},
]
