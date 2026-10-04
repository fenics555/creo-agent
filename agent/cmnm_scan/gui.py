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
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import cmnm_scan as eng  # noqa: E402
import ui_common as U  # noqa: E402  (волна 1: общий каркас окон; признаки дизайна — в нём)

SETTINGS = Path(__file__).resolve().parent / "gui_settings.json"
TITLE = "ВНУТРЕННИЕ ИМЕНА (CMNM) против имён файлов"


class App:
    def __init__(self, root=None):
        # ПЕРЕВОД НА КАРКАС 04.10.2026 (эталон для 11 окон вне ui_common):
        # было root.geometry(...) и title вручную, без minsize и без каркаса.
        # Теперь make_root даёт title с версией + geometry + minsize разом.
        self.root = root or U.make_root("V3 — " + TITLE, "1020x620", minsize=(900, 560))
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
        # Живая находка 02.10.2026 (аудит): битый список папок = список ОДНОСИМВОЛЬНЫХ строк
        # (так старый код писал `list(StringVar.get())`). Такое молча выкидываем.
        roots = [r for r in (d.get("roots") or []) if isinstance(r, str) and len(r) > 2]
        d["roots"] = roots
        try:
            d["limit"] = int(d.get("limit") or 0)
        except Exception:
            d["limit"] = 0
        return d

    def save(self):
        try:
            # roots читаем ИЗ СПИСКА, а не из roots_var: StringVar.get() отдаёт строку
            # «('D:\\AAA', …)», и старая запись клала в настройки список букв.
            self.st.update({"roots": list(self.lst.get(0, "end")), "limit": int(self.var_limit.get())})
            SETTINGS.write_text(json.dumps(self.st, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:
            pass

    def build(self):
        # --- каркас: результат СЛЕВА, настройки СПРАВА (константа 5) ---
        U.head(self.root, TITLE,
               "Проверяет, совпадает ли внутреннее имя (CMNM) с именем файла. "
               "Класс Р: Creo и агент не нужны, только чтение.")
        left, right = U.split_result_left(self.root, right_width=440)

        # --- слева: кнопки + таблица + сводка с процентом ---
        _, btns = U.actions(left,
                            primary=(("ПРОВЕРИТЬ", self.run),),
                            secondary=(("Открыть папку отчётов",
                                        lambda: self.open_dir(eng.LOG_DIR)),
                                       ("Сохранить список (CSV)", self.save_csv)))
        self.b_find = btns[0]
        self.tree = U.result_tree(left, ("file", "internal", "where"),
                                  ("Файл", "Внутри файла", "Папка"),
                                  [260, 260, 300])
        self.tree.bind("<Double-1>", lambda e: self.open_selected())
        self.sum_var, self.set_summary = U.summary(left)

        # --- справа: вкладки по смыслу (константа 3) ---
        _nb, pages = U.tabs(right, ["Основное", "Папки"])
        top, folders = pages[0], pages[1]

        tk.Label(top, text="Лимит файлов (0 — без предела):").pack(anchor="w", padx=6, pady=(6, 2))
        self.var_limit = tk.IntVar(value=self.st["limit"])
        tk.Spinbox(top, from_=0, to=1000000, textvariable=self.var_limit,
                   width=12).pack(anchor="w", padx=6)
        tk.Label(top, text="(двойной щелчок по файлу в таблице — открыть его папку)",
                 fg="#555").pack(anchor="w", padx=6, pady=(8, 4))

        self.roots_var = tk.Variable(self.root, value=list(self.st.get("roots") or []))
        self.lst = tk.Listbox(folders, listvariable=self.roots_var, height=8, width=52)
        self.lst.pack(fill="both", expand=True, padx=6, pady=4)
        row = tk.Frame(folders)
        row.pack(fill="x", padx=6, pady=(0, 6))
        tk.Button(row, text="Добавить папку…", command=self.add_root).pack(side="left", padx=3)
        tk.Button(row, text="Убрать", command=self.del_root).pack(side="left", padx=3)
        U.readme_button(row, str(Path(__file__).resolve().parent), lambda s: None)

        # --- журнал внизу окна (каркас даёт моноширинный виджет + функцию лога) ---
        self.info, self._log = U.log_view(self.root, height=7, title="ЖУРНАЛ")

    def log(self, s):
        self._log(s)

    def open_dir(self, p):
        try:
            if p and os.path.isdir(p):
                os.startfile(p)
        except Exception as e:
            messagebox.showwarning("Не открыть", "%s\n%s" % (p, e))

    def cur_roots(self):
        """Текущий список папок ИЗ СПИСКА (roots_var.get() у Variable может отдать строку)."""
        try:
            return list(self.lst.get(0, "end"))
        except Exception:
            return []

    def selected_root(self):
        sel = self.lst.curselection()
        return self.cur_roots()[sel[0]] if sel and sel[0] < len(self.cur_roots()) else ""

    def add_root(self):
        p = filedialog.askdirectory()
        if p:
            roots = self.cur_roots()
            if p not in roots:
                roots.append(p)
                self.roots_var.set(self.cur_roots())
                self.save()

    def del_root(self):
        sel = self.lst.curselection()
        if not sel:
            return
        roots = self.cur_roots()
        roots.pop(sel[0])
        self.roots_var.set(self.cur_roots())
        self.save()
# ---------- проверка ----------
    def run(self):
        roots = self.cur_roots()
        if not roots:
            return messagebox.showwarning("Нет папок", "Добавьте хотя бы одну папку")
        self.save()
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.b_find.config(state="disabled")
        self.log("проверяю: %s" % "; ".join(roots))
        for bad in eng.missing_roots(roots):
            self.log("ВНИМАНИЕ: папки нет на диске: %s" % bad)
        # Живая находка 02.10.2026 (аудит): Tk-переменные НЕЛЬЗЯ читать из фонового потока —
        # `int(self.var_limit.get())` там падал с «RuntimeError: main thread is not in main loop».
        # Все значения с окна читаем ЗДЕСЬ, в главном потоке, и передаём в поток числами.
        limit = int(self.var_limit.get())

        def work():
            try:
                res = eng.scan(roots, limit,
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
        # ОТЧЁТ В ФАЙЛ: окно раньше писало только в своё поле, а кнопка «Открыть папку отчётов»
        # показывала папку с одними консольными отчётами (найдено 02.10.2026). Теперь след есть
        # и от окна — тот же формат, что у командной строки.
        lines = ["=== ВНУТРЕННИЕ ИМЕНА (CMNM) против имён файлов ===",
                 "окно: проверка папок: %s" % "; ".join(self.cur_roots())]
        for full, nm, fn in res["bad"]:
            lines.append("  РАСХОЖДЕНИЕ: файл «%s»  →  внутри «%s»" % (fn, nm))
        lines.append("\nфайлов просмотрено: %d; без поля CMNM: %d; расхождений: %d (%.0f с)"
                     % (res["files"], res["nofield"], len(res["bad"]), res["seconds"]))
        p = eng.write_report(lines)
        if p:
            self.log("отчёт сохранён: %s" % p)

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

# Метод show_readme удалён 04.10.2026: кнопку README теперь даёт каркас (U.readme_button),
# поэтому собственный дубль остался бы мёртвым кодом.


if __name__ == "__main__":
    # Окно создаёт САМ каркас (make_root) — раньше здесь создавался tk.Tk() вручную,
    # из-за чего окно не получало title с версией, geometry и minsize от каркаса.
    App().root.mainloop()