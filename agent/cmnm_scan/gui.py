# -*- coding: utf-8 -*-
"""cmnm_scan — ОКНО проверки внутренних имён Creo-файлов (CMNM против имени файла).

Запуск: cmnm_scan_gui.bat (или python gui.py). Класс Р: Creo и агент не нужны, только чтение.
Движок — `cmnm_scan.py` в этой же папке (функция scan).
"""
import json
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cmnm_scan as eng  # noqa: E402

SETTINGS = Path(__file__).resolve().parent / "gui_settings.json"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("ВНУТРЕННИЕ ИМЕНА (CMNM) против имён файлов")
        self.root.geometry("1020x620")
        self.st = self.load()
        self.res = None
        self.build()

    def load(self):
        d = {"roots": [], "limit": 0}
        try:
            if SETTINGS.exists():
                d.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
        except Exception:
            pass
        return d

    def save(self):
        try:
            self.st.update({"roots": list(self.roots_var.get()), "limit": int(self.var_limit.get())})
            SETTINGS.write_text(json.dumps(self.st, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:
            pass

    def build(self):
        top = tk.LabelFrame(self.root, text="НАСТРОЙКИ", padx=10, pady=8)
        top.pack(fill="x", padx=10, pady=8)

        tk.Label(top, text="Где проверять:").grid(row=0, column=0, sticky="nw")
        self.roots_var = tk.StringVar(value=self.st["roots"])
        self.lst = tk.Listbox(top, listvariable=self.roots_var, height=4, width=74)
        self.lst.grid(row=0, column=1, rowspan=2, sticky="we", padx=6)
        tk.Button(top, text="Добавить папку…", command=self.add_root).grid(row=0, column=2, sticky="w")
        tk.Button(top, text="Убрать", command=self.del_root).grid(row=1, column=2, sticky="w")
        tk.Label(top, text="(двойной щелчок по файлу в таблице — открыть его папку)", fg="#555").grid(
            row=2, column=1, sticky="w")

        tk.Label(top, text="Лимит файлов (0 — без предела):").grid(row=3, column=0, sticky="w", pady=4)
        self.var_limit = tk.IntVar(value=self.st["limit"])
        tk.Spinbox(top, from_=0, to=1000000, textvariable=self.var_limit, width=9).grid(row=3, column=1, sticky="w", padx=6)

        btns = tk.Frame(self.root)
        btns.pack(fill="x", padx=10)
        self.b_find = tk.Button(btns, text="ПРОВЕРИТЬ", width=18, command=self.run)
        self.b_find.pack(side="left", padx=4)
        tk.Button(btns, text="Открыть папку отчётов", command=lambda: self.open_dir(eng.LOG_DIR)).pack(side="left", padx=4)
        tk.Button(btns, text="Сохранить список (CSV)", command=self.save_csv).pack(side="left", padx=4)

        cols = ("file", "internal", "where")
        heads = ("Файл", "Внутри файла", "Папка")
        self.tree = ttk.Treeview(self.root, columns=cols, show="headings", height=14)
        for c, h, w in zip(cols, heads, (260, 260, 470)):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w)
        self.tree.pack(fill="both", expand=True, padx=10, pady=8)
        self.tree.bind("<Double-1>", lambda e: self.open_selected())

        self.info = tk.Text(self.root, height=8, font=("Consolas", 9), bg="#f8f9fa")
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

    def selected_root(self):
        sel = self.lst.curselection()
        return self.roots_var.get()[sel[0]] if sel else ""

    def add_root(self):
        p = filedialog.askdirectory()
        if p:
            roots = list(self.roots_var.get())
            if p not in roots:
                roots.append(p)
                self.roots_var.set(roots)
                self.save()

    def del_root(self):
        sel = self.lst.curselection()
        if not sel:
            return
        roots = list(self.roots_var.get())
        roots.pop(sel[0])
        self.roots_var.set(roots)
        self.save()
# ---------- проверка ----------
    def run(self):
        roots = list(self.roots_var.get())
        if not roots:
            return messagebox.showwarning("Нет папок", "Добавьте хотя бы одну папку")
        self.save()
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.b_find.config(state="disabled")
        self.log("проверяю: %s" % "; ".join(roots))

        def work():
            try:
                res = eng.scan(roots, int(self.var_limit.get()),
                               progress=lambda s: self.root.after(0, self.log, s))
            except Exception as e:
                self.root.after(0, lambda: (messagebox.showerror("Ошибка", str(e)),
                                            self.b_find.config(state="normal")))
                return
            self.root.after(0, lambda: self.show(res))
        threading.Thread(target=work, daemon=True).start()

    def show(self, res):
        self.res = res
        for full, nm, fn in res["bad"]:
            self.tree.insert("", "end", values=(fn, nm, os.path.dirname(full)))
        self.log("файлов просмотрено: %d; без поля CMNM: %d; РАСХОЖДЕНИЙ: %d (%.0f с)"
                 % (res["files"], res["nofield"], len(res["bad"]), res["seconds"]))
        if res["bad"]:
            self.log("это значит: Creo НЕ откроет модель по имени файла (XToolkitNotFound).")
            self.log("как лечить: открыть файл в Creo и «Сохранить как» с правильным именем, "
                     "либо переименовать файл под внутреннее имя (если так задумано).")
        elif res["files"]:
            self.log("расхождений нет — модели откроются по имени файла.")
        self.b_find.config(state="normal")

    def open_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        self.open_dir(self.tree.item(sel[0], "values")[2])

    def save_csv(self):
        if not self.res or not self.res["bad"]:
            return messagebox.showinfo("Нечего сохранять", "Сначала проверка с расхождениями")
        p = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="cmnm_расхождения.csv")
        if not p:
            return
        try:
            with open(p, "w", encoding="utf-8-sig") as f:
                f.write("файл;внутри файла;полный путь\n")
                for full, nm, fn in self.res["bad"]:
                    f.write("%s;%s;%s\n" % (fn, nm, full))
            self.log("список сохранён: %s" % p)
        except Exception as e:
            messagebox.showerror("Не сохранить", str(e))


if __name__ == "__main__":
    r = tk.Tk()
    App(r)
    r.mainloop()