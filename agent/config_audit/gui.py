# -*- coding: utf-8 -*-
"""config_audit — ОКНО проверки путей config.pro.

Запуск: config_audit_gui.bat. Класс Р: Creo и агент не нужны, только чтение.
Движок — `config_audit.py` в этой же папке (функция audit).
"""
import csv
import json
import os
import sys
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config_audit as eng  # noqa: E402
import ui_common as U  # noqa: E402  (волна 1: общий каркас окон, 6 дизайн-констант)

# Настройки окна — в data\ рядом с остальными (манифест п.19). До 02.10.2026 окно их не имело
# вовсе: выбранный config.pro терялся при закрытии, это был самый частый сценарий — открыть,
# посмотреть, закрыть, снова выбирать.
SETTINGS = Path(r"D:\AI\tools\agent\data\config_audit_settings.json")
# Известные места config.pro — 03.10.2026: список даёт ОБЩИЙ поиск дома
# (`agent\agent\creo_path.config_paths()`), он же отсеивает несуществующие пути.
# Раньше список был зашит здесь, и при переезде домена окно предлагало мёртвые пути.
KNOWN = eng.BOOT.config_paths() or [r"Z:\PTC\CREO-START\START-STD\config.pro"]
DEFAULTS = {"last_config": eng.BOOT.config_path() or KNOWN[0]}
# Подстановки переменных Creo (манифест п.19: одна база — одно место). Пути к УСТАНОВКЕ
# здесь больше не хранятся: их даёт общий поиск `creo_path.find()` (бат запуска → реестр →
# диск). Хранить их в настройках = хранить версию, которая протухнет при переезде домена.
CREO_VARS = {"$PROSTD": r"Z:\PTC\CREO-START\НАСТРОЙКИ"}


class App:
    def __init__(self, root=None):
        self.root = root or U.make_root("V1 — ПУТИ CONFIG.PRO — что есть, чего нет",
                                        "1020x620", minsize=(900, 560))
        self.root.minsize(900, 560)
        self.res = None
        self._pending = []
        self.st = self.load_settings()
        self.build()

    def load_settings(self):
        d = dict(DEFAULTS)
        try:
            if SETTINGS.exists():
                d.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
        except Exception as e:
            self._pending.append("настройки не прочитаны (%s) — беру значения по умолчанию" % e)
        return d

    def save_settings(self):
        try:
            self.st["creo_vars"] = dict(CREO_VARS)
            SETTINGS.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS.write_text(json.dumps(self.st, ensure_ascii=False, indent=1),
                                encoding="utf-8")
        except Exception as e:
            self._pending.append("настройки не сохранены: %s" % e)

    def build(self):
        # --- каркас ui_common: результат СЛЕВА, настройки СПРАВА (константа 5) ---
        U.head(self.root, "V1 — ПУТИ CONFIG.PRO: что есть, чего нет",
               "Проверяются пути вида `C:\\…`, `\\\\сервер\\…`, `$PRO_DIRECTORY`, "
               "`$CREO_COMMON_FILES`, `$PROSTD`; у Creo-файлов учитывается версия (`.prt` → `.prt.1`). "
               "Класс Р: Creo и агент не нужны, только чтение.")
        left, right = U.split_result_left(self.root, right_width=470)

        # --- слева: результат (дерево) + сводка с процентом соответствия (константа 4) ---
        U.actions(left, primary=(("ПРОВЕРИТЬ", self.run),),
                  secondary=(("Открыть файл", self.open_file),
                             ("Открыть папку",
                              lambda: self.open_dir(os.path.dirname(self.var_path.get())))))
        self.tree = U.result_tree(left, ("st", "line", "opt", "value", "path"),
                                  ("Статус", "Строка", "Настройка",
                                   "Как записано в конфиге", "Путь на диске"),
                                  [60, 60, 170, 260, 300])
        self.sum_var, self.set_summary = U.summary(left)

        # --- справа: вкладки по смыслу (константа 3) ---
        nb, pages = U.tabs(right, ["Основное", "Дополнительно"])

        # основная вкладка: ТАБЛИЦА настроек Option|Value|Status|Description (константа 1)
        self.var_path = tk.StringVar(value=str(self.st.get("last_config") or eng.CONFIG))
        spec = [{"option": "last_config", "value": self.var_path.get(),
                 "desc": "какой config.pro проверяем", "default": DEFAULTS["last_config"]}]
        self.tbl = U.SettingsTable(pages[0], spec, log=self.log, on_apply=self._on_apply)
        self.tbl.saved = dict(self.tbl.vals)
        tk.Label(pages[0], text="Известные места config.pro: " + " | ".join(KNOWN[:3]),
                 bg=U.BG, fg=U.MUTED, font=("Segoe UI", 8), wraplength=440,
                 justify="left").pack(anchor="w", padx=8, pady=2)
        tk.Button(pages[0], text="Обзор…", command=self.browse).pack(anchor="e", padx=8)

        # дополнительная вкладка: второстепенные кнопки (сложное — за «Дополнительно»)
        extra = pages[1]
        for txt, cmd in (("Сохранить отчёт (CSV)", self.save_csv),
                         ("Папка отчётов", lambda: self.open_dir(eng.REPORT_DIR)),
                         ("Папка логов", lambda: self.open_dir(eng.LOG_DIR))):
            tk.Button(extra, text=txt, command=cmd).pack(anchor="w", padx=8, pady=3)
        U.readme_button(extra, Path(__file__).resolve().parent, self.log)

        # журнал внизу
        # журнал внизу: log_view отдаёт (рамка, ФУНКЦИЯ log), а не виджет
        self._log_box, self._log_write = U.log_view(self.root, height=6)
        self.status = U.statusbar(self.root)
        for s in self._pending:        # сообщения, накопленные до создания виджета лога
            self.log(s)
        self._pending = []
        self.log("настройки: %s" % SETTINGS)
        self.log("конфиг: %s" % self.var_path.get())
        self.log("журнал: %s | отчёты: %s" % (eng.LOG_DIR, eng.REPORT_DIR))

    def _on_apply(self, vals):
        """Кнопка «Применить» таблицы: путь из таблицы идёт в проверку и в настройки."""
        self.var_path.set(vals.get("last_config", self.var_path.get()))
        self.st["last_config"] = vals.get("last_config")
        self.save_settings()
        return vals

    def log(self, s):
        try:
            self._log_write(str(s))          # пишем в журнал каркаса
        except Exception:
            self._pending.append(str(s))     # журнала ещё нет — копим и выведем при сборке

    def open_dir(self, p):
        try:
            if p and os.path.isdir(p):
                os.startfile(p)
        except Exception as e:
            messagebox.showwarning("Не открыть", "%s\n%s" % (p, e))

    def open_file(self):
        try:
            if os.path.exists(self.var_path.get()):
                os.startfile(self.var_path.get())
        except Exception as e:
            messagebox.showwarning("Не открыть", str(e))

    def browse(self):
        p = filedialog.askopenfilename(filetypes=[("config.pro", "*.pro"), ("Все файлы", "*.*")])
        if p:
            self.var_path.set(p)
            self.st["last_config"] = p
            self.save_settings()   # выбранный конфиг переживает перезапуск окна

    def run(self):
        """Проверка: дерево слева, иконка статуса на каждой строке, сводка с процентом.
        Чтение файла уходит в поток — окно не замирает (константа 5)."""
        p = self.var_path.get()
        self.st["last_config"] = p
        self.save_settings()
        if not os.path.exists(p):
            return messagebox.showwarning("Нет файла", p)
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.status.set("проверяю %s…" % p)
        self.stop_flag, _ = U.stop_button(self.root, self.log)

        def work():
            return eng.audit(p)

        U.run_in_thread(self.root, work, on_done=lambda res: self._show(res, p),
                        on_error=lambda e: self.log("ОШИБКА проверки: %s" % e),
                        log=self.log)

    def _show(self, res, p):
        _t0 = time.time()
        self.res = res
        for pr in res["problems"]:
            self.tree.insert("", "end", values=(U.ICON_ERR, pr["line"], pr["opt"],
                                                pr["value"], pr["path"]), tags=("fail",))
        _secs = time.time() - _t0
        ok_ = max(0, res["total"] - res["missing"])
        self.set_summary(res["total"], ok_, res["missing"],
                         label="путей на месте: %d из %d" % (ok_, res["total"]))
        self.status.set("готово за %.2f с" % _secs)
        self.log("файл: %s (%.2f с)" % (p, _secs))
        if self.res["missing"]:
            self.log("ЧТО ДЕЛАТЬ: файла нет → либо положить файл по этому пути, либо закомментировать "
                     "настройку (`!`) и рядом записать причину.")
        else:
            self.log("все пути на месте.")
        # тот же журнал и отчёт, что у CLI (закон трёх рук: одна база — один лог, один отчёт)
        try:
            rep = eng.write_report(self.res, p, _secs, quiet=True)
            self.log("отчёт: %s" % rep)
            self.log("журнал прогона: %s" % os.path.join(eng.LOG_DIR, "run_*.txt"))
        except Exception as e:
            self.log("отчёт не записан: %s" % e)

    def save_csv(self):
        if not self.res:
            return messagebox.showinfo("Нечего сохранять", "Сначала проверка")
        p = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="config_пути.csv")
        if not p:
            return
        try:
            with open(p, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["строка", "настройка", "в конфиге", "путь на диске"])
                for pr in self.res["problems"]:
                    w.writerow([pr["line"], pr["opt"], pr["value"], pr["path"]])
            self.log("отчёт сохранён: %s" % p)
        except Exception as e:
            messagebox.showerror("Не сохранить", str(e))

    # README теперь показывает каркас (U.readme_button) — свой метод не нужен.


if __name__ == "__main__":
    r = U.make_root("V1 — ПУТИ CONFIG.PRO — что есть, чего нет", "1020x620", minsize=(900, 560))
    App(r)
    r.mainloop()