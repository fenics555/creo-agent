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
from tkinter import simpledialog, ttk

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import engine as eng  # noqa: E402

VERSION = "V1"
SETTINGS = HERE / "gui_settings.json"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("PLM-ДЕРЕВО %s — паспорт · дерево · входимость · изменения" % VERSION)
        self.root.geometry("1140x720")
        self.s = self.load()
        self.build()

    def load(self):
        try:
            return json.loads(SETTINGS.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def save(self):
        try:
            SETTINGS.write_text(json.dumps(
                {"roots": self.roots(), "limit": self.var_limit.get(),
                 "max_mb": self.var_mmb.get(), "depth": self.var_depth.get()},
                ensure_ascii=False, indent=1),
                encoding="utf-8")
        except Exception:
            pass

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
        top = tk.LabelFrame(self.root, text=" НАСТРОЙКИ ", padx=10, pady=8)
        top.pack(fill="x", padx=10, pady=(10, 6))
        r = self.s.get("roots") or eng.DEFAULT_ROOTS
        tk.Label(top, text="Корень 1:").grid(row=0, column=0, sticky="w")
        self.var_r1 = tk.StringVar(value=r[0] if r else "")
        tk.Entry(top, textvariable=self.var_r1, width=88).grid(row=0, column=1, padx=6, pady=3)
        tk.Label(top, text="Корень 2:").grid(row=1, column=0, sticky="w")
        self.var_r2 = tk.StringVar(value=r[1] if len(r) > 1 else "")
        tk.Entry(top, textvariable=self.var_r2, width=88).grid(row=1, column=1, padx=6, pady=3)
        tk.Label(top, text="Лимит, с:").grid(row=2, column=0, sticky="w")
        self.var_limit = tk.StringVar(value=str(self.s.get("limit", 120)))
        tk.Entry(top, textvariable=self.var_limit, width=8).grid(row=2, column=1, sticky="w", padx=6, pady=3)
        tk.Label(top, text="Макс. файл, МБ:").grid(row=3, column=0, sticky="w")
        self.var_mmb = tk.StringVar(value=str(self.s.get("max_mb", 8)))
        tk.Entry(top, textvariable=self.var_mmb, width=8).grid(row=3, column=1, sticky="w", padx=6, pady=3)
        tk.Label(top, text="Глубина папок (0 = без предела):").grid(row=4, column=0, sticky="w")
        self.var_depth = tk.StringVar(value=str(self.s.get("depth", 0)))
        tk.Entry(top, textvariable=self.var_depth, width=8).grid(row=4, column=1, sticky="w", padx=6, pady=3)
        tk.Label(top, text="своя база: %s" % eng.DB, fg="#555").grid(
            row=5, column=0, columnspan=2, sticky="w")

        bar = tk.Frame(self.root)
        bar.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(bar, text="Модель:").pack(side="left")
        self.var_model = tk.StringVar(value="")
        tk.Entry(bar, textvariable=self.var_model, width=26).pack(side="left", padx=6)
        self.b_scan = tk.Button(bar, text="СКАНИРОВАТЬ", width=15, command=self.scan)
        self.b_scan.pack(side="left", padx=4)
        tk.Button(bar, text="ДЕРЕВО", width=10, command=lambda: self.cap(eng.do_tree, self.var_model.get().strip(), 4)).pack(side="left", padx=4)
        tk.Button(bar, text="ГДЕ ИСПОЛЬЗУЕТСЯ", width=17, command=self.where).pack(side="left", padx=4)
        tk.Button(bar, text="ИЗМЕНЕНИЯ", width=11, command=lambda: self.cap(eng.do_changes, 40)).pack(side="left", padx=4)
        tk.Button(bar, text="README", width=9, command=self.show_readme).pack(side="left", padx=4)
        tk.Button(bar, text="СЧИТАТЬ (строение)", width=17, command=self.count).pack(side="left", padx=4)
        tk.Button(bar, text="💾 СОХРАНИТЬ НАСТРОЙКИ", width=22,
                  command=self.save_settings).pack(side="left", padx=4)

        self.sum = tk.Label(self.root, text="готов", anchor="w", bg="#fff1c7", padx=8, pady=4)
        self.sum.pack(fill="x", padx=10)
        self.pb = ttk.Progressbar(self.root, mode="determinate")
        self.pb.pack(fill="x", padx=10, pady=(0, 6))
        self.txt = tk.Text(self.root, font=("Consolas", 9), bg="#fbfbfb")
        self.txt.pack(fill="both", expand=True, padx=10, pady=8)

    def roots(self):
        return [x for x in (self.var_r1.get().strip(), self.var_r2.get().strip()) if x]

    def scan(self):
        self.save()
        self.b_scan.config(state="disabled")
        self.sum.config(text="сканирую…")
        t0 = time.time()
        self.log("=" * 100)
        self.log("СКАНИРОВАНИЕ: %s" % " | ".join(self.roots()))

        def work():
            import contextlib
            import io
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    eng.do_scan(self.roots(), float(self.var_mmb.get() or 8),
                                float(self.var_limit.get() or 120),
                                (int(self.var_depth.get() or 0) or None), progress_cb=self.on_prog)
            except Exception as e:
                buf.write("ОШИБКА: %s" % e)
            self.root.after(0, lambda: self.done_scan(buf.getvalue(), time.time() - t0))
        threading.Thread(target=work, daemon=True).start()

    def done_scan(self, out, secs):
        self.log(out.rstrip())
        self.sum.config(text="сканирование: за %.1f с" % secs)
        self.b_scan.config(state="normal")

    def where(self):
        m = self.var_model.get().strip() or simpledialog.askstring("Модель", "Имя модели:", parent=self.root)
        if m:
            self.cap(eng.do_where, m)

    def save_settings(self):
        self.save()
        self.sum.config(text="настройки сохранены: %s" % SETTINGS)

    def on_prog(self, done, total):
        pct = 100.0 * done / max(total, 1)
        self.root.after(0, lambda: (self.pb.config(maximum=max(total, 1), value=done),
                                    self.sum.config(text="скан: %d/%d (%.0f%%)" % (done, total, pct))))

    def count(self):
        def work():
            import contextlib
            import io
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    eng.inventory(self.roots(), float(self.var_mmb.get() or 8),
                                  max_depth=(int(self.var_depth.get() or 0) or None))
            except Exception as e:
                buf.write("ОШИБКА: %s" % e)
            self.root.after(0, lambda: self.log(buf.getvalue().rstrip()))
        threading.Thread(target=work, daemon=True).start()

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
