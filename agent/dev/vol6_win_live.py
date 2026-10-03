# -*- coding: utf-8 -*-
"""Живая сборка окна аудита чертежа (волна 6): окно поднимается, кнопка ПРОВЕРИТЬ
отрабатывает в потоке, дерево и сводка заполняются на ЖИВОМ прогоне."""
import io
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(AGENT / "drawing_audit"))

fail = []


def ok(name, cond, detail=""):
    d = detail if isinstance(detail, str) else str(detail)
    print(("OK   " if cond else "FAIL ") + name + ((" | " + d) if d else ""))
    if not cond:
        fail.append(name)


import gui as g        # noqa: E402
import drawing_audit as eng   # noqa: E402

app = g.App()
app.root.update_idletasks()
ok("окно аудита собрано", app.root.winfo_exists() == 1)
ok("чек-лист в таблице настроек загружен",
   bool(app.tbl.vals.get("notes")), app.tbl.vals.get("notes", ""))

# живой прогон боевой папки через окно (папка маленькая, чтобы проба была быстрой)
app.tbl.vals["folders"] = str(eng.ETALON.parent)
t0 = time.time()
app.run()
for _ in range(160):
    app.root.update()
    time.sleep(0.05)
    if app.res is not None:
        break
ok("прогон отработал в потоке", app.res is not None, "%.2f с" % (time.time() - t0))
if app.res:
    kids = app.tree.get_children()
    ok("дерево заполнено", len(kids) > 0,
       "строк: %d, чертежей: %d, предупреждений: %d"
       % (len(kids), app.res["checked"], app.res["warns"]))
    ok("сводка с процентом", "соответствие" in app.sum_var.get(), app.sum_var.get())
    ok("ошибок на боевой папке нет", app.res["errors"] == 0,
       "ошибок: %d" % app.res["errors"])
    if kids:
        app.tree.selection_set(kids[0])
        ok("выбор строки для превью работает", app.selected_file() is not None,
           app.selected_file() or "нет")
app.root.destroy()
print("=== ИТОГ ЖИВОГО ОКНА ВОЛНЫ 6: %s (провалов %d) ==="
      % ("ОК" if not fail else "НЕ ОК", len(fail)))
if fail:
    print("провалы: " + "; ".join(fail))
sys.exit(1 if fail else 0)