# -*- coding: utf-8 -*-
"""excel — ОКНО просмотра спецификации XLSX (что реально записано в файле).

Запуск: excel_gui.bat. Класс Р: Creo и агент не нужны, только чтение.
Разбор делает `excel_import.read_specification_xlsx` из этой же папки.
Запись XLSX (сборка спецификации) делает агент (`spec_tools.py`, `excel_export.py`) — в окне её нет,
чтобы не выдумывать данные: окно ЧИТАЕТ и показывает.
"""
import os
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import excel_import as imp  # noqa: E402

SETTINGS = Path(__file__).resolve().parent / "gui_settings.json"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("СПЕЦИФИКАЦИЯ XLSX — просмотр")
        self.root.geometry("1080x640")
        self.rows = []
        self.build()

    def build(self):
        top = tk.LabelFrame(self.root, text="НАСТРОЙКИ", padx=10, pady=8)
        top.pack(fill="x", padx=10, pady=8)

        tk.Label(top, text="Файл спецификации:").grid(row=0, column=0, sticky="w")
        self.var_path = tk.StringVar(value="")
        tk.Entry(top, textvariable=self.var_path, width=80).grid(row=0, column=1, padx=6)
        tk.Button(top, text="Обзор…", command=self.browse).grid(row=0, column=2)
        tk.Label(top, text="Читаются столбцы «Обозначение» и «Наименование»; разделы — по названиям ГОСТ.",
                 fg="#555").grid(row=1, column=0, columnspan=3, sticky="w")

        btns = tk.Frame(self.root)
        btns.pack(fill="x", padx=10)
        tk.Button(btns, text="ПОКАЗАТЬ", width=14, command=self.run).pack(side="left", padx=4)
        tk.Button(btns, text="Открыть файл", command=self.open_file).pack(side="left", padx=4)
        tk.Button(btns, text="Открыть папку", command=lambda: self.open_dir(os.path.dirname(self.var_path.get()))).pack(side="left", padx=4)

        self.sum = tk.Label(self.root, text="готов", anchor="w", bg="#fff1c7", padx=8, pady=4)
        self.sum.pack(fill="x", padx=10)

        self.tree = ttk.Treeview(self.root, show="headings", height=16)
        self.tree.pack(fill="both", expand=True, padx=10, pady=8)
        self.tree.bind("<Double-1>", lambda e: self.open_file())

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
            if self.var_path.get() and os.path.exists(self.var_path.get()):
                os.startfile(self.var_path.get())
        except Exception as e:
            messagebox.showwarning("Не открыть", str(e))

    def browse(self):
        p = filedialog.askopenfilename(filetypes=[("Excel", "*.xlsx"), ("Все файлы", "*.*")])
        if p:
            self.var_path.set(p)
            self.run()

    def run(self):
        p = self.var_path.get()
        if not os.path.exists(p):
            return messagebox.showwarning("Нет файла", p)
        try:
            data = open(p, "rb").read()
            sections, rows = imp.read_specification_xlsx(data)
        except Exception as e:
            return messagebox.showerror("Не прочитать спецификацию", str(e))
        self.rows = rows
        keys = []
        for r in rows:
            for k in r.keys():
                if k not in keys:
                    keys.append(k)
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = keys
        for k in keys:
            self.tree.heading(k, text=k)
            self.tree.column(k, width=140, anchor="w")
        for r in rows:
            self.tree.insert("", "end", values=[r.get(k, "") for k in keys])
        self.sum.config(text="файл: %s | разделов: %d | строк: %d | колонок: %d"
                             % (os.path.basename(p), len(sections), len(rows), len(keys)))
        self.log("разделы: %s" % ", ".join(sections))
        self.log("строк: %d; колонки: %s" % (len(rows), ", ".join(keys)))


if __name__ == "__main__":
    r = tk.Tk()
    App(r)
    r.mainloop()