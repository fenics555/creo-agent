# -*- coding: utf-8 -*-
"""batch_params - ОКНО пакетных параметров (каркас ui_common, волна 7, класс Ж).

Запуск: batch_params_gui.bat. Логика: сначала ПРОВЕРИТЬ строит план (без Creo),
человек смотрит сводку; ПРИМЕНИТЬ пишет в Creo только с флажком согласия и на копии;
СТОП останавливает цикл между моделями.
"""
import io
import json
import sys
import time
from pathlib import Path

# НЕ переназначаем sys.stdout при импорте (урок волны 3).
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import tkinter as tk                         # noqa: E402
from tkinter import filedialog, messagebox   # noqa: E402
import plan as P                              # noqa: E402
import apply as A                             # noqa: E402
import ui_common as U                         # noqa: E402

ICON_TAG = {"change": ("warn", U.ICON_WARN), "same": ("ok", U.ICON_OK),
            "miss": ("warn", U.ICON_WARN), "read_fail": ("fail", U.ICON_ERR)}


class App:
    def __init__(self, root=None):
        self.root = root or U.make_root("V1 — ПАКЕТНЫЕ ПАРАМЕТРЫ", "1180x720",
                                        minsize=(1000, 640))
        self.root.minsize(1000, 640)
        self.plan = None
        self.res = None
        self.build()

    def build(self):
        U.head(self.root, "Пакетные параметры: план, согласие, СТОП",
               "Класс Ж. Сначала план (без Creo), потом запись по вашему согласию и только "
               "на копии. Боевые файлы не трогаются.")
        left, right = U.split_result_left(self.root, right_width=440)
        self.stop_flag, _ = U.stop_button(left, log=self.log)
        U.actions(left, primary=(("ПРОВЕРИТЬ", self.run), ("ПРИМЕНИТЬ", self.apply)),
                  secondary=(("Открыть планы", self.open_plans),))
        self.tree = U.result_tree(left, ("st", "file", "param", "note"),
                                  ("Статус", "Модель", "Параметр", "Что"),
                                  [60, 210, 150, 420])
        self.sum_var, self.set_summary = U.summary(left)

        nb, pages = U.tabs(right, ["Параметры", "План"])
        self.tbl = U.SettingsTable(pages[0], [
            {"option": "root", "value": str(P.DEFAULT_ROOT),
             "desc": "папка с моделями", "default": str(P.DEFAULT_ROOT)},
            {"option": "param", "value": "GROUP=std;МАССА=0.1",
             "desc": "параметры через «;»: ИМЯ=ЗНАЧЕНИЕ",
             "default": "GROUP=std;МАССА=0.1"},
            {"option": "limit", "value": "300", "desc": "сколько моделей просмотреть",
             "default": "300"},
            {"option": "approve", "value": "нет",
             "desc": "согласие на запись в Creo: нет/да (без «да» ПРИМЕНИТЬ откажет)",
             "default": "нет"},
            {"option": "dry_run", "value": "да",
             "desc": "проба без записи: да/нет", "default": "да"},
        ], log=self.log)
        self.tbl.saved = dict(self.tbl.vals)

        pl = pages[1]
        tk.Button(pl, text="Выбрать папку…", command=self.pick_folder)\
            .pack(anchor="w", padx=8, pady=6)
        tk.Button(pl, text="Перезагрузить план с диска", command=self.load_plan)\
            .pack(anchor="w", padx=8, pady=3)
        U.readme_button(pl, _HERE, self.log)

        self._log_box, self._log_write = U.log_view(self.root, height=6)
        self.status = U.statusbar(self.root)
        self.log("сначала ПРОВЕРИТЬ: план строится чтением файлов, без Creo")

    def log(self, s):
        try:
            self._log_write(str(s))
        except Exception:
            pass

    def params(self):
        return [x.strip() for x in self.tbl.vals.get("param", "").split(";") if x.strip()]

    def approve(self):
        return self.tbl.vals.get("approve") == "да"

    def pick_folder(self):
        p = filedialog.askdirectory()
        if not p:
            return
        self.tbl.vals["root"] = p
        self.tbl.refresh()
        self.log("папка: %s" % p)

    def open_plans(self):
        try:
            import os
            os.startfile(str(P.LOG_DIR))
        except Exception as e:
            self.log("не открыть папку планов: %s" % e)

    def load_plan(self):
        """Перечитать последний план с диска (проверка: план - это файл, а не память)."""
        files = sorted(P.LOG_DIR.glob("plan_batch_params_*.json"))
        if not files:
            self.log("планов на диске нет")
            self.status.set("планов нет")
            return
        self.plan = json.loads(files[-1].read_text(encoding="utf-8"))
        self.log("план загружен: %s" % files[-1])
        self.show_plan(self.plan)

    def run(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.status.set("строю план…")
        t0 = time.time()
        root = self.tbl.vals.get("root") or None
        params = self.params()

        def work():
            return P.build_plan(root, params, int(self.tbl.vals.get("limit") or 300))

        def done(pl):
            self.plan = pl
            if pl.get("error"):
                self.status.set("ошибка плана")
                self.log("ошибка плана: %s" % pl["error"])
                return
            self.show_plan(pl)
            rp, jp = P.write_plan(pl)
            self.log("план записан: %s / %s (%.2f с)" % (rp, jp, time.time() - t0))
            self.status.set("план готов за %.2f с; ПРИМЕНИТЬ = запись, нужно согласие"
                            % (time.time() - t0))

        U.run_in_thread(self.root, work, on_done=done,
                        on_error=lambda e: self.status.set("ошибка плана"),
                        log=self.log)

    def show_plan(self, pl):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for s in pl.get("steps", []):
            tag, icon = ICON_TAG.get(s["verdict"], ("ok", U.ICON_OK))
            self.tree.insert("", "end",
                             values=(icon, s["name"], s["param"],
                                     "%s -> %s (%s)" % (s["old"] or "—", s["value"],
                                                        s["note"])),
                             tags=(tag,))
        c = pl.get("counts", {})
        self.set_summary(pl.get("total", 0), c.get("same", 0),
                         c.get("change", 0) + c.get("miss", 0) + c.get("read_fail", 0),
                         label="изменится/создастся: %d" % pl.get("will_change", 0))

    def apply(self):
        if not self.plan or not self.plan.get("steps"):
            self.status.set("сначала ПРОВЕРИТЬ (плана нет)")
            self.log("ПРИМЕНИТЬ без плана: отказ")
            return
        if not self.approve():
            self.status.set("нет согласия — запись не начата")
            self.log("ПРИМЕНИТЬ без согласия: запись НЕ началась (RC 3)")
            return
        dry = self.tbl.vals.get("dry_run") == "да"
        if not dry and not messagebox.askyesno(
                "Запись в Creo", "Прогон писать будет в %d моделей. Копия, не боевая.\nПродолжить?"
                % len({s["file"] for s in self.plan["steps"]})):
            self.status.set("отменено человеком")
            self.log("запись отменена человеком")
            return
        A.STOP["flag"] = False
        self.status.set("применяю…")
        pl = self.plan

        def work():
            return A.apply_plan(pl, approve=True, dry_run=dry, on_log=self.log)

        def done(res):
            self.res = res
            self.status.set("готово: RC %d — %s" % (res.get("rc", 0), res.get("detail", "")))
            self.log("RC %d: %s" % (res.get("rc", 0), res.get("detail", "")))
            if res.get("results"):
                self.log("отчёт: %s" % A.write_apply_report(res))

        U.run_in_thread(self.root, work, on_done=done,
                        on_error=lambda e: self.status.set("ошибка применения"),
                        log=self.log)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    r = U.make_root("V1 — ПАКЕТНЫЕ ПАРАМЕТРЫ", "1180x720", minsize=(1000, 640))
    App(r)
    r.mainloop()