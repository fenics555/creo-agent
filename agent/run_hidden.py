# -*- coding: utf-8 -*-
r"""run_hidden.py — ТИХИЙ запуск любой команды без окна (обёртка для Планировщика).

ЗАЧЕМ (23.11.2026): `powershell.exe -WindowStyle Hidden` в задачах Планировщика всё равно
иногда мигает консолью. Здесь родитель — pythonw.exe (консоли НЕТ вовсе), а дочерний процесс
запускается с CREATE_NO_WINDOW, поэтому окно не создаётся.

ЗАПУСК из задачи:
    pythonw.exe D:\AI\tools\agent\run_hidden.py powershell.exe -NoProfile -File "C:\...\x.ps1" -Quiet

Вывод (stdout+stderr) — в D:\AI\log\agent\hidden_run.log.
"""
import datetime
import os
import subprocess
import sys

CNW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
LOG = r"D:\AI\log\agent\hidden_run.log"


def main():
    args = sys.argv[1:]
    if not args:
        return 2
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    stamp = lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write("%s запуск: %s\n" % (stamp(), " ".join(args)))
        f.flush()
        try:
            rc = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=f, stderr=f,
                                creationflags=CNW, timeout=900).returncode
        except Exception as e:
            f.write("%s ОШИБКА: %s\n" % (stamp(), e))
            return 1
        f.write("%s завершено rc=%s\n" % (stamp(), rc))
    return rc


if __name__ == "__main__":
    sys.exit(main())