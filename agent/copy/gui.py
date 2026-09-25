# -*- coding: utf-8 -*-
"""copy_server — ОКНО службы копирования/переименования (для веб-страниц дома).

Запуск: copy_gui.bat. Класс Р: Creo не нужен.
Движок — `copy_server.py` рядом (HTTP на 127.0.0.1, страница `/copy.html`).
Окно умеет: запустить/остановить службу, сменить порт, открыть страницу, показать лог, проверить порт.
"""
import json
import os
import socket
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
SERVER = HERE / "copy_server.py"
SETTINGS = HERE / "gui_settings.json"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("V1 — СЛУЖБА КОПИРОВАНИЯ (copy_server)")
        self.root.geometry("820x520")
        self.st = self.load()
        self.proc = None
        self.build()
        self.refresh_state()

    def load(self):
        d = {"port": 8000, "bind": "127.0.0.1"}
        try:
            if SETTINGS.exists():
                d.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
        except Exception:
            pass
        return d

    def save(self):
        try:
            self.st.update({"port": int(self.var_port.get()), "bind": self.var_bind.get()})
            SETTINGS.write_text(json.dumps(self.st, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:
            pass

    def build(self):
        top = tk.LabelFrame(self.root, text="НАСТРОЙКИ", padx=10, pady=8)
        top.pack(fill="x", padx=10, pady=8)

        tk.Label(top, text="Порт:").grid(row=0, column=0, sticky="w")
        self.var_port = tk.IntVar(value=self.st["port"])
        tk.Spinbox(top, from_=1024, to=65535, textvariable=self.var_port, width=8,
                   command=self.save).grid(row=0, column=1, sticky="w", padx=6)

        tk.Label(top, text="Адрес привязки:").grid(row=0, column=2, sticky="w", padx=(20, 0))
        self.var_bind = tk.StringVar(value=self.st["bind"])
        tk.Entry(top, textvariable=self.var_bind, width=16).grid(row=0, column=3, sticky="w", padx=6)
        tk.Label(top, text="(127.0.0.1 — только своя машина; 0.0.0.0 — вся сеть, осторожно)",
                 fg="#555").grid(row=1, column=0, columnspan=4, sticky="w")

        btns = tk.Frame(self.root)
        btns.pack(fill="x", padx=10)
        self.b_start = tk.Button(btns, text="ЗАПУСТИТЬ СЛУЖБУ", width=20, command=self.start)
        self.b_start.pack(side="left", padx=4)
        self.b_stop = tk.Button(btns, text="ОСТАНОВИТЬ", width=14, state="disabled", command=self.stop)
        self.b_stop.pack(side="left", padx=4)
        tk.Button(btns, text="Открыть страницу", command=self.open_page).pack(side="left", padx=4)
        tk.Button(btns, text="Проверить порт", command=self.refresh_state).pack(side="left", padx=4)

        self.state = tk.Label(self.root, text="", anchor="w", bg="#fff1c7", padx=8, pady=4)
        self.state.pack(fill="x", padx=10, pady=(6, 0))

        self.info = tk.Text(self.root, font=("Consolas", 9), bg="#f8f9fa")
        self.info.pack(fill="both", expand=True, padx=10, pady=8)

    # ---------- вспомогательное ----------
    def log(self, s):
        self.info.insert("end", s)
        self.info.see("end")

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
        busy = self.port_busy()
        self.state.config(text="порт %d: %s" % (int(self.var_port.get()),
                                                "ЗАНЯТ (служба уже работает)" if busy else "свободен"))
        self.b_start.config(state="disabled" if busy else "normal")
        self.b_stop.config(state="normal" if (busy or self.proc) else "disabled")

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


if __name__ == "__main__":
    r = tk.Tk()
    App(r)
    r.mainloop()