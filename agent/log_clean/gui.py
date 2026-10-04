# -*- coding: utf-8 -*-
"""log_clean — ОКНО уборки логов (настройки + план + уборка). Класс Р: Creo и агент не нужны.

ВЕРСИЯ ОКНА: V2 (04.10.2026 — перевод на каркас ui_common).
Запуск: log_clean_gui.bat  (или python gui.py)
Настройки окна — через каркас, `data\\log_clean_settings.json`; сроки по каталогам —
D:\\AI\\log\\retention.json (тот же файл читает ночной цикл агента, поэтому цифры одни на всех).
"""
import os
import time
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog

PROG_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROG_DIR))
sys.path.insert(0, str(PROG_DIR.parent))
import engine  # noqa: E402
import ui_common as U  # noqa: E402  (общий каркас окон дома)

TITLE = "УБОРКА ЛОГОВ дома"
DEFAULTS = {"root": str(engine.LOG_ROOT), "days": engine.DEFAULT_DAYS,
            "mode": "trash", "trash_days": 7}


class App:
    def __init__(self, root=None):
        self.root = root or U.make_root("V2 — " + TITLE, "1020x640", minsize=(900, 560))
        self.st = self.load()
        self.plan = []
        self.build()
        self.refresh()

    # ---------- настройки ----------
    def load(self):
        # Путь и запись — через каркас (тот же data\log_clean_settings.json, что был
        # прописан константой; меняется только способ, чтобы окно не вело свою копию пути).
        return U.load_settings("log_clean", DEFAULTS)

    def save(self):
        # ГРАБЛЯ МОЕЙ ПЕРВОЙ ПРАВКИ (04.10.2026): после перевода `save` осталась в старом виде
        # и писала `self.st` как есть — то есть сохраняла бы ПУСТЫЕ значения, потому что
        # значения живут в Tk-переменных окна. Значит: сохраняем то, что видит человек.
        try:
            self.st.update(self.cur())
        except (tk.TclError, ValueError):
            return          # окно ещё не собрано (save зовут радиокнопки при создании)
        out = U.save_settings("log_clean", self.st)
        if str(out).startswith("ошибка"):
            self.log("настройки не сохранены: %s" % out)

    # ---------- интерфейс ----------
    def build(self):
        # --- каркас: план СЛЕВА, настройки СПРАВА (константа 5) ---
        U.head(self.root, TITLE,
               "Смотрит каталоги логов, сверяет возраст файлов со сроком хранения и убирает старое. "
               "Сроки лежат в D:\\AI\\log\\retention.json — тот же файл читает ночной цикл агента. "
               "По умолчанию ничего не удаляется: старое уезжает в корзину. Класс Р: Creo не нужен.")
        left, right = U.split_result_left(self.root, right_width=380)

        _, btns = U.actions(left,
                            primary=(("УБРАТЬ СТАРОЕ", self.run_clean),),
                            secondary=(("ОБНОВИТЬ ПЛАН", self.refresh),
                                       ("Открыть папку логов", lambda: self.open_dir(self.var_root.get())),
                                       ("Открыть корзину", self.open_trash)))
        self.b_run = btns[0]
        self.b_run.config(state="disabled")

        self.tree = U.result_tree(left, ("folder", "files", "days", "old", "mb", "locked", "oldest", "newest"),
                                  ("Каталог", "Файлов", "Срок дн.", "Старше", "МБ", "Занятых",
                                   "Самый старый", "Последний"),
                                  [170, 70, 80, 70, 70, 80, 110, 110])
        self.tree.bind("<Double-1>", self.edit_days)
        self.sum_var, self.set_summary = U.summary(left)

        # --- справа: вкладки по смыслу (константа 3) ---
        _nb, pages = U.tabs(right, ["Корень и сроки", "Режим"])
        top, mode = pages[0], pages[1]

        tk.Label(top, text="Корень логов:", bg=U.BG).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        self.var_root = tk.StringVar(value=self.st["root"])
        tk.Entry(top, textvariable=self.var_root).grid(row=1, column=0, columnspan=2, sticky="ew", padx=8)
        tk.Button(top, text="Обзор", command=self.browse).grid(row=2, column=0, sticky="w", padx=8, pady=6)
        tk.Label(top, text="Срок по умолчанию (дней):", bg=U.BG).grid(
            row=3, column=0, sticky="w", padx=8)
        self.var_days = tk.IntVar(value=self.st["days"])
        tk.Spinbox(top, from_=1, to=3650, textvariable=self.var_days, width=8).grid(
            row=3, column=1, sticky="w", padx=6)
        tk.Label(top, text="двойной щелчок по строке в таблице — срок ИМЕННО этого каталога "
                           "(пишется в retention.json)", bg=U.BG, fg=U.MUTED,
                 wraplength=320, justify="left").grid(row=4, column=0, columnspan=2,
                                                      sticky="w", padx=8)
        top.columnconfigure(0, weight=1)

        tk.Label(mode, text="Что делать со старым:", bg=U.BG).grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        self.var_mode = tk.StringVar(value=self.st["mode"])
        tk.Radiobutton(mode, text="уносить в корзину (можно вернуть)", bg=U.BG,
                       variable=self.var_mode, value="trash", command=self.save).grid(
            row=1, column=0, sticky="w", padx=8)
        tk.Radiobutton(mode, text="удалять навсегда", bg=U.BG, variable=self.var_mode,
                       value="delete", command=self.save).grid(row=2, column=0, sticky="w", padx=8)
        tk.Label(mode, text="Держать корзину (дней):", bg=U.BG).grid(
            row=3, column=0, sticky="w", padx=8, pady=(10, 2))
        self.var_trash = tk.IntVar(value=self.st["trash_days"])
        tk.Spinbox(mode, from_=0, to=365, textvariable=self.var_trash, width=8).grid(
            row=3, column=1, sticky="w", padx=6)
        row = tk.Frame(mode, bg=U.BG)
        row.grid(row=4, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
        U.readme_button(row, str(PROG_DIR), self.log)

        # --- журнал (каркас: моноширинный виджет + функция лога) ---
        self.info, self._log = U.log_view(self.root, height=6, title="ЖУРНАЛ")

    def log(self, s):
        self._log(s)

    def open_trash(self):
        self.open_dir(str(Path(self.var_root.get()) / "_trash_clean"))

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
    def cur(self):
        """Значения настроек ИЗ ОКНА — единственный источник для save()."""
        return {"root": self.var_root.get(), "days": int(self.var_days.get()),
                "mode": self.var_mode.get(), "trash_days": int(self.var_trash.get())}

    def refresh(self):
        # Тяжёлое (обход дерева логов) — в потоке каркаса. Раньше scan выполнялся в главном
        # потоке: на живом D:\AI\log (21 каталог, тысячи файлов) окно подвисало на секунды.
        # Tk-переменные из потока не читаем — числа забираем ЗДЕСЬ, в главном потоке.
        self.st.update(self.cur())
        out = U.save_settings("log_clean", self.st)
        if str(out).startswith("ошибка"):
            self.log("настройки не сохранены: %s" % out)
        root_dir = self.st["root"]
        days = self.st["days"]
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.log("сканирую: %s (срок %d дн.)" % (root_dir, days))
        U.run_in_thread(self.root,
                        lambda: engine.scan(root_dir, days),
                        on_done=self.show_plan,
                        on_error=lambda e: self.log("план не построен: %s" % e),
                        log=self.log)

    def show_plan(self, plan):
        self.plan = plan
        tot_old = tot_mb = tot_files = 0
        for r in plan:
            self.tree.insert("", "end", values=(r["folder"], r["files"], r["days"], r["old"],
                                                round(r["old_bytes"] / 1048576, 1), r["locked"],
                                                r["oldest"], r["newest"]),
                             tags=("warn" if r["old"] else "ok",))
            tot_old += r["old"]
            tot_mb += r["old_bytes"]
            tot_files += r["files"]
        # Сводка каркаса: «соответствие» здесь = доля файлов, НЕ попавших под уборку.
        self.set_summary(tot_files, tot_files - tot_old, tot_old,
                         "каталогов: %d" % len(plan))
        self.b_run.config(state="normal" if tot_old else "disabled")
        self.log("план: каталогов %d, файлов %d, старше срока %d (%.1f МБ)"
                 % (len(plan), tot_files, tot_old, tot_mb / 1048576))

    def edit_days(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        name = self.tree.item(sel[0], "values")[0]
        cur = self.tree.item(sel[0], "values")[2]
        d = simpledialog.askinteger("Срок хранения", "Сколько дней держать каталог «%s»?" % name,
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
        # Уборка — тяжёлая (перенос/удаление файлов), поэтому в потоке каркаса. Значения
        # окна забираем ДО старта потока числами.
        root_dir = self.var_root.get()
        days = int(self.var_days.get())
        trash_days = int(self.var_trash.get())
        self.b_run.config(state="disabled")
        self.log("убираю: корень %s, срок %d дн., режим %s" % (root_dir, days, mode))

        def work():
            rep = engine.clean(root_dir, mode, days)
            return rep, engine.trash_cleanup(trash_days, root_dir)

        def done(res):
            rep, gone = res
            self.log("сделано: в корзину %d, удалено %d, пропущено %d, освобождено %.1f МБ (за %.1f с)"
                     % (len(rep["перенесено"]), len(rep["удалено"]), len(rep["пропущено"]),
                        rep["байт"] / 1048576, time.time() - _t0))
            for s in rep["пропущено"][:10]:
                self.log("   пропущено: %s" % s)
            for g in gone:
                self.log("корзина: убран старый каталог %s" % g)
            self.refresh()

        U.run_in_thread(self.root, work, on_done=done,
                        on_error=lambda e: (self.log("уборка не выполнена: %s" % e),
                                            self.b_run.config(state="normal")),
                        log=self.log)

# Метод show_readme удалён 04.10.2026: кнопку README теперь даёт каркас (U.readme_button),
# поэтому собственный дубль остался бы мёртвым кодом.


if __name__ == "__main__":
    # Окно создаёт САМ каркас (make_root) — раньше здесь создавался tk.Tk() вручную.
    App().root.mainloop()