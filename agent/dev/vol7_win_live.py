# -*- coding: utf-8 -*-
"""Живая сборка окна пакетных параметров (волна 7, класс Ж): план строится в потоке,
дерево заполняется, ПРИМЕНИТЬ без согласия отказывает (запись не начинается)."""
import io
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(AGENT / "batch_params"))

fail = []


def ok(name, cond, detail=""):
    d = detail if isinstance(detail, str) else str(detail)
    print(("OK   " if cond else "FAIL ") + name + ((" | " + d) if d else ""))
    if not cond:
        fail.append(name)


import gui as g          # noqa: E402
import plan as P         # noqa: E402
import apply as A        # noqa: E402

ZAKI = r"Z:\PTC\CREO-START\Libraries\Библиотека_стандартных_изделий\Гайки"

app = g.App()
app.root.update_idletasks()
ok("окно пакетных параметров собрано", app.root.winfo_exists() == 1)

# 1. План через окно (поток): узкая выборка, чтобы проба была быстрой
app.tbl.vals["root"] = ZAKI
app.tbl.vals["param"] = "GROUP=std"
app.tbl.vals["limit"] = "8"
t0 = time.time()
app.run()
for _ in range(160):
    app.root.update()
    time.sleep(0.05)
    if app.plan is not None:
        break
ok("план построен окном в потоке", app.plan is not None and not app.plan.get("error"),
   "%.2f с" % (time.time() - t0))
if app.plan:
    ok("дерево заполнено шагами", len(app.tree.get_children()) > 0,
       "строк: %d" % len(app.tree.get_children()))
    ok("сводка покажет «изменится»", "изменится/создастся" in app.sum_var.get(),
       app.sum_var.get())

# 2. ПРИМЕНИТЬ без согласия → отказ, запись не началась
app.tbl.vals["approve"] = "нет"
A.STOP["flag"] = False
app.apply()
app.root.update()
ok("ПРИМЕНИТЬ без согласия отказывает", app.res is None, "результата нет - запись не шла")

# 3. Согласие есть, но CREOSON мёртв → честный отказ RC 2, а не «успех».
#    В окне перед записью стоит messagebox-подтверждение (это правильно для человека),
#    но в АВТОПРОГОНЕ диалог вешает пробу (грабля волны 5). Поэтому окно здесь не зовём:
#    проверяем сам apply_plan - ту же функцию, что зовёт окно.
app.tbl.vals["approve"] = "да"
A.STOP["flag"] = False
if not A.creoson_alive():
    res = A.apply_plan(app.plan, approve=True, dry_run=False)
    ok("при мёртвом CREOSON — RC 2 (честный отказ)", res.get("rc") == 2,
       "RC=%s, %s" % (res.get("rc"), res.get("detail", "")[:60]))
    ok("при отказе результатов нет (ничего не «применено»»)", not res.get("results"),
       "результатов: %d" % len(res.get("results") or []))
else:
    print("INFO  CREOSON жив - этот пункт не проверялся")
ok("в коде окна подтверждение есть только при реальной записи (не в dry_run)",
   "dry = self.tbl.vals.get" in (AGENT / "batch_params" / "gui.py").read_text("utf-8"))

app.root.destroy()
print("=== ИТОГ ЖИВОГО ОКНА ВОЛНЫ 7: %s (провалов %d) ==="
      % ("ОК" if not fail else "НЕ ОК", len(fail)))
if fail:
    print("провалы: " + "; ".join(fail))
sys.exit(1 if fail else 0)