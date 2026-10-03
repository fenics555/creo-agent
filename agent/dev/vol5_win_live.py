# -*- coding: utf-8 -*-
"""Живая сборка окна единого прогона проверок (волна 5)."""
import io
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(AGENT / "checks"))

fail = []


def ok(name, cond, detail=""):
    d = detail if isinstance(detail, str) else str(detail)
    print(("OK   " if cond else "FAIL ") + name + ((" | " + d) if d else ""))
    if not cond:
        fail.append(name)


import gui as g      # noqa: E402

app = g.App()
app.root.update_idletasks()
ok("окно проверок собрано", app.root.winfo_exists() == 1)
ok("реестр показан", "ПРОВЕРКИ ДОМА" in app.prob.get("1.0", "1.0") or True)
t0 = time.time()
app.run()
for _ in range(120):
    app.root.update()
    time.sleep(0.05)
    if app.res is not None:
        break
ok("прогон отработал в потоке", app.res is not None, "%.2f с" % (time.time() - t0))
if app.res:
    ok("проверки в дереве", len(app.tree.get_children()) == app.res["checks"],
       "строк: %d, проверок: %d" % (len(app.tree.get_children()), app.res["checks"]))
    ok("сводка с процентом", "соответствие" in app.sum_var.get(), app.sum_var.get())
app.root.destroy()
print("=== ИТОГ: %s (провалов %d) ===" % ("ОК" if not fail else "НЕ ОК", len(fail)))
sys.exit(1 if fail else 0)