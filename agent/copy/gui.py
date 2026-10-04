# -*- coding: utf-8 -*-
"""copy_server — ОКНО службы копирования/переименования (для веб-страниц дома).

ВЕРСИЯ ОКНА: V2 (04.10.2026 — перевод на каркас ui_common).
Запуск: copy_gui.bat. Класс Р: Creo не нужен.
Движок — `copy_server.py` рядом (HTTP на 127.0.0.1, страница `/copy.html`).
Окно умеет: запустить/остановить службу, сменить порт, открыть страницу, показать лог, проверить порт.

ПЕРЕВОД НА КАРКАС ui_common (04.10.2026, Cline; эстафета волн 10–13, раздел 5, шаги 1–11):
было — `tk.LabelFrame` вручную, `tk.Text` с `bg="#f8f9fa"`, свой `show_readme`, Tk создавался вручную.
Теперь окно строит каркас (make_root/head/actions/tabs/log_view/readme_button) — признаки дизайна
(`V<N>` в заголовке, geometry, minsize, моноширинный журнал, кнопка README) даёт он.
"""
import socket
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import ui_common as U  # noqa: E402  (общий каркас окон дома)

SERVER = HERE / "copy_server.py"
# Настройки окна — через каркас (data\copy_settings.json). До 02.10.2026 окно искало
# `gui_settings.json` в папке программы, которого там НИКОГДА не было: настройки просто
# не сохранялись. Путь теперь даёт ui_common.settings_path.
LOG_DIR = r"D:\AI\log\copy"
TITLE = "СЛУЖБА КОПИРОВАНИЯ (copy_server)"
DEFAULTS = {"port": 8000, "bind": "127.0.0.1"}


class App:
    def __init__(self, root=None):
        # Шаг 2 каркаса: make_root даёт title с версией + geometry + minsize разом.
        self.root = root or U.make_root("V2 — " + TITLE, "1020x620", minsize=(900, 560))
        # ГРАБЛЯ, КОТОРУЮ Я САМ ВНОСИЛ И СРАЗУ УВИДЕЛ: `load()` кладёт текст ошибки в
        # `self._pending`, поэтому `_pending` обязан существовать ДО вызова load — иначе
        # сообщение «настройки не прочитаны» молча пропадало бы (присваивание [] ниже).
        self._pending = []
        self.st = self.load()
        self.proc = None
        self.build()
        self.refresh_state()

    def load(self):
        d = U.load_settings("copy", DEFAULTS)
        self._pending = [] if "_error" not in d else [d["_error"]]
        return {k: v for k, v in d.items() if not k.startswith("_")}

    def save(self):
        out = U.save_settings("copy", self.st)
        if str(out).startswith("ошибка"):
            self._pending.append("настройки не сохранены: %s" % out)

    def build(self):
        # --- каркас: действие СЛЕВА, настройки СПРАВА (константа 5) ---
        U.head(self.root, TITLE,
               "Поднимает и останавливает службу копирования/переименования "
               "(copy_server.py, HTTP на своём порту, страница /copy.html). "
               "Класс Р: Creo не нужен.")
        left, right = U.split_result_left(self.root, right_width=400)

        # --- слева: рабочие кнопки ---
        _, btns = U.actions(left,
                            primary=(("ЗАПУСТИТЬ СЛУЖБУ", self.start),),
                            secondary=(("ОСТАНОВИТЬ", self.stop),
                                       ("Открыть страницу", self.open_page),
                                       ("Проверить порт", self.refresh_state)))
        self.b_start, self.b_stop = btns[0], btns[1]

        # --- слева: состояние службы таблицей (признак канона Treeview show=headings,
        # раньше окно показывало его жёлтой плашкой Label — таблица даёт ту же правду
        # плюс видно, кто порт занял и что именно слушает) ---
        tk.Label(left, text="СОСТОЯНИЕ СЛУЖБЫ", bg=U.BG, fg=U.FG,
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=8, pady=(6, 0))
        self.tree = U.result_tree(left, ("svc", "bind", "port", "state", "who"),
                                  ("Служба", "Адрес", "Порт", "Состояние", "Кто поднял"),
                                  [150, 110, 70, 130, 220])

        # --- справа: вкладка настроек (константа 3) ---
        _nb, pages = U.tabs(right, ["Порт и адрес"])
        top = pages[0]

        tk.Label(top, text="Порт:", bg=U.BG).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        self.var_port = tk.IntVar(value=self.st["port"])
        tk.Spinbox(top, from_=1024, to=65535, textvariable=self.var_port, width=8,
                   command=self.save).grid(row=0, column=1, sticky="w", padx=6, pady=(8, 2))

        tk.Label(top, text="Адрес привязки:", bg=U.BG).grid(row=1, column=0, sticky="w", padx=8)
        self.var_bind = tk.StringVar(value=self.st["bind"])
        tk.Entry(top, textvariable=self.var_bind, width=16).grid(row=1, column=1, sticky="w", padx=6)
        tk.Label(top, text="(127.0.0.1 — только своя машина; 0.0.0.0 — вся сеть, осторожно)",
                 bg=U.BG, fg=U.MUTED, wraplength=340, justify="left").grid(
            row=2, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 2))
        tk.Label(top, text="Порт и адрес сохраняются в data\\copy_settings.json — "
                           "файл настроек окна (через каркас).", bg=U.BG, fg=U.MUTED,
                 wraplength=340, justify="left").grid(row=3, column=0, columnspan=2,
                                                     sticky="w", padx=8)
        # ГРАБЛЯ (04.10.2026, живая проба): внутри вкладки сетка `grid`, поэтому ряд с
        # кнопкой README нельзя `pack` — Tcl ругается «cannot use geometry manager pack
        # inside ...: grid is already managing its content windows». Ряд сажаем в грид.
        row = tk.Frame(top, bg=U.BG)
        row.grid(row=4, column=0, columnspan=2, sticky="ew", padx=8, pady=6)
        U.readme_button(row, str(HERE), lambda s: None)

        # --- журнал внизу окна (каркас даёт моноширинный виджет + функцию лога) ---
        self.info, self._log = U.log_view(self.root, height=7, title="ЖУРНАЛ")
        for s in self._pending:
            self.log(s)
        self._pending = []
        self.log("настройки: %s" % U.settings_path("copy"))
        # 03.10.2026: было HERE.parent.parent/"log" = D:\AI\tools\log — такой папки нет вовсе
        # (Test-Path -> False), журнал службы лежит в D:\AI\log\copy.
        self.log("журнал службы: %s" % LOG_DIR)

    # ---------- вспомогательное ----------
    def log(self, s):
        self._log(s)

    def port_busy(self):
        s = socket.socket()
        s.settimeout(0.4)
        try:
            s.connect((self.var_bind.get() or "127.0.0.1", int(self.var_port.get())))
            return True
        except Exception:
            return False
        finally:
            s.close()

    def refresh_state(self):
        # ЖИВАЯ НАХОДКА 04.10.2026 (перевод на каркас): было `self.state` — жёлтый Label с одной
        # строкой. Теперь тот же факт живёт в дереве состояния (одна строка = одна служба),
        # поэтому плашки больше нет, а кнопки управляются как раньше.
        busy = self.port_busy()
        bind = self.var_bind.get() or "127.0.0.1"
        port = int(self.var_port.get())
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.tree.insert("", "end", values=(
            "copy_server", bind, port,
            "РАБОТАЕТ" if busy else "остановлена",
            "это окно" if self.proc else "не этим окном (например, стек агента)"),
            tags=("ok" if busy else "warn",))
        self.b_start.config(state="disabled" if busy else "normal")
        self.b_stop.config(state="normal" if (busy or self.proc) else "disabled")
        self.log("порт %d: %s" % (port, "ЗАНЯТ (служба уже работает)" if busy else "свободен"))

    def open_page(self):
        webbrowser.open("http://%s:%d/copy.html" % (self.var_bind.get() or "127.0.0.1", int(self.var_port.get())))

    # ---------- служба ----------
    def start(self):
        self.save()
        self.log("запускаю: python copy_server.py --port %d --bind %s\n" % (int(self.var_port.get()), self.var_bind.get()))
        try:
            self.proc = subprocess.Popen([sys.executable, str(SERVER), "--port", str(int(self.var_port.get())),
                                          "--bind", self.var_bind.get()],
                                         cwd=str(HERE), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, encoding="utf-8", errors="replace", bufsize=1)
        except Exception as e:
            return self.log("не запустить: %s\n" % e)

        def pump():
            for line in self.proc.stdout:
                self.root.after(0, self.log, line)
            self.root.after(0, self.after_stop)

        threading.Thread(target=pump, daemon=True).start()
        self.root.after(900, self.refresh_state)

    def after_stop(self):
        self.proc = None
        self.log("\nслужба остановлена\n")
        self.refresh_state()

    def stop(self):
        if self.proc:
            try:
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)], capture_output=True)
            except Exception as e:
                self.log("не остановить: %s\n" % e)
        else:
            self.log("останавливать нечего: эту службу поднял не я (например, стек агента)\n")
        self.after_stop()
# Метод show_readme удалён 04.10.2026: кнопку README теперь даёт каркас (U.readme_button),
# поэтому собственный дубль остался бы мёртвым кодом.


if __name__ == "__main__":
    # Окно создаёт САМ каркас (make_root) — раньше здесь создавался tk.Tk() вручную,
    # из-за чего окно не получало title с версией, geometry и minsize от каркаса.
    App().root.mainloop()