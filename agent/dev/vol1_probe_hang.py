# -*- coding: utf-8 -*-
"""Где именно зависает config_audit: замер каждого шага с flush (проба висяка).
Запуск: cmd /c "cd /d D:\AI\tools\agent && python -X utf8 dev\vol1_probe_hang.py"
"""
import io
import sys
import time
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
AGENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AGENT))


def mark(s):
    print("[%7.2f c] %s" % (time.time() - t0, s), flush=True)


t0 = time.time()
mark("старт")
sys.path.insert(0, str(AGENT))
import ui_common as U
mark("ui_common импортирован")
sys.path.insert(0, str(AGENT / "config_audit"))
import config_audit as eng
mark("движок импортирован, KNOWN=%d" % len(eng.CREO.config_paths() or []))
r = U.make_root("проба", "1020x620", minsize=(900, 560))
mark("make_root")
U.head(r, "ПРОБА", "подзаголовок")
mark("head")
left, right = U.split_result_left(r, right_width=470)
mark("split_result_left")
U.actions(left, primary=(("ПРОВЕРИТЬ", lambda: None),), secondary=(("Открыть файл", lambda: None),))
mark("actions")
tr = U.result_tree(left, ("st", "line", "opt", "value", "path"),
                   ("Статус", "Строка", "Настройка", "Значение", "Путь"),
                   [60, 60, 170, 260, 300])
mark("result_tree")
var, set_sum = U.summary(left)
mark("summary")
nb, pages = U.tabs(right, ["Основное", "Дополнительно"])
mark("tabs")
tbl = U.SettingsTable(pages[0], [{"option": "last_config", "value": r"D:\config.pro",
                                   "desc": "какой конфиг", "default": r"D:\config.pro"}],
                      log=print)
mark("SettingsTable")
_, logw = U.log_view(r, height=6)
mark("log_view")
st = U.statusbar(r)
mark("statusbar")
U.readme_button(pages[1], AGENT / "config_audit", print)
mark("readme_button")
r.update_idletasks()
mark("update_idletasks")
r.destroy()
mark("каркас целиком собран")
# --- теперь настоящее окно config_audit: импорт и сборка БЕЗ запуска проверки ---
sys.path.insert(0, str(AGENT / "config_audit"))
import gui as g
mark("gui импортирован")
app = g.App()
mark("config_audit App() собран (root=%s)" % app.root.winfo_exists())
app.root.update_idletasks()
mark("config_audit update_idletasks")
app.root.destroy()
mark("готово — окно config_audit собирается, висяка нет")