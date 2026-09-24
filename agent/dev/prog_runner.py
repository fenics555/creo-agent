# -*- coding: utf-8 -*-
r"""ОБЁРТКА ЗАПУСКА ДВИЖКА ДОМА (dev\prog_runner.py)

Зачем: любая программа дома должна сама докладывать в ОБЩИЙ ЖУРНАЛ РАБОТ —
«сканирование запущено в фоне» и «сканирование завершено …». Агент запускает движок через эту
обёртку (prog_tools.prog_run), обёртка пишет вывод в файл запуска и ставит две строки в журнал.

Зов:  python dev\prog_runner.py <id> <cwd> <файл-журнала> <команда> [аргументы…]
"""
import sys, os, time, datetime, subprocess
from pathlib import Path

sys.path.insert(0, r"D:\AI\tools\agent")
import core  # noqa: E402  (общий журнал работ дома)


def main():
    if len(sys.argv) < 5:
        print(__doc__)
        return 2
    prog_id, cwd, logfile = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    cmd = sys.argv[4:]
    logfile.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    core.job(prog_id, "запущено в фоне", движок=" ".join(cmd[:3]))
    head = "\n%s >>> %s\n    cwd=%s\n" % (datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                                          " ".join(cmd), cwd)
    with open(logfile, "a", encoding="utf-8", errors="replace") as f:
        f.write(head)
        f.flush()
        try:
            r = subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT, shell=False)
            code = r.returncode
        except Exception as e:
            f.write("ОШИБКА ЗАПУСКА: %s\n" % e)
            code = -1
    dt = round(time.time() - t0, 1)
    core.job(prog_id, "завершено" if code == 0 else "завершено с ошибкой",
             code=code, секунд=dt, лог=str(logfile))
    return code


if __name__ == "__main__":
    sys.exit(main())
