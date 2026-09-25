# -*- coding: utf-8 -*-
"""make_lst — ОКНО сборки файла ограничений параметров (list.lst).

Запуск: make_lst_gui.bat. Класс Р: Creo и агент не нужны.
Движок — `make_lst.py` в этой же папке (build / write_file / check_against_refs).
"""
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_lst as eng  # noqa: E402


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("V1 — ОГРАНИЧЕНИЯ ПАРАМЕТРОВ (list.lst)")
        self.root.geometry("980x660")
        self.build()

    def build(self):
        top = tk.LabelFrame(self.root, text="НАСТРОЙКИ", padx=10, pady=8)
        top.pack(fill="x", padx=10, pady=8)

        tk.Label(top, text="Файл ограничений:").grid(row=0, column=0, sticky="w")
        self.var_target = tk.StringVar(value=eng.TARGET)
        tk.Entry(top, textvariable=self.var_target, width=78).grid(row=0, column=1, padx=6)
        tk.Button(top, text="Обзор…", command=self.browse_target).grid(row=0, column=2)

        tk.Label(top, text="Отчёт чесалки для сверки (не обязательно):").grid(row=1, column=0, sticky="w", pady=4)
        self.var_refs = tk.StringVar(value="")
        tk.Entry(top, textvariable=self.var_refs, width=78).grid(row=1, column=1, padx=6)
        tk.Button(top, text="Обзор…", command=self.browse_refs).grid(row=1, column=2)
        tk.Label(top, text="refs.txt делает `creo_comb.bat refs <папка>` — по нему видно, "
                           "что значения параметров совпадают с шаблонами", fg="#555").grid(
            row=2, column=0, columnspan=3, sticky="w")

        btns = tk.Frame(self.root)
        btns.pack(fill="x", padx=10)
        tk.Button(btns, text="ПОКАЗАТЬ (ничего не пишем)", width=30, command=self.preview).pack(side="left", padx=4)
        self.b_write = tk.Button(btns, text="ЗАПИСАТЬ ФАЙЛ (с бэкапом)", width=26, command=self.write)
        self.b_write.pack(side="left", padx=4)
        tk.Button(btns, text="Открыть папку файла", command=lambda: self.open_dir(os.path.dirname(self.var_target.get()))).pack(side="left", padx=4)
        tk.Button(btns, text="Показать текущий файл", command=self.show_current).pack(side="left", padx=4)

        tk.Label(self.root, text="Что будет записано / журнал", anchor="w").pack(fill="x", padx=12, pady=(8, 0))
        self.txt = tk.Text(self.root, font=("Consolas", 9), bg="#fbfbfb")
        self.txt.pack(fill="both", expand=True, padx=10, pady=6)

        self.sum = tk.Label(self.root, text="готов", anchor="w", bg="#fff1c7", padx=8, pady=4)
        self.sum.pack(fill="x", padx=10, pady=(0, 8))

    # ---------- вспомогательное ----------
    def log(self, s):
        self.txt.insert("end", s + "\n")
        self.txt.see("end")

    def clear(self):
        self.txt.delete("1.0", "end")

    def open_dir(self, p):
        try:
            if p and os.path.isdir(p):
                os.startfile(p)
        except Exception as e:
            messagebox.showwarning("Не открыть", "%s\n%s" % (p, e))

    def browse_target(self):
        p = filedialog.asksaveasfilename(defaultextension=".lst", initialfile="list.lst")
        if p:
            self.var_target.set(p)

    def browse_refs(self):
        p = filedialog.askopenfilename(filetypes=[("Отчёт чесалки", "*.txt"), ("Все файлы", "*.*")])
        if p:
            self.var_refs.set(p)

    def preview(self):
        self.clear()
        self.log("цель: %s" % self.var_target.get())
        if self.var_refs.get():
            eng.check_against_refs(self.var_refs.get(), self.log)
        self.log("")
        self.log(eng.build())
        self.sum.config(text="показано содержимое (на диск ничего не записано)")

    def show_current(self):
        self.clear()
        p = self.var_target.get()
        if not os.path.exists(p):
            self.log("файла ещё нет: %s" % p)
            return
        try:
            data = open(p, "rb").read()
            self.log("текущий файл: %s (%d байт, cp1251)" % (p, len(data)))
            self.log("")
            self.log(data.decode("cp1251"))
        except Exception as e:
            self.log("не прочитать: %s" % e)

    def write(self):
        p = self.var_target.get()
        if not messagebox.askyesno("Подтверждение",
                                   "Записать файл ограничений?\n%s\n\nПрежний файл уедет в _pre рядом."
                                   % p):
            return
        self.clear()
        try:
            eng.write_file(p, eng.build(), self.log)
            self.sum.config(text="файл записан: %s" % p)
        except Exception as e:
            messagebox.showerror("Ошибка записи", str(e))


if __name__ == "__main__":
    r = tk.Tk()
    App(r)
    r.mainloop()