# -*- coding: utf-8 -*-
"""Живая сборка окна правил (волна 4): каркас, текст правил, движение порядка."""
import io
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))
sys.path.insert(0, str(AGENT / "rules"))

fail = []


def ok(name, cond, detail=""):
    d = detail if isinstance(detail, str) else str(detail)
    print(("OK   " if cond else "FAIL ") + name + ((" | " + d) if d else ""))
    if not cond:
        fail.append(name)


import gui as g      # noqa: E402

app = g.App()
app.root.update_idletasks()
ok("окно правил собрано", app.root.winfo_exists() == 1)
ok("minsize задан", app.root.minsize() == (980, 620), str(app.root.minsize()))
ok("правила в дереве", len(app.tree.get_children()) >= 8,
   "строк: %d" % len(app.tree.get_children()))
ok("текст правил показан", app.txt.get("1.0", "10.0").strip().startswith("IF"),
   app.txt.get("1.0", "1.0").strip()[:40])
ok("форма: правила заполнены", app.lst.size() >= 8, "в списке: %d" % app.lst.size())
ok("валидация проходит", app.validate() is True)

# порядок правил меняется живым нажатием кнопки
before = app.rules()[0]["id"]
app.lst.selection_set(0)
app.shift(1)
ok("кнопка «вниз» меняет порядок", app.rules()[1]["id"] == before,
   "было: %s, стало: %s" % (before, app.rules()[1]["id"]))
app.shift(-1)
ok("кнопка «вверх» возвращает обратно", app.rules()[0]["id"] == before)

# Вкл/Выкл не портит файл (мы не сохраняем)
n_enabled = sum(1 for r in app.rules() if r.get("enabled", True))
app.lst.selection_set(0)
app.toggle()
ok("Вкл/Выкл переключает правило",
   sum(1 for r in app.rules() if r.get("enabled", True)) == n_enabled - 1
   if app.rules()[0].get("enabled", True) else True)
app.toggle()

ok("сводка с процентом", "соответствие" in app.sum_var.get(), app.sum_var.get())
app.root.destroy()
print("=== ИТОГ: %s (провалов %d) ===" % ("ОК" if not fail else "НЕ ОК", len(fail)))
sys.exit(1 if fail else 0)