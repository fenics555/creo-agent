# -*- coding: utf-8 -*-
"""skills_check — ОКНО проверки скиллов (шапки, дубли имён, «краши»).

ВЕРСИЯ ОКНА: V2 (04.10.2026 — перевод на каркас ui_common).
Запуск: skills_check_gui.bat. Класс Р: Creo и агент не нужны.
Движок — `skills_check.py` рядом: он проверяет скиллы репозитория, сравнивает с эталоном
(`data\\skills_check_baseline.txt`) и пишет отчёт `D:\\AI\\log\\skills_check\\skills_check_report.txt`.
Окно только запускает его и показывает вывод — так поведение проверки остаётся ровно тем же.
"""
import os
import subprocess
import time
import sys
import threading
import tkinter as tk
from pathlib import Path

HERE = Path(__file__).resolve().parent
AGENT = HERE.parent
sys.path.insert(0, str(AGENT))
import ui_common as U  # noqa: E402  (общий каркас окон дома)

ENGINE = HERE / "skills_check.py"
REPORT = Path(r"D:\AI\log\skills_check\skills_check_report.txt")
TITLE = "ПРОВЕРКА СКИЛЛОВ (skills_check)"


class App:
    def __init__(self, root=None):
        self.root = root or U.make_root("V2 — " + TITLE, "1020x640", minsize=(900, 560))
        self.proc = None
        self.build()

    def build(self):
        # --- каркас: действие СЛЕВА, справка СПРАВА (константа 5) ---
        U.head(self.root, TITLE,
               "Проверяет шапки скиллов, дубли имён и «краши» репозитория. "
               "Класс Р: Creo и агент не нужны. Отчёт: %s" % REPORT)
        left, right = U.split_result_left(self.root, right_width=360)

        box, btns = U.actions(left,
                              primary=(("ПРОВЕРИТЬ", self.run),),
                              secondary=(("СТОП", self.stop),
                                         ("Открыть отчёт", self.open_report),
                                         ("Обновить эталон", self.rebaseline)))
        self.b_run, self.b_stop = btns[0], btns[1]
        self.b_stop.config(state="disabled")
        self.sum_var, self.set_summary = U.summary(left)
        # Кнопка README — каркасная. Подпись сокращена: полная — в подсказке и в самом README.
        U.readme_button(box, str(HERE), self.log)

        # --- вывод проверки: моноширинный (признак канона), справа во всю высоту ---
        self.info, self._log = U.log_view(right, height=18, title="ВЫВОД ПРОВЕРКИ")

    def log(self, s):
        self._log(s)

    def open_report(self):
        try:
            if REPORT.exists():
                os.startfile(str(REPORT))
            else:
                self.log("отчёта ещё нет — сначала проверка\n")
        except Exception as e:
            self.log("не открыть: %s\n" % e)

    def rebaseline(self):
        base = Path(r"D:\AI\tools\agent\data\skills_check_baseline.txt")
        if not base.exists():
            return self.log("эталона ещё нет — он создастся сам при первом прогоне\n")
        if not tk.messagebox.askyesno("Обновить эталон",
                                      "Текущие нарушения станут нормой.\n"
                                      "Делать это можно ТОЛЬКО после того, как нарушения разобраны.\n\nПродолжить?"):
            return
        try:
            bak = base.with_suffix(".txt." + __import__("datetime").datetime.now().strftime("%Y-%m-%d_%H%M") + ".bak")
            base.replace(bak)
            self.log("эталон снят, старый сохранён: %s\nпри следующем прогоне эталон создастся заново\n" % bak.name)
        except Exception as e:
            self.log("не обновить эталон: %s\n" % e)

    def run(self):
        self.info.winfo_children()[0].delete("1.0", "end")
        self.log("запускаю: python skills_check.py\n\n")
        self.b_run.config(state="disabled")
        self.b_stop.config(state="normal")
        self.sum_var.set("идёт проверка…")
        try:
            self.proc = subprocess.Popen([sys.executable, str(ENGINE)], cwd=str(HERE),
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, encoding="utf-8", errors="replace", bufsize=1)
        except Exception as e:
            self.log("не запустить: %s\n" % e)
            return self.done()

        def pump():
            _t0 = time.time()
            for line in self.proc.stdout:
                self.root.after(0, self.log, line)
            self.proc.wait()
            self.root.after(0, self.log, "\n=== код возврата: %s за %.1f с ===\n"
                            % (self.proc.returncode, time.time() - _t0))
            self.root.after(0, self.done)

        threading.Thread(target=pump, daemon=True).start()

    def stop(self):
        try:
            if self.proc:
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)], capture_output=True)
                self.log("\nостановлено по кнопке СТОП\n")
        except Exception as e:
            self.log("не остановить: %s\n" % e)
        self.done()

    def done(self):
        # 03.10.2026: эти две строки стояли ОШИБКОЙ внутри show_readme() — из-за этого после
        # проверки кнопка СТОП не гасла, а строка состояния «готов» обновлялась только
        # кнопкой README. Теперь состояние окна приводит сам прогон.
        self.proc = None
        self.b_run.config(state="normal")
        self.b_stop.config(state="disabled")
        self.sum_var.set("готов · отчёт: %s" % REPORT)

# Метод show_readme удалён 04.10.2026: кнопку README даёт каркас (U.readme_button),
# поэтому собственный дубль остался бы мёртвым кодом.


if __name__ == "__main__":
    # Окно создаёт САМ каркас (make_root) — раньше здесь создавался tk.Tk() вручную.
    App().root.mainloop()