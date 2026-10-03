# -*- coding: utf-8 -*-
"""vol11_size.py — ЖИВАЯ проверка РЕАЛЬНЫХ размеров окон (слово владельца 03.10.2026:
«не работает, что-то с размерами окон»).

ЧТО ПРОВЕРЯЕТ. Прежняя проба vol10_win.py печатала `winfo_width/height` =(1, 1) —
это размер СКРЫТОГО окна (root.withdraw()), то есть цифра ничего не значила. Здесь окно
ПОКАЗЫВАЕТСЯ (`deiconify` + `update`), после чего размер становится настоящим. Проверяем:
  1) окно имеет ненулевой размер и он близок к запрошенному geometry;
  2) размер НЕ меньше minsize (окно не схлопнулось в полосу);
  3) содержимое (кнопки/дерево/лог) реально имеет ненулевой размер — «пустое» окно
     с кнопками 0x0 это как раз «окно есть, а в нём ничего»;
  4) окно открывается ДВАЖДЫ подряд (баг «второй раз не открывается»);
  5) ширина не обрезана: сумма минимальных ширин колонок влезает в окно.
"""
import io
import sys
import time
import tkinter as tk
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(r"D:\AI\tools\agent")
ok = [0]
fail = [0]


def crit(cond, text):
    if cond:
        ok[0] += 1
        print("  OK   %s" % text)
    else:
        fail[0] += 1
        print("  ПРОВАЛ %s" % text)


def measure(build, title):
    """Поднять окно, показать, дождаться расчёта геометрии, вернуть замеры."""
    r = tk.Tk()
    app = build(r)
    r.deiconify()
    r.update_idletasks()
    r.update()
    time.sleep(0.4)
    r.update()
    w, h = r.winfo_width(), r.winfo_height()
    rw, rh = r.winfo_reqwidth(), r.winfo_reqheight()
    data = {"w": w, "h": h, "rw": rw, "rh": rh, "minsize": r.minsize(), "root": r, "app": app}
    return data


print("== ОКНО ЧИСТИЛЬЩИКА (purge_versions\\gui.py) ==")
sys.path.insert(0, str(AGENT / "purge_versions"))
sys.path.append(str(AGENT))
try:
    import gui as G

    d = measure(lambda r: G.PurgeGUI(r), "purge")
    print("   размер: %dx%d, запрошенный: %dx%d, minsize: %s"
          % (d["w"], d["h"], d["rw"], d["rh"], d["minsize"]))
    crit(d["w"] > 400 and d["h"] > 300, "окно имеет настоящий размер %dx%d" % (d["w"], d["h"]))
    crit(d["w"] >= d["minsize"][0] and d["h"] >= d["minsize"][1],
         "размер не меньше minsize %s" % (d["minsize"],))
    a = d["app"]
    for nm, wid in (("ПЛАН", a.btn_plan), ("ЧИСТИТЬ", a.btn_execute), ("README", a.btn_readme)):
        crit(wid.winfo_width() > 30 and wid.winfo_height() > 10,
             "кнопка %s видима и кликабельна: %dx%d" % (nm, wid.winfo_width(), wid.winfo_height()))
    crit(a.tree.winfo_width() > 100, "дерево результатов по ширине: %d" % a.tree.winfo_width())
    crit(a.info_text.winfo_height() > 20, "панель лога по высоте: %d" % a.info_text.winfo_height())
    # Сумма минимальных ширин колонок дерева должна влезать в окно
    cols = sum(int(a.tree.column(c, "width")) for c in a.tree["columns"])
    crit(cols <= d["w"], "колонки дерева (%d) влезают в окно (%d)" % (cols, d["w"]))
    d["root"].destroy()

    d2 = measure(lambda r: G.PurgeGUI(r), "purge-2")
    crit(d2["w"] > 400, "второй раз открывается: %dx%d" % (d2["w"], d2["h"]))
    d2["root"].destroy()
except Exception as e:
    crit(False, "чистильщик: %s: %s" % (type(e).__name__, e))

print("\n== ОКНО СБОРА (harvest_gui.py) ==")
try:
    if str(AGENT) not in sys.path:
        sys.path.insert(0, str(AGENT))
    import harvest_gui as HG
    d = measure(lambda r: HG.HarvestGUI(r), "harvest")
    print("   размер: %dx%d, запрошенный: %dx%d, minsize: %s"
          % (d["w"], d["h"], d["rw"], d["rh"], d["minsize"]))
    crit(d["w"] > 400 and d["h"] > 300, "окно имеет настоящий размер %dx%d" % (d["w"], d["h"]))
    crit(d["w"] >= d["minsize"][0], "размер не меньше minsize %s" % (d["minsize"],))
    a = d["app"]
    crit(a.tree.winfo_width() > 100, "дерево по ширине: %d" % a.tree.winfo_width())
    crit(a.log_txt.winfo_height() > 20, "лог по высоте: %d" % a.log_txt.winfo_height())
    crit(a.stop_btn.winfo_width() > 30, "кнопка СТОП: %dx%d" % (a.stop_btn.winfo_width(),
                                                                 a.stop_btn.winfo_height()))
    d["root"].destroy()
except Exception as e:
    crit(False, "harvest: %s: %s" % (type(e).__name__, e))

print("\nИТОГ: критериев %d, провалов %d" % (ok[0] + fail[0], fail[0]))
print("ВЕРДИКТ: %s" % ("РАЗМЕРЫ В ПОРЯДКЕ" if not fail[0] else "ЕСТЬ ПРОБЛЕМА С РАЗМЕРАМИ"))
sys.exit(1 if fail[0] else 0)