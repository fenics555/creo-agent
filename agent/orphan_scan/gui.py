# -*- coding: utf-8 -*-
"""orphan_scan — ОКНО поиска чертежей-сирот.

ВЕРСИЯ ОКНА: V2 (04.10.2026 — перевод на каркас ui_common).
Запуск: orphan_scan_gui.bat (или python gui.py). Класс Р: Creo не нужен (только чтение).
Нужны базы дома (`data\\agent.sqlite`, `data\\harvest.db`) и, для режима «по дому», `Z:\\PTC\\Work\\search.pro`.
Движок — `orphan_scan.py` в этой же папке (класс OrphanScanner).
"""
import csv
import json
import os
import time
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import orphan_scan as eng  # noqa: E402
import ui_common as U  # noqa: E402  (общий каркас окон дома)

# Настройки окна живут в data\ рядом с настройками остальных инструментов дома
# (закон трёх рук, манифест п.19). Старый файл в папке инструмента переносится
# автоматически при первом чтении (живая правка 02.10.2026).
SETTINGS = Path(eng.SETTINGS_PATH)
LEGACY_SETTINGS = Path(eng.LEGACY_SETTINGS)
TITLE = "ЧЕРТЕЖИ-СИРОТЫ (нет модели рядом)"


class App:
    def __init__(self, root=None):
        self.root = root or U.make_root("V2 — " + TITLE, "1080x680", minsize=(900, 560))
        self._pending = []          # сообщения, пока окно лога ещё не создано
        self.st = self.load()
        self.scanner = None
        self.build()

    def get_roots(self):
        """Список папок из окна. Живая находка 02.10.2026: `list(self.roots_var.get())`
        давал СПИСОК СИМВОЛОВ строки (обход шёл по `Scanning: (`, `Scanning: '`),
        поэтому берём элементы прямо из Listbox."""
        return list(self.lst.get(0, tk.END))

    def set_roots(self, roots):
        self.roots_var.set(list(roots))

    def load(self):
        d = {"mode": "search_pro", "roots": []}
        try:
            if not SETTINGS.exists() and LEGACY_SETTINGS.exists():
                # перенос старых настроек из папки инструмента в data\
                d.update(json.loads(LEGACY_SETTINGS.read_text(encoding="utf-8")))
                self.save(d)
                self._pending.append("настройки перенесены: %s -> %s" % (LEGACY_SETTINGS, SETTINGS))
            elif SETTINGS.exists():
                d.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
        except Exception as e:
            self._pending.append("настройки не прочитаны (%s) — беру значения по умолчанию" % e)
        return d

    def save(self, state=None):
        try:
            self.st.update(state or {"mode": self.var_mode.get(),
                                     "roots": self.get_roots()})
            SETTINGS.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS.write_text(json.dumps(self.st, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception as e:
            self._pending.append("настройки не сохранены: %s" % e)

    def build(self):
        # --- каркас: результат СЛЕВА, настройки СПРАВА (константа 5) ---
        U.head(self.root, TITLE,
               "Ищет чертежи, у которых рядом нет модели (сироты), и модели, "
               "лежащие в другом месте. Ничего не меняется — только отчёт. "
               "Класс Р: Creo не нужен; нужны базы дома agent.sqlite + harvest.db (только чтение).")
        left, right = U.split_result_left(self.root, right_width=420)

        _, btns = U.actions(left,
                            primary=(("НАЙТИ СИРОТ", self.run),),
                            secondary=(("СТОП", self.stop),
                                       ("Последний отчёт", self.open_report),
                                       ("Папка отчётов", lambda: self.open_dir(eng.REPORT_DIR)),
                                       ("Папка логов", lambda: self.open_dir(eng.LOG_DIR)),
                                       ("Сохранить список (CSV)", self.save_csv)))
        self.b_run, self.b_stop = btns[0], btns[1]
        self.b_stop.config(state="disabled")
        self.sum_var, self.set_summary = U.summary(left)

        self.tree = U.result_tree(left, ("cls", "file", "folder"),
                                  ("Класс", "Чертёж", "Папка"), [150, 420, 460])
        self.tree.bind("<Double-1>", lambda e: self.open_selected())
        self.tree.tag_configure("orphan", background="#ffe3e3")
        self.tree.tag_configure("elsewhere", background="#fff8dc")

        # --- справа: вкладки по смыслу (константа 3) ---
        _nb, pages = U.tabs(right, ["Что проверять", "Папки"])
        top, folders = pages[0], pages[1]

        self.var_mode = tk.StringVar(value=self.st["mode"])
        tk.Radiobutton(top, text="весь дом — все папки из Z:\\PTC\\Work\\search.pro",
                       bg=U.BG, variable=self.var_mode, value="search_pro",
                       command=self.toggle).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        tk.Radiobutton(top, text="только выбранные папки:", bg=U.BG, variable=self.var_mode,
                       value="custom", command=self.toggle).grid(row=1, column=0, sticky="w", padx=8)
        tk.Label(top, text="осмотр идёт по подпапкам; ничего не меняется — только отчёт; "
                           "нужны пути Creo: %s" % eng.SEARCH_PRO, bg=U.BG, fg=U.MUTED,
                 wraplength=360, justify="left").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        row = tk.Frame(top, bg=U.BG)
        row.grid(row=3, column=0, sticky="ew", padx=8, pady=6)
        U.readme_button(row, str(HERE), self.log)

        self.roots_var = tk.Variable(self.root, value=list(self.st.get("roots") or []))
        self.lst = tk.Listbox(folders, listvariable=self.roots_var, height=10, width=48)
        self.lst.pack(fill="both", expand=True, padx=6, pady=4)
        frow = tk.Frame(folders, bg=U.BG)
        frow.pack(fill="x", padx=6, pady=(0, 6))
        tk.Button(frow, text="Добавить папку…", command=self.add_root).pack(side="left", padx=3)
        tk.Button(frow, text="Убрать", command=self.del_root).pack(side="left", padx=3)
        self.toggle()

        # --- журнал внизу окна (каркас: моноширинный виджет + функция лога) ---
        self.info, self._log = U.log_view(self.root, height=7, title="ЖУРНАЛ")
        for s in self._pending:      # отдать сообщения, накопленные до создания виджета
            self.log(s)
        self._pending = []
        self.log("настройки: %s" % SETTINGS)
        self.log("базы: agent.sqlite + harvest.db (только чтение); пути Creo: %s" % eng.SEARCH_PRO)

    def toggle(self):
        state = "normal" if self.var_mode.get() == "custom" else "disabled"
        self.lst.config(state=state)
        self.save()

    def log(self, s):
        self._log(s)

    def open_dir(self, p):
        try:
            if p and os.path.isdir(p):
                os.startfile(p)
        except Exception as e:
            messagebox.showwarning("Не открыть", "%s\n%s" % (p, e))

    def open_report(self):
        try:
            files = sorted(Path(eng.REPORT_DIR).glob("%s_*.md" % eng.REPORT_PREFIX))
            if not files:
                # старые отчёты спеки 113 остаются доступными до их истечения
                files = sorted(Path(eng.REPORT_DIR).glob("REPORT_spec113_local_leg_*.md"))
            if not files:
                return messagebox.showinfo("Отчётов нет", "Сначала прогон")
            os.startfile(str(files[-1]))
        except Exception as e:
            messagebox.showerror("Не открыть", str(e))

    def add_root(self):
        p = filedialog.askdirectory()
        if p:
            roots = self.get_roots()
            if p not in roots:
                roots.append(p)
                self.set_roots(roots)
                self.save()

    def del_root(self):
        sel = self.lst.curselection()
        if not sel:
            return
        roots = self.get_roots()
        roots.pop(sel[0])
        self.set_roots(roots)
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
            roots = self.get_roots()          # было list(self.roots_var.get()) — список символов
            if not roots:
                return messagebox.showwarning("Нет папок", "Добавьте хотя бы одну папку")
        self.save()
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.b_run.config(state="disabled")
        self.b_stop.config(state="normal")
        self._t0 = time.time()
        self.sum_var.set("идёт осмотр…")

        # Тяжёлое — обход дерева — в потоке каркаса. Свой сканер нужен прогону (в нём
        # счётчики и флаг остановки), поэтому поток поднимаем каркасом, а не threading.
        self.scanner = eng.OrphanScanner()   # новый экземпляр на каждый прогон (счётчики сбрасываются)
        scanner = self.scanner
        self.log("осмотр запущен: %s" % (("папки: %s" % "; ".join(roots)) if roots
                                         else "весь дом по %s" % eng.SEARCH_PRO))

        def work():
            scanner.scan(roots=roots, progress=lambda s: self.root.after(0, self.log, s))

        U.run_in_thread(self.root, work, on_done=self.done,
                        on_error=lambda e: (self.log("ошибка осмотра: %s" % e),
                                            messagebox.showerror("Ошибка осмотра", str(e)),
                                            self.b_run.config(state="normal"),
                                            self.b_stop.config(state="disabled")),
                        log=self.log)

    def stop(self):
        # Мягкая остановка: флаг в движке. Живая проверка 02.10.2026: присваивание
        # scanner.roots = [] цикл `for root in self.roots` НЕ прерывало
        # (обойдено 3 корня из 3), поэтому флаг проверяется в теле обхода.
        if self.scanner:
            self.scanner.request_stop()
            self.log("остановка: обход прекращается на следующей папке, "
                     "отчёт по найденному будет записан")
        self.b_stop.config(state="disabled")

    def done(self, _res=None):
        # run_in_thread зовёт on_done(payload) — отсюда _res=None: старый вызов без аргумента
        # тоже остаётся рабочим (жёсткое требование каркаса, а не вкусовщина).
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
        # Сводка каркаса с процентом: «соответствие» = доля чертёжей, у которых модель рядом есть.
        total = s.stats["total_drawings"]
        ok_ = s.stats["not_orphan"]
        self.set_summary(total, ok_, s.stats["orphan"] + s.stats["model_elsewhere"],
                         "модель в другом месте: %d" % s.stats["model_elsewhere"])
        self.log("чертежей: %d | не сирот: %d | модель в другом месте: %d | СИРОТ: %d | за %.1f с"
                 % (total, ok_, s.stats["model_elsewhere"], s.stats["orphan"],
                    time.time() - getattr(self, "_t0", time.time())))
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

# Метод show_readme удалён 04.10.2026: кнопку README теперь даёт каркас (U.readme_button),
# поэтому собственный дубль остался бы мёртвым кодом.


if __name__ == "__main__":
    # Окно создаёт САМ каркас (make_root) — раньше здесь создавался tk.Tk() вручную.
    App().root.mainloop()