# -*- coding: utf-8 -*-
"""Живая сборка окна hol_check (волна 3) + проверка в нём. Без показа пользователю."""
import io
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(AGENT / "hol_check"))

fail = []


def ok(name, cond, detail=""):
    d = detail if isinstance(detail, str) else str(detail)
    print(("OK   " if cond else "FAIL ") + name + ((" | " + d) if d else ""))
    if not cond:
        fail.append(name)


import gui as g  # noqa: E402

app = g.App()
app.root.update_idletasks()
ok("hol_check: окно собрано", app.root.winfo_exists() == 1)
ok("hol_check: minsize", app.root.minsize() == (950, 600), str(app.root.minsize()))
ok("hol_check: таблица настроек", len(app.tbl.spec) == 2)
t0 = time.time()
app.run()
for _ in range(80):
    app.root.update()
    time.sleep(0.05)
    if app.res is not None:
        break
ok("hol_check: проверка отработала в потоке", app.res is not None, "%.2f с" % (time.time() - t0))
if app.res:
    ok("hol_check: файлов проверено > 0", app.res["checked"] > 0,
       "файлов: %d, ошибок: %d, предупреждений: %d"
       % (app.res["checked"], app.res["errors"], app.res["warns"]))
    ok("hol_check: боевые без ошибок", app.res["errors"] == 0, "ошибок: %d" % app.res["errors"])
    ok("hol_check: сводка с процентом", "соответствие" in app.sum_var.get(), app.sum_var.get())
    ok("hol_check: строки в дереве", len(app.tree.get_children()) > 0,
       "строк: %d" % len(app.tree.get_children()))
app.root.destroy()
print("=== ИТОГ: %s (провалов %d) ===" % ("ОК" if not fail else "НЕ ОК", len(fail)))
sys.exit(1 if fail else 0)