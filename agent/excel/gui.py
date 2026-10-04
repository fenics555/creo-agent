# -*- coding: utf-8 -*-
"""excel — ОКНО просмотра спецификации XLSX (что реально записано в файле).

ВЕРСИЯ ОКНА: V2 (04.10.2026 — перевод на каркас ui_common).
ЖИВАЯ НАХОДКА 04.10.2026 (перевод на каркас): была константа `SETTINGS = .../excel/gui_settings.json`,
которую НИКТО НИКОГДА не читал и не писал — окно не помнило последний файл между запусками.
Теперь настройки ведёт каркас (`data\\excel_settings.json`), и в них лежит путь к спецификации.
Запуск: excel_gui.bat. Класс Р: Creo и агент не нужны, только чтение.
Разбор делает `excel_import.read_specification_xlsx` из этой же папки.
Запись XLSX (сборка спецификации) делает агент (`spec_tools.py`, `excel_export.py`) — в окне её нет,
чтобы не выдумывать данные: окно ЧИТАЕТ и показывает.
"""
import os
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import excel_import as imp  # noqa: E402
import ui_common as U  # noqa: E402  (общий каркас окон дома)

TITLE = "СПЕЦИФИКАЦИЯ XLSX — просмотр"
DEFAULTS = {"last_path": ""}


class App:
    def __init__(self, root=None):
        self.root = root or U.make_root("V2 — " + TITLE, "1080x640", minsize=(900, 560))
        self.st = self.load()
        self.rows = []
        self.build()

    def load(self):
        return U.load_settings("excel", DEFAULTS)

    def build(self):
        # --- каркас: результат СЛЕВА, настройки СПРАВА (константа 5) ---
        U.head(self.root, TITLE,
               "Читает файл спецификации XLSX и показывает, что реально в нём записано. "
               "Столбцы «Обозначение» и «Наименование», разделы — по названиям ГОСТ. "
               "Класс Р: Creo и агент не нужны, только чтение; запись XLSX делает агент.")
        left, right = U.split_result_left(self.root, right_width=400)

        _, btns = U.actions(left,
                            primary=(("ПОКАЗАТЬ", self.run),),
                            secondary=(("Открыть файл", self.open_file),
                                       ("Открыть папку", self.open_dir_cur),
                                       ("Обзор…", self.browse)))
        self.b_run = btns[0]

        # --- слева: таблица спецификации. Колонки приходят из файла, поэтому дерево
        # создаётся каркасом с одной служебной колонкой и перестраивается в run(). ---
        self.tree = U.result_tree(left, ("col1",), ("(файл не прочитан)",), [600])
        self.tree.bind("<Double-1>", lambda e: self.open_file())

        # --- справа: вкладка с файлом (константа 3) ---
        _nb, pages = U.tabs(right, ["Файл"])
        top = pages[0]

        tk.Label(top, text="Файл спецификации:", bg=U.BG).grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        self.var_path = tk.StringVar(value=self.st.get("last_path", ""))
        tk.Entry(top, textvariable=self.var_path).grid(row=1, column=0, sticky="ew", padx=8)
        tk.Button(top, text="Обзор…", command=self.browse).grid(
            row=2, column=0, sticky="w", padx=8, pady=6)
        tk.Label(top, text="Путь помнится между запусками: настройки окна в "
                           "data\\excel_settings.json (через каркас).",
                 bg=U.BG, fg=U.MUTED, wraplength=340, justify="left").grid(
            row=3, column=0, sticky="w", padx=8)
        row = tk.Frame(top, bg=U.BG)
        row.grid(row=4, column=0, sticky="ew", padx=8, pady=6)
        U.readme_button(row, str(HERE), self.log)
        top.columnconfigure(0, weight=1)

        # --- сводка и журнал (каркас: строка с процентом + моноширинный лог) ---
        self.sum_var, self.set_summary = U.summary(left)
        self.info, self._log = U.log_view(self.root, height=6, title="ЖУРНАЛ")

    def log(self, s):
        self._log(s)

    def open_dir_cur(self):
        self.open_dir(os.path.dirname(self.var_path.get()))

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
        # ЖИВАЯ НАХОДКА 04.10.2026: чтение XLSX идёт в потоке каркаса (U.run_in_thread).
        # Раньше разбор файла выполнялся В ГЛАВНОМ потоке — на большой спецификации окно
        # белело и переставало отвечать. Tk-переменные из потока не читаем: путь забираем
        # ЗДЕСЬ, числами передаём в поток (та же грабля, что в cmnm_scan).
        self.save_path(p)
        _t0 = time.time()
        self.b_run.config(state="disabled")
        self.log("читаю: %s" % p)

        def work():
            with open(p, "rb") as f:
                data = f.read()
            return imp.read_specification_xlsx(data)

        U.run_in_thread(self.root, work,
                        on_done=lambda res: self.show(res, p, _t0),
                        on_error=lambda e: self.failed(e),
                        log=self.log)

    def save_path(self, p):
        out = U.save_settings("excel", {"last_path": p})
        if str(out).startswith("ошибка"):
            self.log("путь не сохранён: %s" % out)

    def failed(self, e):
        self.b_run.config(state="normal")
        messagebox.showerror("Не прочитать спецификацию", str(e).splitlines()[-1])

    def show(self, res, p, _t0):
        sections, rows = res
        self.rows = rows
        keys = []
        for r in rows:
            for k in r.keys():
                if k not in keys:
                    keys.append(k)
        self.tree.delete(*self.tree.get_children())
        # ЖИВАЯ НАХОДКА 04.10.2026: колонки у дерева каркаса задаются созданием, а в файле
        # их набор неизвестен заранее. Поэтому перестраиваем набор на том же Treeview —
        # это поддерживается Tk и не ломает признак `show="headings"`, который дал каркас.
        self.tree["columns"] = keys or ("col1",)
        for k in (keys or ["(файл не прочитан)"]):
            self.tree.heading(k, text=k)
            self.tree.column(k, width=140, anchor="w")
        for r in rows:
            self.tree.insert("", "end", values=[r.get(k, "") for k in keys])
        # Сводка каркаса считает «соответствие» — здесь оно означает «строк с обозначением».
        with_design = sum(1 for r in rows if str(r.get("Обозначение", "")).strip())
        pct = self.set_summary(len(rows), with_design, len(rows) - with_design,
                               "разделов: %d" % len(sections))
        self.log("файл: %s | разделов: %d | строк: %d | колонок: %d | за %.1f с"
                 % (os.path.basename(p), len(sections), len(rows), len(keys),
                    time.time() - _t0))
        self.log("строк с обозначением: %d (%.0f %%)" % (with_design, pct or 0.0))
        self.log("разделы: %s" % ", ".join(sections))
        self.log("строк: %d; колонки: %s" % (len(rows), ", ".join(keys)))
        self.b_run.config(state="normal")

# Метод show_readme удалён 04.10.2026: кнопку README теперь даёт каркас (U.readme_button),
# поэтому собственный дубль остался бы мёртвым кодом.


if __name__ == "__main__":
    # Окно создаёт САМ каркас (make_root) — раньше здесь создавался tk.Tk() вручную.
    App().root.mainloop()