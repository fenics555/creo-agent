# -*- coding: utf-8 -*-
r"""git_sync.py — ТИХИЙ автосинк дома на GitHub (без окон).

ЗАЧЕМ (23.11.2026, слово владельца «на гитхаб расписание каждые 30 минут моргает»):
прежняя цепочка `wscript RUN_HIDDEN.vbs -> GIT_SYNC*.bat -> cmd -> git` на практике
всё равно показывала консольные окна раз в 30 минут. Метод заменён:
родитель — pythonw.exe (консоли НЕТ вовсе), все дочерние процессы идут с
CREATE_NO_WINDOW, ввод git запрещён (GIT_TERMINAL_PROMPT=0, GCM_INTERACTIVE=never),
поэтому ни git, ни Git Credential Manager окно открыть не могут.

ЗАПУСК (так его зовёт Планировщик задач):
    pythonw.exe D:\AI\tools\agent\git_sync.py tools
    pythonw.exe D:\AI\tools\agent\git_sync.py repo
    pythonw.exe D:\AI\tools\agent\git_sync.py all

Логи: D:\AI\log\git_sync\git_sync_<имя>_<дата>.log (культура дома, 30 дней).
"""
import datetime
import os
import subprocess
import sys

LOG_DIR = r"D:\AI\log\git_sync"
REPOS = {
    "tools": r"D:\AI\tools",   # github.com/fenics555/creo-agent
    "repo": r"D:\AI\repo",     # github.com/fenics555/creo-repo
}
CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never", GIT_ASKPASS="")


def _log(path, line):
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write("%s %s\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), line))
    except Exception:
        pass


def _git(cwd, args, timeout=180):
    p = subprocess.run(["git"] + args, cwd=cwd, env=ENV, stdin=subprocess.DEVNULL,
                       capture_output=True, text=True, errors="replace",
                       creationflags=CNW, timeout=timeout)
    return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()


def sync(name):
    root = REPOS.get(name)
    if not root or not os.path.isdir(os.path.join(root, ".git")):
        return 2, "репозитория нет: %s" % root
    logf = os.path.join(LOG_DIR, "git_sync_%s_%s.log"
                        % (name, datetime.date.today().strftime("%Y-%m-%d")))
    rc, out, err = _git(root, ["add", "-A"])
    if rc:
        _log(logf, "%s: git add упал rc=%s %s" % (name, rc, err[:300]))
        return rc, "add"
    rc, out, err = _git(root, ["diff", "--cached", "--quiet"])
    if rc == 0:
        _log(logf, "%s: нечего коммитить (дерево чистое)" % name)
        return 0, "clean"
    msg = "autosave %s" % datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    rc, out, err = _git(root, ["commit", "-m", msg])
    if rc:
        _log(logf, "%s: commit rc=%s %s %s" % (name, rc, out[:200], err[:300]))
        return rc, "commit"
    _log(logf, "%s: commit %s" % (name, msg))
    rc, out, err = _git(root, ["push", "origin", "master"], timeout=240)
    if rc:
        _log(logf, "%s: push rc=%s %s" % (name, rc, (err or out)[:400]))
        return rc, "push"
    _log(logf, "%s: push OK %s" % (name, (out or err)[-200:]))
    return 0, "pushed"


def main():
    os.makedirs(LOG_DIR, exist_ok=True)
    what = (sys.argv[1] if len(sys.argv) > 1 else "all").strip().lower()
    names = list(REPOS) if what in ("all", "") else [what]
    worst = 0
    for n in names:
        rc, why = sync(n)
        worst = max(worst, rc)
    return worst


if __name__ == "__main__":
    sys.exit(main())