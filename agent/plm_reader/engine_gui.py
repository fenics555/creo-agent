# -*- coding: utf-8 -*-
r"""plm_tree — ОКНО ПЛМ (V1): паспорт, дерево производства, входимость, изменения.

База — `plm_tree.db` рядом с инструментом. Creo не нужен.
"""
import json
import os
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, simpledialog, ttk

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine as eng  # noqa: E402

VERSION = "V1"
SETTINGS = HERE / "gui_settings.json"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("PLM-ДЕРЕВО %s — ГОТОВАЯ БАЗА: дерево · входимость · изменения" % VERSION)
        self.root.geometry("1140x720")
        self.build()
        self.base_info()

    def base_info(self):
        """Одна строка о ГОТОВОЙ базе. Здесь НИЧЕГО не сканируется и не проверяется — скан в главном окне."""
        s = eng.summary()
        self.sum.config(text="ГОТОВАЯ БАЗА: файлов %d · моделей %d · связей %d · папок %d · изменений %d"
                        % (s.get("snapshots", 0), s.get("models", 0), s.get("links", 0),
                           s.get("folders", 0), s.get("changes", 0)))

    def log(self, s):
        self.txt.insert("end", s + "\n")
        self.txt.see("end")

    def cap(self, fn, *a):
        import contextlib
        import io
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                fn(*a)
        except Exception as e:
            self.log("ОШИБКА: %s" % e)
            return
        self.log(buf.getvalue().rstrip())

    def build(self):
        tk.Label(self.root, text="БАЗА (только чтение): %s" % eng.DB, fg="#555").pack(
            anchor="w", padx=12, pady=(10, 2))


        bar = tk.Frame(self.root)
        bar.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(bar, text="Модель:").pack(side="left")
        self.var_model = tk.StringVar(value="")
        tk.Entry(bar, textvariable=self.var_model, width=28).pack(side="left", padx=6)
        tk.Button(bar, text="ДЕРЕВО", width=12,
                  command=lambda: self.cap(eng.do_tree, self.var_model.get().strip(), 4)).pack(side="left", padx=4)
        tk.Button(bar, text="ГДЕ ИСПОЛЬЗУЕТСЯ", width=17, command=self.where).pack(side="left", padx=4)
        tk.Button(bar, text="ИЗМЕНЕНИЯ", width=11,
                  command=lambda: self.cap(eng.do_changes, 40)).pack(side="left", padx=4)
        tk.Button(bar, text="README", width=9, command=self.show_readme).pack(side="left", padx=4)
        tk.Label(self.root, text="Скан и проверка актуальности — в главном окне PLM Reader; здесь только чтение базы.",
                 fg="#555").pack(anchor="w", padx=12, pady=(0, 4))


        data = tk.Frame(self.root)
        data.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.sum = tk.Label(data, text="готовая база", anchor="w", bg="#fff1c7",
                            padx=8, pady=4, justify="left")
        self.sum.pack(fill="x")
        self.txt = tk.Text(data, font=("Consolas", 9), bg="#fbfbfb")
        self.txt.pack(fill="both", expand=True, pady=(4, 0))
        self.root.bind("<Configure>", lambda e: self.sum.config(
            wraplength=max(240, self.root.winfo_width() - 60)))   # текст не пропадает в узком окне

    def where(self):
        m = self.var_model.get().strip() or simpledialog.askstring("Модель", "Имя модели:", parent=self.root)
        if m:
            self.cap(eng.do_where, m)

    def show_readme(self):
        try:
            text = (HERE / "README.md").read_text(encoding="utf-8")
        except Exception as e:
            self.log("README не прочитан: %s" % e)
            return
        self.log("=" * 100)
        for line in text.splitlines():
            self.log(line)
        self.log("=" * 100)


def main():
    r = tk.Tk()
    App(r)
    r.mainloop()


if __name__ == "__main__":
    main()
