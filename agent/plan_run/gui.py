# -*- coding: utf-8 -*-
r"""plan_run - ОКНО ИСПОЛНЕНИЯ ПЛАНА (каркас ui_common, волна 8, класс Ж).

Запуск: plan_run_gui.bat. Слева - шаги плана с иконкой риска, справа - настройки и
откуда план. ЗАГРУЗИТЬ читает `plan.json` и проверяет его; ВЫПОЛНИТЬ требует
флажка согласия (без него RC 3), идёт в поток и останавливается по кнопке СТОП.
Образец окна: checks\gui.py. Запись - только через runner.py.
"""
import io
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import tkinter as tk                                # noqa: E402
from tkinter import filedialog, messagebox          # noqa: E402
import plan_fmt as F                                 # noqa: E402
import runner as R                                   # noqa: E402
import ui_common as U                                # noqa: E402

APP_VERSION = "V1"

RISK_TAG = {"write": ("warn", U.ICON_WARN),
            "read": ("ok", U.ICON_SKIP),
            "destructive": ("fail", U.ICON_ERR)}


class App:
    def __init__(self, root=None):
        self.root = root or U.make_root("Ж — ПЛАНЫ ЗАДАЧ %s" % APP_VERSION,
                                        "1180x720", minsize=(1000, 640),
                                        tool_dir=_HERE)
        self.root.minsize(1000, 640)
        self.plan = None
        self.plan_path = ""
        self.res = None
        self.build()

    def build(self):
        U.head(self.root, "План задачи: шаг · что · где · риск · как откатить",
               "Класс Ж. План читается БЕЗ Creo. Исполнение - только по вашему "
               "согласию, с журналом шагов и СТОП. Боевые файлы не трогаются.")
        left, right = U.split_result_left(self.root, right_width=430)
        self.stop_flag, _ = U.stop_button(left, log=self.log)
        U.actions(left, primary=(("ЗАГРУЗИТЬ ПЛАН", self.open_plan),
                                 ("ВЫПОЛНИТЬ", self.run)),
                  secondary=(("Открыть журнал", self.open_log),))
        self.tree = U.result_tree(left, ("st", "n", "risk", "what", "where"),
                                  ("Статус", "№", "Риск", "Что", "Где"),
                                  [55, 45, 110, 120, 380])
        self.sum_var, self.set_summary = U.summary(left)

        nb, pages = U.tabs(right, ["План", "О прогоне"])
        tk.Button(pages[0], text="Выбрать plan.json…", command=self.open_plan)\
            .pack(anchor="w", padx=8, pady=6)
        self.src = tk.Label(pages[0], text="план не загружен", bg=U.BG, fg=U.MUTED,
                            font=("Consolas", 9), justify="left", anchor="w",
                            wraplength=380)
        self.src.pack(fill="x", padx=8)
        self.tbl = U.SettingsTable(pages[0], [
            {"option": "approve", "value": "нет",
             "desc": "согласие на запись: нет/да (без «да» ВЫПОЛНИТЬ откажет RC 3)",
             "default": "нет"},
            {"option": "dry_run", "value": "да",
             "desc": "проба без записи: да/нет", "default": "да"},
        ], log=self.log)
        self.tbl.saved = dict(self.tbl.vals)
        U.readme_button(pages[0], _HERE, self.log)

        tk.Label(pages[1], text=(
            "Формат: plan_version=%d, шаги: n · what · where · args · risk · "
            "rollback · verdict.\n\n"
            "risk: read (не пишет) · write (пишет) · destructive.\n"
            "rollback обязателен: шаг, который нечем откатить, писать нельзя.\n\n"
            "Журнал шагов: %s\n"
            "Отчёты: %s\n\n"
            "Носитель формата — план batch_params (его build_plan + from_batch_params)."
            % (F.PLAN_VERSION, R.LOG_DIR, R.REPORT_DIR)),
            bg=U.BG, fg=U.MUTED, font=("Segoe UI", 9), justify="left", anchor="nw",
            wraplength=380).pack(fill="both", expand=True, padx=10, pady=8)

        self._log_box, self._log_write = U.log_view(self.root, height=6)
        self.status = U.statusbar(self.root)
        self.log("ЗАГРУЗИТЬ plan.json - проверка без Creo. ВЫПОЛНИТЬ = запись, "
                 "нужно согласие")

    def log(self, s):
        try:
            self._log_write(s)
        except Exception:
            pass

    def show_plan(self, plan, path):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for s in plan.get("steps", []):
            tag, icon = RISK_TAG.get(s.get("risk"), ("ok", U.ICON_SKIP))
            self.tree.insert("", "end",
                             values=(icon, s.get("n", ""), s.get("risk", ""),
                                     s.get("what", ""), s.get("where", "")),
                             tags=(tag,))
        c = plan.get("counts", {})
        self.set_summary(plan.get("total", 0), c.get("read", 0),
                         c.get("write", 0) + c.get("destructive", 0),
                         label="изменится/создастся: %d" % c.get("write", 0))
        self.src.config(text="%s\n%s\nшагов: %d · %s"
                        % (path, plan.get("title", ""), plan.get("total", 0),
                           plan.get("counts", {})))

    def open_plan(self):
        p = filedialog.askopenfilename(title="Выбрать plan.json",
                                       filetypes=[("Планы", "*.json"), ("Все", "*.*")])
        if p:
            self.load_plan(p)

    def load_plan(self, path):
        plan, ok, errs = F.load_plan(path)
        if not ok:
            self.status.set("план не прошёл проверку")
            for e in errs[:5]:
                self.log("ОТКАЗ: %s" % e)
            return
        self.plan, self.plan_path = plan, str(path)
        self.show_plan(plan, path)
        self.status.set("план загружен: %d шагов" % plan.get("total", 0))
        self.log("план прошёл проверку: %s (шагов %d)"
                 % (path, plan.get("total", 0)))

    def open_log(self):
        R.LOG_DIR.mkdir(parents=True, exist_ok=True)
        p = R.LOG_DIR / "plan_run.log"
        if not p.exists():
            self.log("журнала ещё нет: %s" % p)
            return
        try:
            lines = p.read_text(encoding="utf-8").splitlines()[-40:]
        except Exception as e:
            self.log("журнал не читается: %s" % e)
            return
        for line in lines:
            self.log("| " + line)

    def run(self):
        if not self.plan:
            self.status.set("сначала ЗАГРУЗИТЬ ПЛАН")
            self.log("ВЫПОЛНИТЬ без плана: отказ")
            return
        if self.tbl.vals.get("approve") != "да":
            self.status.set("нет согласия — шаги не начаты")
            self.log("ВЫПОЛНИТЬ без согласия: шаги НЕ начались (RC 3)")
            return
        dry = self.tbl.vals.get("dry_run") == "да"
        writes = sum(1 for s in self.plan.get("steps", []) if s.get("risk") == "write")
        if not dry and not messagebox.askyesno(
                "Исполнение плана",
                "Писать будет в %d моделей. Цель - из плана, не боевая.\nПродолжить?"
                % writes):
            self.status.set("отменено человеком")
            self.log("исполнение отменено человеком")
            return
        R.STOP["flag"] = False
        self.status.set("выполняю…")
        t0 = time.time()
        plan = self.plan

        def work():
            return R.run_plan(plan, approve=True, dry_run=dry, on_log=self.log)

        def done(res):
            self.res = res
            self.status.set("готово за %.2f с: RC %s — %s"
                            % (time.time() - t0, res.get("rc"), res.get("detail", "")))
            self.log("RC %s: %s" % (res.get("rc"), res.get("detail", "")))
            if res.get("results"):
                self.log("отчёт: %s" % R.write_report(res, plan))

        U.run_in_thread(self.root, work, on_done=done,
                        on_error=lambda e: self.status.set("ошибка исполнения"),
                        log=self.log)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    r = U.make_root("Ж — ПЛАНЫ ЗАДАЧ %s" % APP_VERSION, "1180x720",
                    minsize=(1000, 640), tool_dir=_HERE)
    App(r)
    r.mainloop()
