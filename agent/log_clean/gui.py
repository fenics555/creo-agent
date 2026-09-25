# -*- coding: utf-8 -*-
"""log_clean — ОКНО уборки логов (настройки + план + уборка). Класс Р: Creo и агент не нужны.

Запуск: log_clean_gui.bat  (или python gui.py)
Настройки: gui_settings.json рядом с программой; сроки по каталогам — D:\\AI\\log\\retention.json
(тот же файл читает ночной цикл агента, поэтому цифры одни на всех).
"""
import json
import os
import time
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import engine  # noqa: E402

PROG_DIR = Path(__file__).resolve().parent
SETTINGS_FILE = PROG_DIR / "gui_settings.json"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("V1 — УБОРКА ЛОГОВ дома")
        self.root.geometry("980x620")
        self.st = self.load()
        self.plan = []
        self.build()
        self.refresh()

    # ---------- настройки ----------
    def load(self):
        d = {"root": str(engine.LOG_ROOT), "days": engine.DEFAULT_DAYS,
             "mode": "trash", "trash_days": 7}
        try:
            if SETTINGS_FILE.exists():
                d.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
        return d

    def save(self):
        try:
            self.st.update({"root": self.var_root.get(), "days": int(self.var_days.get()),
                            "mode": self.var_mode.get(), "trash_days": int(self.var_trash.get())})
            SETTINGS_FILE.write_text(json.dumps(self.st, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:
            pass

    # ---------- интерфейс ----------
    def build(self):
        top = tk.LabelFrame(self.root, text="НАСТРОЙКИ", padx=10, pady=8)
        top.pack(fill="x", padx=10, pady=8)

        tk.Label(top, text="Корень логов:").grid(row=0, column=0, sticky="w")
        self.var_root = tk.StringVar(value=self.st["root"])
        tk.Entry(top, textvariable=self.var_root, width=62).grid(row=0, column=1, padx=6)
        tk.Button(top, text="Обзор", command=self.browse).grid(row=0, column=2)

        tk.Label(top, text="Срок по умолчанию (дней):").grid(row=1, column=0, sticky="w", pady=4)
        self.var_days = tk.IntVar(value=self.st["days"])
        tk.Spinbox(top, from_=1, to=3650, textvariable=self.var_days, width=6).grid(row=1, column=1, sticky="w", padx=6)

        tk.Label(top, text="Что делать со старым:").grid(row=2, column=0, sticky="w")
        self.var_mode = tk.StringVar(value=self.st["mode"])
        tk.Radiobutton(top, text="уносить в корзину (можно вернуть)", variable=self.var_mode,
                       value="trash", command=self.save).grid(row=2, column=1, sticky="w", padx=6)
        tk.Radiobutton(top, text="удалять навсегда", variable=self.var_mode,
                       value="delete", command=self.save).grid(row=2, column=1, sticky="e", padx=6)
        tk.Label(top, text="Держать корзину (дней):").grid(row=3, column=0, sticky="w", pady=4)
        self.var_trash = tk.IntVar(value=self.st["trash_days"])
        tk.Spinbox(top, from_=0, to=365, textvariable=self.var_trash, width=6).grid(row=3, column=1, sticky="w", padx=6)
        tk.Label(top, text="двойной щелчок по строке — срок ИМЕННО этого каталога (пишется в retention.json)",
                 fg="#555").grid(row=4, column=0, columnspan=3, sticky="w")

        btns = tk.Frame(self.root)
        btns.pack(fill="x", padx=10)
        tk.Button(btns, text="ОБНОВИТЬ ПЛАН", width=18, command=self.refresh).pack(side="left", padx=4)
        self.b_run = tk.Button(btns, text="УБРАТЬ СТАРОЕ", width=18, state="disabled", command=self.run_clean)
        self.b_run.pack(side="left", padx=4)
        tk.Button(btns, text="Открыть папку логов", command=lambda: self.open_dir(self.var_root.get())).pack(side="left", padx=4)
        tk.Button(btns, text="Открыть корзину", command=lambda: self.open_dir(str(Path(self.var_root.get()) / "_trash_clean"))).pack(side="left", padx=4)

        cols = ("folder", "files", "days", "old", "mb", "locked", "oldest", "newest")
        heads = ("Каталог", "Файлов", "Срок дн.", "Старше", "МБ", "Занятых", "Самый старый", "Последний")
        self.tree = ttk.Treeview(self.root, columns=cols, show="headings", height=14)
        for c, h, w in zip(cols, heads, (170, 70, 80, 70, 70, 80, 110, 110)):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=8)
        self.tree.bind("<Double-1>", self.edit_days)

        self.info = tk.Text(self.root, height=6, font=("Consolas", 9), bg="#f8f9fa")
        self.info.pack(fill="x", padx=10, pady=(0, 8))

    def log(self, s):
        self.info.insert("end", s + "\n")
        self.info.see("end")

    def open_dir(self, p):
        try:
            os.startfile(p)
        except Exception as e:
            messagebox.showwarning("Нет папки", "%s\n%s" % (p, e))

    def browse(self):
        from tkinter import filedialog
        p = filedialog.askdirectory()
        if p:
            self.var_root.set(p)
            self.save()
            self.refresh()

    # ---------- работа ----------
    def refresh(self):
        self.save()
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.plan = engine.scan(self.var_root.get(), int(self.var_days.get()))
        tot_old = tot_mb = 0
        for r in self.plan:
            self.tree.insert("", "end", values=(r["folder"], r["files"], r["days"], r["old"],
                                                round(r["old_bytes"] / 1048576, 1), r["locked"],
                                                r["oldest"], r["newest"]))
            tot_old += r["old"]
            tot_mb += r["old_bytes"]
        self.b_run.config(state="normal" if tot_old else "disabled")
        self.log("план: каталогов %d, старше срока %d файлов (%.1f МБ)" % (len(self.plan), tot_old, tot_mb / 1048576))

    def edit_days(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        name = self.tree.item(sel[0], "values")[0]
        cur = self.tree.item(sel[0], "values")[2]
        d = tk.simpledialog.askinteger("Срок хранения", "Сколько дней держать каталог «%s»?" % name,
                                       initialvalue=int(cur), minvalue=1, maxvalue=3650)
        if not d:
            return
        retention = engine.get_retention()
        retention[name] = int(d)
        engine.save_retention(retention)
        self.log("срок для «%s» = %d дней (записано в retention.json — то же число увидит ночной цикл агента)"
                 % (name, d))
        self.refresh()

    def run_clean(self):
        old = sum(r["old"] for r in self.plan)
        if not old:
            return
        mode = self.var_mode.get()
        word = "унести в корзину" if mode == "trash" else "УДАЛИТЬ НАВСЕГДА"
        if not messagebox.askyesno("Подтверждение",
                                   "Файлов старше срока: %d\nЧто делаем: %s\n\nПродолжить?"
                                   % (old, word)):
            return
        _t0 = time.time()
        rep = engine.clean(self.var_root.get(), mode, int(self.var_days.get()))
        self.log("сделано: в корзину %d, удалено %d, пропущено %d, освобождено %.1f МБ (за %.1f с)"
                 % (len(rep["перенесено"]), len(rep["удалено"]), len(rep["пропущено"]),
                    rep["байт"] / 1048576, time.time() - _t0))
        for s in rep["пропущено"][:10]:
            self.log("   пропущено: %s" % s)
        gone = engine.trash_cleanup(int(self.var_trash.get()), self.var_root.get())
        for g in gone:
            self.log("корзина: убран старый каталог %s" % g)
        self.refresh()


if __name__ == "__main__":
    r = tk.Tk()
    App(r)
    r.mainloop()