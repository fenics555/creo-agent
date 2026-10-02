# -*- coding: utf-8 -*-
"""config_audit — ОКНО проверки путей config.pro.

Запуск: config_audit_gui.bat. Класс Р: Creo и агент не нужны, только чтение.
Движок — `config_audit.py` в этой же папке (функция audit).
"""
import csv
import json
import os
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config_audit as eng  # noqa: E402

# Настройки окна — в data\ рядом с остальными (манифест п.19). До 02.10.2026 окно их не имело
# вовсе: выбранный config.pro терялся при закрытии, это был самый частый сценарий — открыть,
# посмотреть, закрыть, снова выбирать.
SETTINGS = Path(r"D:\AI\tools\agent\data\config_audit_settings.json")
# Известные места дома. Живая проверка 02.10.2026: START-Config НЕ существует на диске —
# держать его в списке значило предлагать пользователю заведомо мёртвый путь.
KNOWN = [
    r"Z:\PTC\CREO-START\START-STD\config.pro",
    r"D:\PTC\CREO-LOCAL-SETUP\CREO-LOCAL-START\config.pro",
]
DEFAULTS = {"last_config": KNOWN[0]}
# Подстановки переменных Creo живут в настройках (манифест п.19: одна база — одно место).
# Если блока нет, движок сам найдёт установку на диске (D:\PTC\CREO*\Creo *\Parametric).
CREO_VARS = {
    "$PRO_DIRECTORY": r"D:\PTC\CREO12\Creo 12.4.2.0\Parametric",
    "$CREO_COMMON_FILES": r"D:\PTC\CREO12\Creo 12.4.2.0\Common Files",
    "$PROSTD": r"Z:\PTC\CREO-START\НАСТРОЙКИ",
}


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("V1 — ПУТИ CONFIG.PRO — что есть, чего нет")
        self.root.geometry("1020x620")
        self.res = None
        self._pending = []
        self.st = self.load_settings()
        self.build()

    def load_settings(self):
        d = dict(DEFAULTS)
        try:
            if SETTINGS.exists():
                d.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
        except Exception as e:
            self._pending.append("настройки не прочитаны (%s) — беру значения по умолчанию" % e)
        return d

    def save_settings(self):
        try:
            self.st["creo_vars"] = dict(CREO_VARS)
            SETTINGS.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS.write_text(json.dumps(self.st, ensure_ascii=False, indent=1),
                                encoding="utf-8")
        except Exception as e:
            self._pending.append("настройки не сохранены: %s" % e)

    def build(self):
        top = tk.LabelFrame(self.root, text="НАСТРОЙКИ", padx=10, pady=8)
        top.pack(fill="x", padx=10, pady=8)

        tk.Label(top, text="Файл config.pro:").grid(row=0, column=0, sticky="w")
        self.var_path = tk.StringVar(value=str(self.st.get("last_config") or eng.CONFIG))
        self.combo = ttk.Combobox(top, textvariable=self.var_path, values=KNOWN, width=80)
        self.combo.grid(row=0, column=1, padx=6, pady=4)
        tk.Button(top, text="Обзор…", command=self.browse).grid(row=0, column=2)
        tk.Label(top, text="Проверяются пути вида `C:\\…`, `\\\\сервер\\…`, `$PRO_DIRECTORY`, "
                           "`$CREO_COMMON_FILES`, `$PROSTD`; у Creo-файлов учитывается версия (`.prt` → `.prt.1`)",
                 fg="#555").grid(row=1, column=0, columnspan=3, sticky="w")

        btns = tk.Frame(self.root)
        btns.pack(fill="x", padx=10, pady=(0, 6))
        tk.Button(btns, text="ПРОВЕРИТЬ", width=18, command=self.run).pack(side="left", padx=4)
        tk.Button(btns, text="Открыть файл", command=self.open_file).pack(side="left", padx=4)
        tk.Button(btns, text="Открыть папку", command=lambda: self.open_dir(os.path.dirname(self.var_path.get()))).pack(side="left", padx=4)
        tk.Button(btns, text="Сохранить отчёт (CSV)", command=self.save_csv).pack(side="left", padx=4)
        tk.Button(btns, text="README", command=self.show_readme).pack(side="left", padx=4)
        tk.Button(btns, text="Папка отчётов", command=lambda: self.open_dir(eng.REPORT_DIR)).pack(side="left", padx=4)
        tk.Button(btns, text="Папка логов", command=lambda: self.open_dir(eng.LOG_DIR)).pack(side="left", padx=4)

        self.sum = tk.Label(self.root, text="готов", anchor="w", bg="#fff1c7", padx=8, pady=4)
        self.sum.pack(fill="x", padx=10)

        cols = ("line", "opt", "value", "path")
        heads = ("Строка", "Настройка", "Как записано в конфиге", "Путь на диске (НЕТ)")
        self.tree = ttk.Treeview(self.root, columns=cols, show="headings", height=15)
        for c, h, w in zip(cols, heads, (70, 210, 350, 380)):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w)
        self.tree.pack(fill="both", expand=True, padx=10, pady=8)

        self.info = tk.Text(self.root, height=6, font=("Consolas", 9), bg="#f8f9fa")
        self.info.pack(fill="x", padx=10, pady=(0, 8))
        for s in self._pending:        # сообщения, накопленные до создания виджета лога
            self.log(s)
        self._pending = []
        self.log("настройки: %s" % SETTINGS)
        self.log("конфиг: %s" % self.var_path.get())
        self.log("журнал: %s | отчёты: %s" % (eng.LOG_DIR, eng.REPORT_DIR))

    def log(self, s):
        self.info.insert("end", s + "\n")
        self.info.see("end")

    def open_dir(self, p):
        try:
            if p and os.path.isdir(p):
                os.startfile(p)
        except Exception as e:
            messagebox.showwarning("Не открыть", "%s\n%s" % (p, e))

    def open_file(self):
        try:
            if os.path.exists(self.var_path.get()):
                os.startfile(self.var_path.get())
        except Exception as e:
            messagebox.showwarning("Не открыть", str(e))

    def browse(self):
        p = filedialog.askopenfilename(filetypes=[("config.pro", "*.pro"), ("Все файлы", "*.*")])
        if p:
            self.var_path.set(p)
            self.st["last_config"] = p
            self.save_settings()   # выбранный конфиг переживает перезапуск окна

    def run(self):
        p = self.var_path.get()
        self.st["last_config"] = p
        self.save_settings()
        if not os.path.exists(p):
            return messagebox.showwarning("Нет файла", p)
        _t0 = time.time()
        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            self.res = eng.audit(p)
        except Exception as e:
            return messagebox.showerror("Ошибка чтения", str(e))
        for pr in self.res["problems"]:
            self.tree.insert("", "end", values=(pr["line"], pr["opt"], pr["value"], pr["path"]))
        _secs = time.time() - _t0
        self.sum.config(text="путей проверено: %d | НЕТ на диске: %d | за %.2f с"
                             % (self.res["total"], self.res["missing"], _secs))
        self.log("файл: %s (%.2f с)" % (p, _secs))
        if self.res["missing"]:
            self.log("ЧТО ДЕЛАТЬ: файла нет → либо положить файл по этому пути, либо закомментировать "
                     "настройку (`!`) и рядом записать причину.")
        else:
            self.log("все пути на месте.")
        # тот же журнал и отчёт, что у CLI (закон трёх рук: одна база — один лог, один отчёт)
        try:
            rep = eng.write_report(self.res, p, _secs, quiet=True)
            self.log("отчёт: %s" % rep)
            self.log("журнал прогона: %s" % os.path.join(eng.LOG_DIR, "run_*.txt"))
        except Exception as e:
            self.log("отчёт не записан: %s" % e)

    def save_csv(self):
        if not self.res:
            return messagebox.showinfo("Нечего сохранять", "Сначала проверка")
        p = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="config_пути.csv")
        if not p:
            return
        try:
            with open(p, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["строка", "настройка", "в конфиге", "путь на диске"])
                for pr in self.res["problems"]:
                    w.writerow([pr["line"], pr["opt"], pr["value"], pr["path"]])
            self.log("отчёт сохранён: %s" % p)
        except Exception as e:
            messagebox.showerror("Не сохранить", str(e))

    def show_readme(self):
        p = Path(__file__).resolve().parent / "README.md"
        try:
            text = p.read_text(encoding="utf-8")
        except Exception as e:
            self.log("README не прочитан: %s" % e)
            return
        self.log("=" * 100)
        self.log("README: %s" % p)
        self.log("=" * 100)
        for line in text.splitlines():
            self.log(line)
        self.log("=" * 100)
        self.log("конец README")


if __name__ == "__main__":
    r = tk.Tk()
    App(r)
    r.mainloop()