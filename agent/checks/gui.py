# -*- coding: utf-8 -*-
"""checks — ОКНО ЕДИНОГО ПРОГОНА ПРОВЕРОК (каркас ui_common, волна 5).

Слева — проверки с иконками статуса, справа — что нашла каждая. Сводка с ПРОЦЕНТОМ
соответствия (константа 4 волны 1). Прогон уходит в поток — окно не замирает.
Запуск: checks_gui.bat
"""
import io
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import tkinter as tk                       # noqa: E402
from tkinter import messagebox            # noqa: E402
import checks as CH                        # noqa: E402
import ui_common as U                      # noqa: E402

TREE = ("icon", "id", "scope", "detail")


class App:
    def __init__(self, root=None):
        self.root = root or U.make_root("V1 — ПРОВЕРКИ ДОМА (прогон)", "1120x700",
                                        minsize=(950, 600))
        self.root.minsize(950, 600)
        self.res = None
        self.build()

    def build(self):
        U.head(self.root, "Единый прогон проверок дома",
               "Все проверки — один отчёт со сводкой и процентом соответствия. "
               "Каждая проверка продолжает работать и отдельно, своим .bat.")
        left, right = U.split_result_left(self.root, right_width=430)

        U.actions(left, primary=(("ПРОГНАТЬ ВСЕ", self.run),),
                  secondary=(("Открыть отчёт", self.open_report),))
        self.tree = U.result_tree(left, ("icon", "id", "scope", "detail"),
                                  ("", "Проверка", "Область", "Что показала"),
                                  [60, 180, 130, 420])
        self.sum_var, self.set_summary = U.summary(left)

        nb, pages = U.tabs(right, ["Проблемы", "Реестр", "О прогоне"])
        self.prob = tk.Text(pages[0], height=16, font=("Consolas", 9), wrap="word",
                            bg="#101418", fg="#d8e2e8", insertbackground="#d8e2e8")
        self.prob.pack(fill="both", expand=True)
        self.prob.insert("1.0", "Здесь будут найденные проблемы.\nНажми «ПРОГНАТЬ ВСЕ».")

        tk.Label(pages[1], text=CH.registry(), bg=U.BG, fg=U.MUTED, font=("Consolas", 9),
                 justify="left", anchor="nw").pack(fill="both", expand=True, padx=10, pady=8)

        about = pages[2]
        tk.Label(about, text=("Движок: checks.py\nОтчёты: %s\n\n"
                              "Падение одной проверки не роняет прогон — она даёт строку "
                              "«провал» в сводке.\nКаждая проверка продолжает работать "
                              "и по-своему (hol_check.bat, config_audit.bat и т.д.)."
                              % CH.REPORT_DIR),
                 bg=U.BG, fg=U.MUTED, font=("Segoe UI", 9), justify="left",
                 anchor="nw").pack(fill="both", expand=True, padx=10, pady=8)
        U.readme_button(about, AGENT_DOCS, self.log)

        self._log_box, self._log_write = U.log_view(self.root, height=6)
        self.status = U.statusbar(self.root)
        self.log("проверок в реестре: %d — жми «ПРОГНАТЬ ВСЕ»" % len(CH.CHECKS))

    def log(self, s):
        try:
            self._log_write(str(s))
        except Exception:
            pass

    def open_report(self):
        import os
        try:
            os.startfile(str(CH.REPORT_DIR))
        except Exception as e:
            messagebox.showwarning("Не открыть", str(e))

    def run(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.prob.delete("1.0", "end")
        self.status.set("прогоняю все проверки…")

        def work():
            return CH.checks_run(as_json=True)

        U.run_in_thread(self.root, work, on_done=self.show, log=self.log)

    def show(self, res):
        self.res = res
        for r in res["rows"]:
            self.tree.insert("", "end",
                             values=(U.ICON_OK if r["ok"] else U.ICON_ERR,
                                     r["id"], r["scope"], r["detail"]),
                             tags=("ok",) if r["ok"] else ("fail",))
        pct = self.set_summary(res["checks"], res["passed"], res["failed_checks"],
                               label="объектов: %d" % res["items"])
        self.status.set("готово за %.2f с: успешно %d из %d (%s %%)"
                        % (res["secs"], res["passed"], res["checks"],
                           round(pct) if pct is not None else "н/д"))
        probs = [(r["id"], it) for r in res["rows"] for it in r["items"]
                 if it["verdict"] != "ok"]
        self.prob.insert("1.0", "Проблем: %d\n\n" % len(probs)
                         + "\n".join("%s · %s %s" % (cid, it["icon"], it["what"])
                                     for cid, it in probs)
                         if probs else "Проблем нет — все проверки зелёные.")
        try:
            p = CH.write_report(res)
            self.log("отчёт: %s" % p)
        except Exception as e:
            self.log("отчёт не записан: %s" % e)


AGENT_DOCS = _HERE / "checks_README.md"

if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    r = U.make_root("V1 — ПРОВЕРКИ ДОМА (прогон)", "1120x700", minsize=(950, 600))
    App(r)
    r.mainloop()