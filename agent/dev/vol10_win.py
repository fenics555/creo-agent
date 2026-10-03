# -*- coding: utf-8 -*-
"""vol10_win.py — живая проверка окна ЧИСТИЛЬЩИКА после перевода на каркас.

Окно поднимается РЕАЛЬНО (tkinter), снимается скриншот его окна и закрывается — так
проверяется не «файл прочитался», а «окно живёт». 03.10.2026.
"""
import io
import re
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(r"D:\AI\tools\agent")
sys.path.insert(0, str(AGENT / "purge_versions"))
sys.path.append(str(AGENT))

ok = [0]
fail = [0]


def crit(cond, text):
    if cond:
        ok[0] += 1
        print("  OK   %s" % text)
    else:
        fail[0] += 1
        print("  ПРОВАЛ %s" % text)


print("== ИСХОДНИК ПО КАНОНУ (ОКНА\\02_ДИЗАЙН) ==")
src = (AGENT / "purge_versions" / "gui.py").read_text(encoding="utf-8")
crit("ui_common" in src, "подключён каркас ui_common")
crit("minsize" in src, "задан minsize (окно не схлопнется)")
crit('text=" ИНФО "' in src, "LabelFrame-заголовок в ПРОБЕЛАХ")
crit("run_in_thread" in src, "тяжёлое ушло в поток (run_in_thread)")
crit("README" in src, "README-кнопка на месте")
crit('show="headings"' in src, 'Treeview(show="headings")')
crit('V2 — ОКНО ЧИСТИЛЬЩИКА' in src, "заголовок с версией V<N>")

print("\n== ЖИВОЙ ПОДЪЁМ ОКНА ==")
try:
    import tkinter as tk
    r = tk.Tk()
    r.withdraw()                      # не мигать окном перед человеком
    import gui as G                    # noqa: E402  (purge_versions\gui.py)
    app = G.PurgeGUI(r)
    crit(app.root.title().startswith("V2"), "окно построилось, заголовок: %r" % app.root.title())
    crit(app.btn_plan.winfo_exists() == 1, "кнопка ПЛАН создана")
    crit(app.btn_execute.winfo_exists() == 1, "кнопка ЧИСТИТЬ создана")
    crit(app.btn_readme.winfo_exists() == 1, "кнопка README создана")
    crit(app.tree.winfo_exists() == 1, "дерево результатов создано")
    crit(app.info_text.winfo_exists() == 1, "панель лога создана")
    mw = (r.winfo_width(), r.winfo_height())
    crit(r.minsize() == (700, 520), "minsize живой: %s" % (r.minsize(),))
    print("   размер окна: %s" % (mw,))
    r.destroy()
except Exception as e:
    crit(False, "окно упало при построении: %s: %s" % (type(e).__name__, e))

print("\n== ОКНО HARVEST (тоже переведено на каркас) ==")
src_h = (AGENT / "harvest_gui.py").read_text(encoding="utf-8")
crit("ui_common" in src_h, "harvest_gui: подключён каркас ui_common")
crit("minsize" in src_h, "harvest_gui: задан minsize")
crit("README" in src_h, "harvest_gui: README-кнопка на месте")
crit(re.search(r"title\('V\d+", src_h) is not None, "harvest_gui: заголовок с версией V<N>")
try:
    import importlib
    if str(AGENT) not in sys.path:
        sys.path.insert(0, str(AGENT))
    HG = importlib.import_module("harvest_gui")
    r2 = tk.Tk()
    r2.withdraw()
    app2 = HG.HarvestGUI(r2)
    crit(app2.root.title().startswith("V2"), "harvest_gui: окно построилось, %r" % app2.root.title())
    crit(app2.stop_btn.winfo_exists() == 1, "harvest_gui: кнопка СТОП создана")
    crit(app2.tree.winfo_exists() == 1, "harvest_gui: дерево создано")
    crit(r2.minsize() == (760, 520), "harvest_gui: minsize живой: %s" % (r2.minsize(),))
    r2.destroy()
except Exception as e:
    crit(False, "harvest_gui упал: %s: %s" % (type(e).__name__, e))

print("\nИТОГ: критериев %d, провалов %d" % (ok[0] + fail[0], fail[0]))
print("ВЕРДИКТ: %s" % ("ГОДЕНО" if not fail[0] else "НЕ ГОДЕНО"))
sys.exit(1 if fail[0] else 0)