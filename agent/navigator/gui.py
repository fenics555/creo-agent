# -*- coding: utf-8 -*-
"""navigator — ОКНО «НАВИГАТОР ПО ДОМУ»: поиск сборки -> деталировка -> PDF с увеличением.

Запуск: navigator_gui.bat. Класс Р: Creo не нужен (данные — индекс дома).
Как пользоваться:
  1) пишешь запрос (например `turn` или `турновер`) и жмёшь НАЙТИ;
  2) выбираешь сборку — справа сразу её деталировка (позиции, количество, есть ли PDF);
  3) выбираешь позицию — снизу показывается её PDF маленьким;
  4) клик по PDF — увеличивает (рыбий глаз), щелчок колесом или двойной клик — вернуть превью,
     колесо мыши — плавный зум, кнопка — открыть в Acrobat.
"""
import os
import time
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

sys.path.insert(0, str(Path(__file__).resolve().parent))
import navigator as eng  # noqa: E402

PREVIEW_W = 300          # ширина маленького превью, px
MAX_ZOOM = 8.0


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("V1 — НАВИГАТОР ПО ДОМУ — поиск, деталировка, PDF")
        self.root.geometry("1320x820")
        self.results = []
        self.bom_rows = []
        self.pdf_path = None
        self.zoom = 1.0
        self.img = None
        self.build()
        # агент может передать запрос через nav_show: окно сразу ищет и показывает результат
        start_q = os.environ.get("NAV_START_QUERY", "").strip()
        if start_q:
            self.var_q.set(start_q)
            self.root.after(200, self.search)

    # ---------- интерфейс ----------
    def build(self):
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=8)
        tk.Label(top, text="Что ищем:").pack(side="left")
        self.var_q = tk.StringVar(value="turn")
        e = tk.Entry(top, textvariable=self.var_q, width=46, font=("Segoe UI", 11))
        e.pack(side="left", padx=6)
        e.bind("<Return>", lambda ev: self.search())
        tk.Button(top, text="НАЙТИ", width=12, command=self.search).pack(side="left")
        self.var_asm = tk.BooleanVar(value=False)
        tk.Checkbutton(top, text="только сборки", variable=self.var_asm).pack(side="left", padx=8)
        tk.Label(top, text="(можно писать словами: «turn блок»)", fg="#555").pack(side="left")
        self.lab = tk.Label(top, text="", anchor="w", bg="#fff1c7", padx=8)
        self.lab.pack(side="left", fill="x", expand=True, padx=6)

        mid = tk.PanedWindow(self.root, orient="horizontal", sashwidth=6)
        mid.pack(fill="both", expand=True, padx=10)

        # левая половина: результаты поиска
        left = tk.LabelFrame(mid, text="НАЙДЕНО")
        self.tree = ttk.Treeview(left, columns=("kind", "name", "folder"), show="headings")
        for c, h, w in (("kind", "Тип", 80), ("name", "Имя", 250), ("folder", "Папка", 380)):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)
        self.tree.bind("<<TreeviewSelect>>", lambda ev: self.picked_model())
        self.tree.bind("<Double-1>", lambda ev: self.open_selected_folder())
        mid.add(left, minsize=420)

        right = tk.PanedWindow(mid, orient="vertical", sashwidth=6)
        # правая верх: деталировка
        top_r = tk.LabelFrame(right, text="ДЕТАЛИРОВКА (состав из индекса дома)")
        self.tree_bom = ttk.Treeview(top_r, columns=("num", "kind", "name", "qty", "pdf", "where"),
                                     show="headings")
        for c, h, w in (("num", "№", 40), ("kind", "Тип", 70), ("name", "Позиция", 250),
                        ("qty", "Кол", 45), ("pdf", "PDF", 55), ("where", "Где лежит", 330)):
            self.tree_bom.heading(c, text=h)
            self.tree_bom.column(c, width=w, anchor="w")
        self.tree_bom.pack(fill="both", expand=True, padx=6, pady=6)
        self.tree_bom.bind("<<TreeviewSelect>>", lambda ev: self.picked_position())
        self.tree_bom.bind("<Double-1>", lambda ev: self.open_position_folder())
        right.add(top_r, minsize=260)

        # правая низ: PDF-превью с рыбьим глазом
        bot_r = tk.LabelFrame(right, text="PDF (клик — увеличить, колесо — зум, двойной клик — вернуть)")
        self.canvas = tk.Canvas(bot_r, bg="#525659", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=6, pady=6)
        self.canvas.bind("<Button-1>", self.zoom_at)
        self.canvas.bind("<Button-3>", lambda ev: self.set_zoom(1.0))
        self.canvas.bind("<Double-1>", lambda ev: self.set_zoom(1.0))
        self.canvas.bind("<MouseWheel>", self.wheel)
        self.canvas.bind("<Configure>", lambda ev: self.redraw())
        right.add(bot_r, minsize=280)
        mid.add(right, minsize=520)

        bar = tk.Frame(self.root)
        bar.pack(fill="x", padx=10, pady=(0, 8))
        tk.Button(bar, text="Открыть PDF в Acrobat", command=self.open_pdf).pack(side="left", padx=4)
        tk.Button(bar, text="Открыть папку позиции", command=self.open_position_folder).pack(side="left", padx=4)
        tk.Button(bar, text="Сохранить картинку…", command=self.save_png).pack(side="left", padx=4)
        tk.Button(bar, text="Состав из живой сессии (Creo)", command=self.live_bom).pack(side="left", padx=4)
        tk.Button(bar, text="Показать полную деталировку (глубже)", command=self.deep_bom).pack(side="left", padx=4)
        self.lab_pdf = tk.Label(bar, text="PDF не выбран", anchor="w", fg="#444")
        self.lab_pdf.pack(side="left", padx=10)

    # ---------- вспомогательное ----------
    def say(self, s):
        self.lab.config(text=s)

    def open_dir(self, p):
        try:
            if p and os.path.isdir(p):
                os.startfile(p)
        except Exception as e:
            messagebox.showwarning("Не открыть", "%s\n%s" % (p, e))

    def open_selected_folder(self):
        sel = self.tree.selection()
        if sel:
            self.open_dir(self.tree.item(sel[0], "values")[2])

    def open_position_folder(self):
        sel = self.tree_bom.selection()
        if not sel:
            return
        i = int(self.tree_bom.item(sel[0], "values")[0]) - 1
        if 0 <= i < len(self.bom_rows):
            self.open_dir(os.path.dirname(self.bom_rows[i]["path"] or ""))

    # ---------- поиск и деталировка ----------
    def search(self):
        q = self.var_q.get().strip()
        if len(q) < 2:
            return self.say("введите хотя бы 2 буквы")
        self.say("ищу: %s …" % q)
        self._t0 = time.time()
        self.tree.delete(*self.tree.get_children())
        only = bool(self.var_asm.get())

        def work():
            try:
                res = eng.find_words(q, limit=400, only_asm=only)
            except Exception as e:
                self.root.after(0, lambda: self.say("ошибка поиска: %s" % e))
                return
            self.root.after(0, lambda: self.show_results(res))
        threading.Thread(target=work, daemon=True).start()

    def show_results(self, res):
        self.results = res
        for r in res:
            hit = ("  (слов %d/%d)" % (r["words_hit"], r["words_all"])) if r.get("words_all") else ""
            self.tree.insert("", "end", values=(r["kind"], r["name"] + hit, r["folder"]))
        self.say("найдено: %d за %.1f с (двойной щелчок — открыть папку, выбор — деталировка)"
                 % (len(res), time.time() - getattr(self, "_t0", time.time())))

    def picked_model(self):
        sel = self.tree.selection()
        if not sel:
            return
        i = self.tree.index(sel[0])
        if not (0 <= i < len(self.results)):
            return
        rec = self.results[i]
        name = rec["name"]
        if not name.lower().endswith((".1", ".2", ".3")):
            name = name + ".1"
        self.show_bom(name, depth=2)

    def show_bom(self, model, depth=2):
        self.tree_bom.delete(*self.tree_bom.get_children())
        self.bom_rows = []
        self.lab_pdf.config(text="собираю деталировку…")
        try:
            rows = eng.bom(model, depth=depth)
        except Exception as e:
            self.lab_pdf.config(text="деталировка не собралась: %s" % e)
            return
        self.bom_rows = rows
        for n, r in enumerate(rows, 1):
            self.tree_bom.insert("", "end", values=("%d.%d" % (r["level"], n), r["kind"], r["name"],
                                                    r["qty"], "да" if r["has_pdf"] else "—",
                                                    r["path"] or ""))
        withpdf = sum(1 for r in rows if r["has_pdf"])
        self.lab_pdf.config(text="позиций: %d, с PDF: %d%s" % (len(rows), withpdf,
                                                             "" if rows else " — состава в индексе нет"))

    def deep_bom(self):
        sel = self.tree.selection()
        if not sel:
            return
        i = self.tree.index(sel[0])
        if 0 <= i < len(self.results):
            self.show_bom(self.results[i]["name"], depth=9)

    def live_bom(self):
        """Состав ИЗ ЖИВОЙ СЕССИИ Creo (CREOSON): окно само откроет модель, прочитает состав и уберёт её.
        Живой факт 23.09.2026: CREOSON требует имя без версии (`d25.asm`) и открытую модель."""
        sel = self.tree.selection()
        if not sel:
            return self.say("сначала найди и выбери сборку")
        i = self.tree.index(sel[0])
        if not (0 <= i < len(self.results)):
            return
        rec = self.results[i]
        self.lab_pdf.config(text="читаю состав из сессии Creo: %s …" % rec["name"])

        def work():
            rows, err = eng.bom_live(rec["name"], path=rec.get("path"))
            self.root.after(0, lambda: self.show_live(rows, err, rec["name"]))
        threading.Thread(target=work, daemon=True).start()

    def show_live(self, rows, err, model):
        if err:
            self.lab_pdf.config(text="живая сессия: %s" % err)
            return
        self.tree_bom.delete(*self.tree_bom.get_children())
        self.bom_rows = []
        for r in rows:
            r["pdf"] = eng.pdf_for(r["name"])
            r["has_pdf"] = bool(r["pdf"])
            r["path"] = r["path"] or eng.path_of(r["name"])
            self.bom_rows.append(r)
        for n, r in enumerate(self.bom_rows, 1):
            self.tree_bom.insert("", "end", values=("%d.%d" % (r["level"], n), r["kind"], r["name"],
                                                    r["qty"], "да" if r["has_pdf"] else "—",
                                                    r["path"] or "(в сессии)"))
        self.lab_pdf.config(text="СОСТАВ ИЗ СЕССИИ %s: позиций %d (модель убрана из сессии)" % (model, len(rows)))

    # ---------- PDF с «рыбьим глазом» ----------
    def picked_position(self):
        sel = self.tree_bom.selection()
        if not sel:
            return
        num = self.tree_bom.item(sel[0], "values")[0]
        i = int(str(num).split(".")[-1]) - 1
        if not (0 <= i < len(self.bom_rows)):
            return
        r = self.bom_rows[i]
        p = r["pdf"] or eng.pdf_for(r["path"] or r["name"])
        self.show_pdf(p, "%s  %s" % (r["name"], eng.pdf_status(p) if p else ""))

    def show_pdf(self, path, title=""):
        self.pdf_path = path
        self.zoom = 1.0
        if not path or not os.path.exists(path):
            self.canvas.delete("all")
            self.lab_pdf.config(text="PDF не найден: %s" % (title or ""))
            return
        self.lab_pdf.config(text=title or os.path.basename(path))
        self.redraw()

    def redraw(self):
        if not self.pdf_path:
            return
        data, info = eng.render_pdf(self.pdf_path, width=int(PREVIEW_W * self.zoom))
        if not data:
            self.canvas.delete("all")
            self.lab_pdf.config(text=str(info))
            return
        self.img = tk.PhotoImage(data=data)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self.img)
        self.canvas.config(scrollregion=(0, 0, self.img.width(), self.img.height()))
        self.lab_pdf.config(text="%s — %d×%d px, зум ×%.2f" % (os.path.basename(self.pdf_path),
                                                               self.img.width(), self.img.height(), self.zoom))

    def set_zoom(self, z, cx=None, cy=None):
        old = self.zoom
        self.zoom = max(0.4, min(MAX_ZOOM, z))
        if abs(self.zoom - old) < 0.001:
            return
        self.redraw()
        if cx is not None and self.img:
            k = self.zoom / old
            sw, sh = max(1, self.img.width()), max(1, self.img.height())
            cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
            self.canvas.xview_moveto(max(0.0, (cx * k - cw / 2) / sw))
            self.canvas.yview_moveto(max(0.0, (cy * k - ch / 2) / sh))

    def zoom_at(self, event):
        """Клик по PDF — «рыбий глаз»: масштаб растёт, точка клика остаётся на виду."""
        if not self.pdf_path:
            return
        self.set_zoom(self.zoom * 2.0, self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))

    def wheel(self, event):
        if not self.pdf_path:
            return
        step = 1.25 if event.delta > 0 else 1 / 1.25
        self.set_zoom(self.zoom * step, self.canvas.canvasx(event.x), self.canvas.canvasy(event.y))

    def open_pdf(self):
        if self.pdf_path and os.path.exists(self.pdf_path):
            try:
                os.startfile(self.pdf_path)
            except Exception as e:
                messagebox.showwarning("Не открыть", str(e))

    def save_png(self):
        if not self.img:
            return
        p = filedialog.asksaveasfilename(defaultextension=".png", initialfile="деталь.png")
        if p:
            try:
                self.img.write(p, format="png")
                self.lab_pdf.config(text="картинка сохранена: %s" % p)
            except Exception as e:
                messagebox.showerror("Не сохранить", str(e))


if __name__ == "__main__":
    r = tk.Tk()
    App(r)
    r.mainloop()