# -*- coding: utf-8 -*-
"""skills_check — ОКНО проверки скиллов (шапки, дубли имён, «краши»).

Запуск: skills_check_gui.bat. Класс Р: Creo и агент не нужны.
Движок — `skills_check.py` рядом: он проверяет скиллы репозитория, сравнивает с эталоном
(`data\\skills_check_baseline.txt`) и пишет отчёт `D:\\AI\\log\\skills_check\\skills_check_report.txt`.
Окно только запускает его и показывает вывод — так поведение проверки остаётся ровно тем же.
"""
import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path

HERE = Path(__file__).resolve().parent
ENGINE = HERE / "skills_check.py"
REPORT = Path(r"D:\AI\log\skills_check\skills_check_report.txt")


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("V1 — ПРОВЕРКА СКИЛЛОВ (skills_check)")
        self.root.geometry("980x600")
        self.proc = None
        self.build()

    def build(self):
        tk.Label(self.root, text="Проверяются шапки скиллов и «краши» репозитория; отчёт — "
                                 "D:\\AI\\log\\skills_check\\skills_check_report.txt",
                 anchor="w", fg="#555").pack(fill="x", padx=10, pady=(10, 4))

        btns = tk.Frame(self.root)
        btns.pack(fill="x", padx=10)
        self.b_run = tk.Button(btns, text="ПРОВЕРИТЬ", width=16, command=self.run)
        self.b_run.pack(side="left", padx=4)
        self.b_stop = tk.Button(btns, text="СТОП", width=10, state="disabled", command=self.stop)
        self.b_stop.pack(side="left", padx=4)
        tk.Button(btns, text="Открыть отчёт", command=self.open_report).pack(side="left", padx=4)
        tk.Button(btns, text="Обновить эталон (после разбора нарушений)",
                  command=self.rebaseline).pack(side="left", padx=4)

        self.sum = tk.Label(self.root, text="готов", anchor="w", bg="#fff1c7", padx=8, pady=4)
        self.sum.pack(fill="x", padx=10, pady=(6, 0))

        self.info = tk.Text(self.root, font=("Consolas", 9), bg="#f8f9fa")
        self.info.pack(fill="both", expand=True, padx=10, pady=8)

    def log(self, s):
        self.info.insert("end", s)
        self.info.see("end")

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
        self.info.delete("1.0", "end")
        self.log("запускаю: python skills_check.py\n\n")
        self.b_run.config(state="disabled")
        self.b_stop.config(state="normal")
        try:
            self.proc = subprocess.Popen([sys.executable, str(ENGINE)], cwd=str(HERE),
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, encoding="utf-8", errors="replace", bufsize=1)
        except Exception as e:
            self.log("не запустить: %s\n" % e)
            return self.done()

        def pump():
            for line in self.proc.stdout:
                self.root.after(0, self.log, line)
            self.proc.wait()
            self.root.after(0, self.log, "\n=== код возврата: %s ===\n" % self.proc.returncode)
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
        self.proc = None
        self.b_run.config(state="normal")
        self.b_stop.config(state="disabled")
        self.sum.config(text="готов · отчёт: %s" % REPORT)


if __name__ == "__main__":
    r = tk.Tk()
    App(r)
    r.mainloop()