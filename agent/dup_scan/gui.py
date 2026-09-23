# -*- coding: utf-8 -*-
"""dup_scan — ОКНО поиска двойников (настройки + поиск + перенос в урну).

Запуск: dup_scan_gui.bat (или python gui.py). Класс Р: Creo и агент не нужны.
Ничего не удаляет: лишние копии уезжают в `_trash_dup` рядом с файлом.
Движок — `dup_scan.py` в этой же папке (find_dups / move_extras).
"""
import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dup_scan as eng  # noqa: E402

SETTINGS = Path(__file__).resolve().parent / "gui_settings.json"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("ДВОЙНИКИ (одинаковые файлы)")
        self.root.geometry("1000x640")
        self.st = self.load()
        self.res = None
        self.build()

    def load(self):
        d = {"roots": [], "ext": "prt,asm,drw,pdf", "min_mb": 0.0, "mode": "report"}
        try:
            if SETTINGS.exists():
                d.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
        except Exception:
            pass
        return d

    def save(self):
        try:
            self.st.update({"roots": list(self.roots_var.get()), "ext": self.var_ext.get(),
                            "min_mb": float(self.var_min.get()), "mode": self.var_mode.get()})
            SETTINGS.write_text(json.dumps(self.st, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:
            pass

    def build(self):
        top = tk.LabelFrame(self.root, text="НАСТРОЙКИ", padx=10, pady=8)
        top.pack(fill="x", padx=10, pady=8)

        tk.Label(top, text="Где искать:").grid(row=0, column=0, sticky="nw")
        self.roots_var = tk.StringVar(value=self.st["roots"])
        self.lst = tk.Listbox(top, listvariable=self.roots_var, height=4, width=70)
        self.lst.grid(row=0, column=1, rowspan=2, sticky="we", padx=6)
        tk.Button(top, text="Добавить папку…", command=self.add_root).grid(row=0, column=2, sticky="w")
        tk.Button(top, text="Убрать", command=self.del_root).grid(row=1, column=2, sticky="w")
        tk.Label(top, text="(двойной щелчок по папке — открыть в проводнике)", fg="#555").grid(
            row=2, column=1, sticky="w")
        self.lst.bind("<Double-1>", lambda e: self.open_dir(self.selected_root()))

        tk.Label(top, text="Расширения:").grid(row=3, column=0, sticky="w", pady=4)
        self.var_ext = tk.StringVar(value=self.st["ext"])
        tk.Entry(top, textvariable=self.var_ext, width=40).grid(row=3, column=1, sticky="w", padx=6)

        tk.Label(top, text="Не меньше, МБ:").grid(row=4, column=0, sticky="w")
        self.var_min = tk.DoubleVar(value=self.st["min_mb"])
        tk.Spinbox(top, from_=0, to=100000, increment=0.5, textvariable=self.var_min, width=8).grid(
            row=4, column=1, sticky="w", padx=6)

        tk.Label(top, text="Что делать с двойниками:").grid(row=5, column=0, sticky="w", pady=4)
        self.var_mode = tk.StringVar(value=self.st["mode"])
        tk.Radiobutton(top, text="только отчёт (ничего не трогать)", variable=self.var_mode,
                       value="report", command=self.save).grid(row=5, column=1, sticky="w", padx=6)
        tk.Radiobutton(top, text="переносить в _trash_dup рядом с файлом", variable=self.var_mode,
                       value="apply", command=self.save).grid(row=5, column=1, sticky="e", padx=6)

        btns = tk.Frame(self.root)
        btns.pack(fill="x", padx=10)
        tk.Button(btns, text="НАЙТИ ДВОЙНИКОВ", width=20, command=self.run_find).pack(side="left", padx=4)
        self.b_apply = tk.Button(btns, text="ПЕРЕНЕСТИ В УРНУ", width=20, state="disabled", command=self.run_apply)
        self.b_apply.pack(side="left", padx=4)
        tk.Button(btns, text="Открыть папку отчётов", command=lambda: self.open_dir(eng.LOG_DIR)).pack(side="left", padx=4)

        cols = ("size", "keep", "extra", "where")
        heads = ("МБ", "Образец (оставляем самый свежий)", "Двойников", "Где они лежат")
        self.tree = ttk.Treeview(self.root, columns=cols, show="headings", height=13)
        for c, h, w in zip(cols, heads, (70, 420, 90, 380)):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w)
        self.tree.pack(fill="both", expand=True, padx=10, pady=8)

        self.info = tk.Text(self.root, height=7, font=("Consolas", 9), bg="#f8f9fa")
        self.info.pack(fill="x", padx=10, pady=(0, 8))

    # ---------- вспомогательное ----------
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

    def del_root(self):
        sel = self.lst.curselection()
        if not sel:
            return
        roots = list(self.roots_var.get())
        roots.pop(sel[0])
        self.roots_var.set(roots)
        self.save()

    # ---------- поиск и перенос ----------
    def run_find(self):
        roots = list(self.roots_var.get())
        if not roots:
            return messagebox.showwarning("Нет папок", "Добавьте хотя бы одну папку")
        self.save()
        exts = {x.strip().lower() for x in self.var_ext.get().split(",") if x.strip()}
        min_bytes = int(float(self.var_min.get()) * 1048576)
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.res = None
        self.b_apply.config(state="disabled")
        self.log("ищу двойников: %s (%.1f+ МБ, расширения: %s)" %
                 ("; ".join(roots), float(self.var_min.get()), ", ".join(sorted(exts)) or "все"))

        def work():
            try:
                res = eng.find_dups(roots, exts, min_bytes, progress=lambda s: self.root.after(0, self.log, s))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Ошибка поиска", str(e)))
                return
            self.root.after(0, lambda: self.show(res))
        threading.Thread(target=work, daemon=True).start()

    def show(self, res):
        self.res = res
        for g in res["groups"]:
            where = os.path.dirname(g["extra"][0][0]) if g["extra"] else ""
            self.tree.insert("", "end", values=(round(g["size"] / 1048576, 2), g["keep"][0],
                                                len(g["extra"]), where))
        self.log("групп двойников: %d, лишнего объёма %.2f ГБ (проверено файлов %d)"
                 % (len(res["groups"]), res["waste"] / 1073741824.0, res["files"]))
        for e in res["errors"]:
            self.log("   " + e)
        enough = bool(res["groups"]) and self.var_mode.get() == "apply"
        self.b_apply.config(state="normal" if enough else "disabled")
        if res["groups"] and self.var_mode.get() != "apply":
            self.log("режим «только отчёт»: чтобы перенести в урну, переключите настройку выше")

    def run_apply(self):
        if not self.res or not self.res["groups"]:
            return
        cnt = sum(len(g["extra"]) for g in self.res["groups"])
        if not messagebox.askyesno("Подтверждение",
                                   "Перенести %d файлов-двойников в _trash_dup рядом с ними?\n"
                                   "Файлы НЕ удаляются — их можно вернуть." % cnt):
            return
        moved = 0
        for g in self.res["groups"]:
            for one in g["extra"]:
                n, errs = eng.move_extras([one])
                moved += n
                if errs:
                    self.log("   НЕ перенесён: %s (%s)" % (os.path.basename(one[0]), errs[0][1]))
                else:
                    self.log("   → в урну: %s" % os.path.basename(one[0]))
        self.log("перенесено файлов: %d" % moved)
        self.run_find()


if __name__ == "__main__":
    r = tk.Tk()
    App(r)
    r.mainloop()