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
        """Список моделей + состав базы (без обхода диска)."""
        self.fill_list()

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
        tk.Label(bar, text="Фильтр:").pack(side="left")
        self.var_model = tk.StringVar(value="")
        e = tk.Entry(bar, textvariable=self.var_model, width=22)
        e.pack(side="left", padx=6)
        e.bind("<KeyRelease>", lambda ev: self.fill_list())
        tk.Button(bar, text="ДЕРЕВО", width=12, command=self.tree).pack(side="left", padx=3)
        tk.Button(bar, text="ГДЕ ИСПОЛЬЗУЕТСЯ", width=17, command=self.where).pack(side="left", padx=3)
        tk.Button(bar, text="ИЗМЕНЕНИЯ", width=11, command=self.changes).pack(side="left", padx=3)
        tk.Button(bar, text="README", width=9, command=self.show_readme).pack(side="left", padx=3)
        tk.Label(self.root, text="Скан и проверка — в главном окне PLM Reader. Здесь: выбрать модель из списка слева и смотреть.",
                 fg="#555").pack(anchor="w", padx=12, pady=(0, 4))

        data = tk.Frame(self.root)
        data.pack(fill="both", expand=True, padx=10, pady=(0, 8))
        self.sum = tk.Label(data, text="готовая база", anchor="w", bg="#fff1c7",
                            padx=8, pady=4, justify="left")
        self.sum.pack(fill="x")
        body = tk.Frame(data)
        body.pack(fill="both", expand=True, pady=(4, 0))
        left = tk.Frame(body)
        left.pack(side="left", fill="y")
        tk.Label(left, text="модели из базы (выбери):").pack(anchor="w")
        self.lst = tk.Listbox(left, width=34, height=18, font=("Consolas", 9), exportselection=False)
        sb = tk.Scrollbar(left, orient="vertical", command=self.lst.yview)
        self.lst.config(yscrollcommand=sb.set)
        self.lst.pack(side="left", fill="y")
        sb.pack(side="left", fill="y")
        self.lst.bind("<<ListboxSelect>>", self.on_pick)
        self.lst.bind("<Double-1>", lambda ev: self.tree())
        self.txt = tk.Text(body, font=("Consolas", 9), bg="#fbfbfb")
        self.txt.pack(side="left", fill="both", expand=True, padx=(8, 0))
        self.root.bind("<Configure>", lambda ev: self.sum.config(
            wraplength=max(240, self.root.winfo_width() - 60)))   # текст не пропадает в узком окне
        self.fill_list()

    def fill_list(self):
        """Список моделей из базы по фильтру — выбирать мышью, а не вводить код вручную."""
        text = self.var_model.get().strip()
        items = eng.find_models(text, 300)
        self.lst.delete(0, "end")
        for m in items:
            self.lst.insert("end", m)
        s = eng.summary()
        tot = eng.count_models(text)
        self.sum.config(text="ГОТОВАЯ БАЗА: файлов %d · моделей %d · изменений %d | в списке %d из %d%s"
                        % (s.get("snapshots", 0), s.get("models", 0), s.get("changes", 0),
                           len(items), tot, ("  (фильтр: %s)" % text) if text else ""))

    def on_pick(self, event=None):
        sel = self.lst.curselection()
        if sel:
            self.var_model.set(self.lst.get(sel[0]))

    def _sel(self):
        sel = self.lst.curselection()
        return self.lst.get(sel[0]) if sel else ""

    def tree(self):
        m = self.var_model.get().strip() or self._sel()
        if m:
            self.cap(eng.do_tree, m, 4)

    def changes(self):
        m = self.var_model.get().strip() or self._sel()
        if m:
            self.cap(eng.do_changes_model, m, 200)
        else:
            self.cap(eng.do_changes, 40)

    def where(self):
        m = self.var_model.get().strip() or self._sel() or simpledialog.askstring(
            "Модель", "Имя модели:", parent=self.root)
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
