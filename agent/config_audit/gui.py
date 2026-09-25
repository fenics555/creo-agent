# -*- coding: utf-8 -*-
"""config_audit — ОКНО проверки путей config.pro.

Запуск: config_audit_gui.bat. Класс Р: Creo и агент не нужны, только чтение.
Движок — `config_audit.py` в этой же папке (функция audit).
"""
import csv
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config_audit as eng  # noqa: E402

KNOWN = [
    r"Z:\PTC\CREO-START\START-STD\config.pro",
    r"Z:\PTC\CREO-START\START-Config\config.pro",
    r"D:\PTC\CREO-LOCAL-SETUP\CREO-LOCAL-START\config.pro",
]


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("V1 — ПУТИ CONFIG.PRO — что есть, чего нет")
        self.root.geometry("1020x620")
        self.res = None
        self.build()

    def build(self):
        top = tk.LabelFrame(self.root, text="НАСТРОЙКИ", padx=10, pady=8)
        top.pack(fill="x", padx=10, pady=8)

        tk.Label(top, text="Файл config.pro:").grid(row=0, column=0, sticky="w")
        self.var_path = tk.StringVar(value=str(eng.CONFIG))
        self.combo = ttk.Combobox(top, textvariable=self.var_path, values=KNOWN, width=80)
        self.combo.grid(row=0, column=1, padx=6, pady=4)
        tk.Button(top, text="Обзор…", command=self.browse).grid(row=0, column=2)
        tk.Label(top, text="Проверяются пути вида `C:\\…`, `\\\\сервер\\…`, `$PRO_DIRECTORY`, "
                           "`$CREO_COMMON_FILES`, `$PROSTD`; у Creo-файлов учитывается версия (`.prt` → `.prt.1`)",
                 fg="#555").grid(row=1, column=0, columnspan=3, sticky="w")

        btns = tk.Frame(self.root)
        btns.pack(fill="x", padx=10)
        tk.Button(btns, text="ПРОВЕРИТЬ", width=18, command=self.run).pack(side="left", padx=4)
        tk.Button(btns, text="Открыть файл", command=self.open_file).pack(side="left", padx=4)
        tk.Button(btns, text="Открыть папку", command=lambda: self.open_dir(os.path.dirname(self.var_path.get()))).pack(side="left", padx=4)
        tk.Button(btns, text="Сохранить отчёт (CSV)", command=self.save_csv).pack(side="left", padx=4)

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

    def run(self):
        p = self.var_path.get()
        if not os.path.exists(p):
            return messagebox.showwarning("Нет файла", p)
        for i in self.tree.get_children():
            self.tree.delete(i)
        try:
            self.res = eng.audit(p)
        except Exception as e:
            return messagebox.showerror("Ошибка чтения", str(e))
        for pr in self.res["problems"]:
            self.tree.insert("", "end", values=(pr["line"], pr["opt"], pr["value"], pr["path"]))
        self.sum.config(text="путей проверено: %d | НЕТ на диске: %d"
                             % (self.res["total"], self.res["missing"]))
        self.log("файл: %s" % p)
        if self.res["missing"]:
            self.log("ЧТО ДЕЛАТЬ: файла нет → либо положить файл по этому пути, либо закомментировать "
                     "настройку (`!`) и рядом записать причину.")
        else:
            self.log("все пути на месте.")

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


if __name__ == "__main__":
    r = tk.Tk()
    App(r)
    r.mainloop()