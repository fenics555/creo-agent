# -*- coding: utf-8 -*-
"""hol_check — ОКНО проверки таблиц отверстий (каркас ui_common, волна 1).

Запуск: hol_check_gui.bat. Класс Р: Creo и агент не нужны, только чтение.
Движок — `hol_check.py` в этой же папке (функция scan).
"""
import io
import json
import sys
import time
from pathlib import Path

# НЕ переназначаем sys.stdout при импорте: проба может импортировать это окно,
# и вторая обёртка TextIOWrapper закрыла бы первый поток
# (ValueError: I/O operation on closed file — найдено живой пробой волны 3).
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import tkinter as tk                         # noqa: E402
from tkinter import filedialog, messagebox   # noqa: E402
import hol_check as eng                      # noqa: E402
import ui_common as U                         # noqa: E402

SETTINGS = Path(r"D:\AI\tools\agent\data\hol_check_settings.json")
DEFAULTS = {"folders": [str(d) for d in eng.DEFAULT_DIRS], "show_ok": "нет"}
ICON_TAG = {"ok": ("ok", U.ICON_OK), "warn": ("warn", U.ICON_WARN),
            "error": ("fail", U.ICON_ERR)}


class App:
    def __init__(self, root=None):
        self.root = root or U.make_root("V1 — ТАБЛИЦЫ ОТВЕРСТИЙ (проверка)", "1120x680",
                                        minsize=(950, 600))
        self.root.minsize(950, 600)
        self.st = self.load()
        self.res = None
        self.build()

    def load(self):
        d = dict(DEFAULTS)
        try:
            if SETTINGS.exists():
                d.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
        except Exception:
            pass
        return d

    def save(self, vals):
        try:
            SETTINGS.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS.write_text(json.dumps(vals, ensure_ascii=False, indent=1),
                                encoding="utf-8")
            return "сохранено: %s" % SETTINGS
        except Exception as e:
            return "ошибка: %s" % e

    def build(self):
        U.head(self.root, "Проверка таблиц отверстий (.hol)",
               "Ищет то, что ломало Creo 18.09.2026: разорванные имена колонок в шапке "
               "THREAD_DATA. Ничего не чинит — только показывает, где чинить (класс Р).")
        left, right = U.split_result_left(self.root, right_width=430)

        U.actions(left, primary=(("ПРОВЕРИТЬ", self.run),),
                  secondary=(("Открыть папку отчётов", self.open_reports),))
        self.tree = U.result_tree(left, ("st", "file", "check", "note"),
                                  ("Статус", "Файл", "Проверка", "Что не так"),
                                  [60, 240, 160, 380])
        self.sum_var, self.set_summary = U.summary(left)

        nb, pages = U.tabs(right, ["Основное", "Дополнительно"])
        self.tbl = U.SettingsTable(pages[0], [
            {"option": "folders", "value": "; ".join(self.st.get("folders") or []),
             "desc": "папки с .hol через «;» (пусто = боевые)",
             "default": "; ".join(str(d) for d in eng.DEFAULT_DIRS)},
            {"option": "show_ok", "value": self.st.get("show_ok", "нет"),
             "desc": "показывать ли успешные проверки: нет/да", "default": "нет"},
        ], log=self.log, on_apply=self._on_apply)
        self.tbl.saved = dict(self.tbl.vals)

        ex = pages[1]
        tk.Label(ex, text="Папки (через «;»):", bg=U.BG, anchor="w").pack(anchor="w", padx=8)
        tk.Button(ex, text="Добавить папку…", command=self.add_folder).pack(anchor="w", padx=8, pady=3)
        tk.Button(ex, text="Папка отчётов", command=self.open_reports).pack(anchor="w", padx=8, pady=3)
        U.readme_button(ex, _HERE, self.log)

        self._log_box, self._log_write = U.log_view(self.root, height=6)
        self.status = U.statusbar(self.root)
        self.log("проверка ничего не меняет на диске — только читает .hol")

    def log(self, s):
        try:
            self._log_write(str(s))
        except Exception:
            pass

    def _on_apply(self, vals):
        self.save(vals)
        return vals

    def add_folder(self):
        p = filedialog.askdirectory()
        if not p:
            return
        cur = [x for x in self.tbl.vals["folders"].split("; ") if x]
        if p not in cur:
            cur.append(p)
            self.tbl.vals["folders"] = "; ".join(cur)
            self.tbl.refresh()

    def open_reports(self):
        import os
        try:
            os.startfile(str(eng.LOG_DIR))
        except Exception as e:
            messagebox.showwarning("Не открыть", str(e))

    def folders(self):
        raw = [x.strip() for x in self.tbl.vals.get("folders", "").split(";") if x.strip()]
        return raw or [str(d) for d in eng.DEFAULT_DIRS]

    def run(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        dirs = self.folders()
        self.status.set("проверяю…")
        t0 = time.time()

        def work():
            return eng.scan(dirs)

        U.run_in_thread(self.root, work, on_done=lambda r: self.show(r, t0, dirs),
                        on_error=lambda e: self.status.set("ошибка проверки"),
                        log=self.log)

    def show(self, res, t0, dirs):
        self.res = res
        show_ok = self.tbl.vals.get("show_ok") == "да"
        n = 0
        for r in res["rows"]:
            if r["verdict"] == "ok" and not show_ok:
                continue
            n += 1
            tag, icon = ICON_TAG[r["verdict"]]
            self.tree.insert("", "end", values=(icon, Path(r["path"]).name, r["id"], r["note"]),
                             tags=(tag,))
        broken = sum(1 for r in res["rows"]
                     if r["verdict"] == "error" and r["id"] == "broken_names")
        self.set_summary(res["checked"], res["checked"] - broken, res["warns"],
                         label="строк в таблице: %d, %.2f с" % (n, time.time() - t0))
        self.status.set("готово за %.2f с: ошибок %d, предупреждений %d"
                        % (time.time() - t0, res["errors"], res["warns"]))
        self.log("проверено папок: %d, файлов: %d, ошибок: %d, предупреждений: %d"
                 % (len(dirs), res["checked"], res["errors"], res["warns"]))
        try:
            rp, cp = eng.write_report(res, time.time() - t0)
            self.log("отчёт: %s" % rp)
            self.log("CSV: %s" % cp)
        except Exception as e:
            self.log("отчёт не записан: %s" % e)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    r = U.make_root("V1 — ТАБЛИЦЫ ОТВЕРСТИЙ (проверка)", "1120x680", minsize=(950, 600))
    App(r)
    r.mainloop()