# -*- coding: utf-8 -*-
"""orphan_scan — ОКНО поиска чертежей-сирот.

Запуск: orphan_scan_gui.bat (или python gui.py). Класс Р: Creo не нужен (только чтение).
Нужны базы дома (`data\\agent.sqlite`, `data\\harvest.db`) и, для режима «по дому», `Z:\\PTC\\Work\\search.pro`.
Движок — `orphan_scan.py` в этой же папке (класс OrphanScanner).
"""
import csv
import json
import os
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import orphan_scan as eng  # noqa: E402

SETTINGS = Path(__file__).resolve().parent / "gui_settings.json"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("V1 — ЧЕРТЕЖИ-СИРОТЫ (нет модели рядом)")
        self.root.geometry("1080x680")
        self.st = self.load()
        self.scanner = None
        self.build()

    def load(self):
        d = {"mode": "search_pro", "roots": []}
        try:
            if SETTINGS.exists():
                d.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
        except Exception:
            pass
        return d

    def save(self):
        try:
            self.st.update({"mode": self.var_mode.get(), "roots": list(self.roots_var.get())})
            SETTINGS.write_text(json.dumps(self.st, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:
            pass

    def build(self):
        top = tk.LabelFrame(self.root, text="НАСТРОЙКИ", padx=10, pady=8)
        top.pack(fill="x", padx=10, pady=8)

        tk.Label(top, text="Что проверять:").grid(row=0, column=0, sticky="nw")
        self.var_mode = tk.StringVar(value=self.st["mode"])
        tk.Radiobutton(top, text="весь дом — все папки из Z:\\PTC\\Work\\search.pro",
                       variable=self.var_mode, value="search_pro", command=self.toggle).grid(
            row=0, column=1, sticky="w")
        tk.Radiobutton(top, text="только выбранные папки:", variable=self.var_mode, value="custom",
                       command=self.toggle).grid(row=1, column=1, sticky="w")
        self.roots_var = tk.StringVar(value=self.st["roots"])
        self.lst = tk.Listbox(top, listvariable=self.roots_var, height=4, width=74)
        self.lst.grid(row=2, column=1, sticky="we", padx=6)
        tk.Button(top, text="Добавить папку…", command=self.add_root).grid(row=2, column=2, sticky="nw")
        tk.Button(top, text="Убрать", command=self.del_root).grid(row=3, column=2, sticky="nw")
        tk.Label(top, text="осмотр идёт по подпапкам; ничего не меняется — только отчёт", fg="#555").grid(
            row=3, column=1, sticky="w")
        self.toggle()

        btns = tk.Frame(self.root)
        btns.pack(fill="x", padx=10)
        self.b_run = tk.Button(btns, text="НАЙТИ СИРОТ", width=18, command=self.run)
        self.b_run.pack(side="left", padx=4)
        self.b_stop = tk.Button(btns, text="СТОП", width=10, state="disabled", command=self.stop)
        self.b_stop.pack(side="left", padx=4)
        tk.Button(btns, text="Последний отчёт", command=self.open_report).pack(side="left", padx=4)
        tk.Button(btns, text="Папка отчётов", command=lambda: self.open_dir(eng.REPORT_DIR)).pack(side="left", padx=4)
        tk.Button(btns, text="Сохранить список (CSV)", command=self.save_csv).pack(side="left", padx=4)

        self.sum = tk.Label(self.root, text="готов", anchor="w", bg="#fff1c7", padx=8, pady=4)
        self.sum.pack(fill="x", padx=10)

        cols = ("cls", "file", "folder")
        heads = ("Класс", "Чертёж", "Папка")
        self.tree = ttk.Treeview(self.root, columns=cols, show="headings", height=16)
        for c, h, w in zip(cols, heads, (150, 420, 460)):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w)
        self.tree.pack(fill="both", expand=True, padx=10, pady=8)
        self.tree.bind("<Double-1>", lambda e: self.open_selected())
        self.tree.tag_configure("orphan", background="#ffe3e3")
        self.tree.tag_configure("elsewhere", background="#fff8dc")

        self.info = tk.Text(self.root, height=7, font=("Consolas", 9), bg="#f8f9fa")
        self.info.pack(fill="x", padx=10, pady=(0, 8))

    def toggle(self):
        state = "normal" if self.var_mode.get() == "custom" else "disabled"
        self.lst.config(state=state)
        self.save()

    def log(self, s):
        self.info.insert("end", s + "\n")
        self.info.see("end")

    def open_dir(self, p):
        try:
            if p and os.path.isdir(p):
                os.startfile(p)
        except Exception as e:
            messagebox.showwarning("Не открыть", "%s\n%s" % (p, e))

    def open_report(self):
        try:
            files = sorted(Path(eng.REPORT_DIR).glob("REPORT_spec113_local_leg_*.md"))
            if not files:
                return messagebox.showinfo("Отчётов нет", "Сначала прогон")
            os.startfile(str(files[-1]))
        except Exception as e:
            messagebox.showerror("Не открыть", str(e))

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

    def open_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        p = self.tree.item(sel[0], "values")[1]
        self.open_dir(os.path.dirname(p))

    # ---------- прогон ----------
    def run(self):
        roots = None
        if self.var_mode.get() == "custom":
            roots = list(self.roots_var.get())
            if not roots:
                return messagebox.showwarning("Нет папок", "Добавьте хотя бы одну папку")
        self.save()
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.b_run.config(state="disabled")
        self.b_stop.config(state="normal")
        self.sum.config(text="идёт осмотр…")
        self.scanner = eng.OrphanScanner()
        self._stop = False

        def work():
            try:
                self.scanner.scan(roots=roots, progress=lambda s: self.root.after(0, self.log, s))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Ошибка осмотра", str(e)))
            self.root.after(0, self.done)
        threading.Thread(target=work, daemon=True).start()

    def stop(self):
        # мягкая остановка: обход прерываем флагом, отчёт по уже найденному пишем
        if self.scanner:
            self.scanner.roots = []
            self.log("остановка: обход прекращён, пишу отчёт по найденному")
        self.b_stop.config(state="disabled")

    def done(self):
        self.b_run.config(state="normal")
        self.b_stop.config(state="disabled")
        s = self.scanner
        if not s:
            return
        for p in s.orphans:
            self.tree.insert("", "end", values=("СИРОТА", p, os.path.dirname(p)), tags=("orphan",))
        for p in s.model_elsewhere_list:
            self.tree.insert("", "end", values=("модель в другом месте", p, os.path.dirname(p)),
                             tags=("elsewhere",))
        self.sum.config(text="чертежей: %d | не сирот: %d | модель в другом месте: %d | СИРОТ: %d"
                             % (s.stats["total_drawings"], s.stats["not_orphan"],
                                s.stats["model_elsewhere"], s.stats["orphan"]))
        self.log("сирот: %d; по папкам (топ-10): %s"
                 % (s.stats["orphan"],
                    ", ".join("%s=%d" % (k, v) for k, v in
                              sorted(s.distribution.items(), key=lambda kv: -kv[1])[:10]) or "—"))
        self.log("пишу отчёт…")
        try:
            s.run_report()
            self.log("готово: отчёт в %s" % eng.REPORT_DIR)
        except Exception as e:
            self.log("отчёт не записан: %s" % e)

    def save_csv(self):
        rows = [(self.tree.item(i, "values")[0], self.tree.item(i, "values")[1]) for i in self.tree.get_children()]
        if not rows:
            return messagebox.showinfo("Нечего сохранять", "Сначала осмотр")
        p = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="сироты.csv")
        if not p:
            return
        try:
            with open(p, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["класс", "чертёж"])
                w.writerows(rows)
            self.log("список сохранён: %s" % p)
        except Exception as e:
            messagebox.showerror("Не сохранить", str(e))


if __name__ == "__main__":
    r = tk.Tk()
    App(r)
    r.mainloop()