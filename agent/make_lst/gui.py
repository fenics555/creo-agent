# -*- coding: utf-8 -*-
"""make_lst — ОКНО сборки файла ограничений параметров (list.lst).

ВЕРСИЯ ОКНА: V2 (04.10.2026 — перевод на каркас ui_common).
Запуск: make_lst_gui.bat. Класс Р: Creo и агент не нужны.
Движок — `make_lst.py` в этой же папке (build / write_file / check_against_refs).
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
import make_lst as eng  # noqa: E402
import ui_common as U  # noqa: E402  (общий каркас окон дома)

TITLE = "ОГРАНИЧЕНИЯ ПАРАМЕТРОВ (list.lst)"
DEFAULTS = {"target": "", "refs": ""}


class App:
    def __init__(self, root=None):
        self.root = root or U.make_root("V2 — " + TITLE, "1020x660", minsize=(900, 560))
        self.st = U.load_settings("make_lst", DEFAULTS)
        self.st.setdefault("target", eng.TARGET)
        self.st.setdefault("refs", "")
        # Живая находка 03.10.2026 (аудит): окно не писало журнал ВООБЩЕ — след оставался только
        # от консольных прогонов, и по журналу нельзя было понять, что файл трогали из окна.
        # Теперь окно и консоль пишут в ОДИН и тот же журнал (eng.make_logger).
        self.flog, self.logpath = eng.make_logger()
        self.flog("окно make_lst запущено · цель по умолчанию: %s" % eng.TARGET)
        self.build()

    def save(self):
        """Настройки окна — каркасом (data\\make_lst_settings.json): путь цели и refs."""
        out = U.save_settings("make_lst", {"target": self.var_target.get(),
                                            "refs": self.var_refs.get()})
        if str(out).startswith("ошибка"):
            self.log("настройки не сохранены: %s" % out)

    def build(self):
        # --- каркас: результат СЛЕВА, настройки СПРАВА (константа 5) ---
        U.head(self.root, TITLE,
               "Собирает файл ограничений параметров (list.lst) и сверяет значения с отчётом "
               "чесалки. Класс Р: Creo и агент не нужны. Журнал окна и консоли — один и тот же.")
        left, right = U.split_result_left(self.root, right_width=380)

        # ВАЖНО: U.actions возвращает (рамка, кнопки). Раньше здесь стояло `_, btns = U.actions(...)`,
        # а в коде кнопка «ЗАПИСАТЬ» добавлялась в переменную с КНОПКАМИ — и падало
        # «AttributeError: 'list' object has no attribute 'tk'». Кнопка пишется в РАМКУ.
        box, btns = U.actions(left,
                              primary=(("ПОКАЗАТЬ (ничего не пишем)", self.preview),),
                              secondary=(("Показать текущий файл", self.show_current),
                                         ("Открыть папку файла", self.open_dir_cur)))
        self.b_preview = btns[0]
        self.b_write = tk.Button(box, text="ЗАПИСАТЬ ФАЙЛ (с бэкапом)", width=26,
                                 bg="#c0392b", fg="white", font=("Segoe UI", 9, "bold"),
                                 command=self.write)
        self.b_write.pack(side="left", padx=3)

        tk.Label(left, text="ЧТО БУДЕТ ЗАПИСАНО / ЖУРНАЛ", bg=U.BG, fg=U.FG,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 0))
        self.info, self._log = U.log_view(left, height=14, title="СОДЕРЖИМОЕ ФАЙЛА")
        self.sum_var, self.set_summary = U.summary(left)

        # --- справа: вкладка с файлами (константа 3) ---
        _nb, pages = U.tabs(right, ["Файлы"])
        top = pages[0]

        tk.Label(top, text="Файл ограничений:", bg=U.BG).grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        self.var_target = tk.StringVar(value=self.st.get("target") or eng.TARGET)
        tk.Entry(top, textvariable=self.var_target).grid(row=1, column=0, sticky="ew", padx=8)
        tk.Button(top, text="Обзор…", command=self.browse_target).grid(
            row=2, column=0, sticky="w", padx=8, pady=6)

        tk.Label(top, text="Отчёт чесалки для сверки (не обязательно):", bg=U.BG).grid(
            row=3, column=0, sticky="w", padx=8)
        self.var_refs = tk.StringVar(value=self.st.get("refs") or "")
        tk.Entry(top, textvariable=self.var_refs).grid(row=4, column=0, sticky="ew", padx=8)
        tk.Button(top, text="Обзор…", command=self.browse_refs).grid(
            row=5, column=0, sticky="w", padx=8, pady=6)

        tk.Label(top, text="refs.txt делает `creo_comb.bat refs <папка>` — по нему видно, "
                           "что значения параметров совпадают с шаблонами. Оба пути "
                           "помнятся между запусками: data\\make_lst_settings.json.",
                 bg=U.BG, fg=U.MUTED, wraplength=320, justify="left").grid(
            row=6, column=0, sticky="w", padx=8)
        row = tk.Frame(top, bg=U.BG)
        row.grid(row=7, column=0, sticky="ew", padx=8, pady=8)
        U.readme_button(row, str(HERE), self.log)
        top.columnconfigure(0, weight=1)

    # ---------- вспомогательное ----------
    def log(self, s):
        self._log(s)
        self.flog(s)              # и в журнал на диск — окно больше не работает «невидимо»

    def open_dir_cur(self):
        self.open_dir(os.path.dirname(self.var_target.get()))

    def open_dir(self, p):
        try:
            if p and os.path.isdir(p):
                os.startfile(p)
        except Exception as e:
            messagebox.showwarning("Не открыть", "%s\n%s" % (p, e))

    def browse_target(self):
        p = filedialog.asksaveasfilename(defaultextension=".lst", initialfile="list.lst")
        if p:
            self.var_target.set(p)

    def browse_refs(self):
        p = filedialog.askopenfilename(filetypes=[("Отчёт чесалки", "*.txt"), ("Все файлы", "*.*")])
        if p:
            self.var_refs.set(p)

    def clear(self):
        """Очистка панели каркаса: log_view отдаёт (рамка, функция), а не Text —
        писать в рамку нельзя, поэтому чистим через delete того же виджета."""
        try:
            self.info.winfo_children()[0].delete("1.0", "end")
        except Exception:
            pass

    def preview(self):
        self.clear()
        _t0 = time.time()
        self.save()
        target = self.var_target.get()
        refs = self.var_refs.get()
        self.log("цель: %s" % target)
        self.b_preview.config(state="disabled")

        # Тяжёлое (сборка ограничений + сверка с чесалкой) — в потоке каркаса. Tk-переменные
        # из потока не читаем: пути забираем ЗДЕСЬ и передаём строками.
        def work():
            lines = []
            if refs:
                eng.check_against_refs(refs, lines.append)
                lines.append("")
            lines.append(eng.build())
            return lines

        def done(res):
            for s in res:
                for ln in str(s).splitlines():
                    self.log(ln)
            self.sum_var.set("показано за %.1f с (на диск ничего не записано); журнал: %s"
                             % (time.time() - _t0, self.logpath))
            self.b_preview.config(state="normal")

        U.run_in_thread(self.root, work, on_done=done,
                        on_error=lambda e: (self.log("не собрать: %s" % e),
                                            self.b_preview.config(state="normal")),
                        log=self.log)

    def show_current(self):
        self.clear()
        p = self.var_target.get()
        if not os.path.exists(p):
            self.log("файла ещё нет: %s" % p)
            return
        try:
            with open(p, "rb") as f:
                data = f.read()
            self.log("текущий файл: %s (%d байт, cp1251)" % (p, len(data)))
            self.log("")
            self.log(data.decode("cp1251"))
        except Exception as e:
            self.log("не прочитать: %s" % e)

    def write(self):
        p = self.var_target.get()
        if not messagebox.askyesno("Подтверждение",
                                   "Записать файл ограничений?\n%s\n\nПрежний файл уедет в _pre рядом."
                                   % p):
            return
        self.clear()
        self.save()
        _t0 = time.time()
        self.b_write.config(state="disabled")

        def work():
            return eng.build()

        def done(res):
            eng.write_file(p, res[0], self.log)
            self.sum_var.set("файл записан: %s (за %.1f с)" % (p, time.time() - _t0))
            self.b_write.config(state="normal")

        U.run_in_thread(self.root, work, on_done=done,
                        on_error=lambda e: (self.log("ошибка записи: %s" % e),
                                            messagebox.showerror("Ошибка записи", str(e)),
                                            self.b_write.config(state="normal")),
                        log=self.log)


# Метод show_readme удалён 04.10.2026: кнопку README теперь даёт каркас (U.readme_button),
# поэтому собственный дубль остался бы мёртвым кодом.


if __name__ == "__main__":
    # Окно создаёт САМ каркас (make_root) — раньше здесь создавался tk.Tk() вручную.
    App().root.mainloop()