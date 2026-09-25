# -*- coding: utf-8 -*-
"""creo_export — ОКНО выгрузки модели из ЖИВОГО Creo (STEP/IGES/VRML/PDF/NEUTRAL/DXF3D/STL).

Запуск: creo_export_gui.bat. Нужен запущенный Creo (JLINK, без CREOSON).
Движок — `creo_export.bat` в этой же папке (класс Ж): окно только собирает команду и показывает вывод.
"""
import os
import subprocess
import time
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

HERE = Path(__file__).resolve().parent
BAT = HERE / "creo_export.bat"
SETTINGS = HERE / "gui_settings.json"

FORMATS = ["step", "iges", "vrml", "pdf", "neutral", "dxf3d", "stl"]
CREO_EXT = ".prt .asm .drw .frm .sec .lay"


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("V1 — ВЫГРУЗКА ИЗ CREO (JLINK)")
        self.root.geometry("900x560")
        self.st = self.load()
        self.proc = None
        self.build()

    def load(self):
        d = {"format": "step", "model": "", "out": str(HERE / "out"), "open_after": True}
        try:
            if SETTINGS.exists():
                import json
                d.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
        except Exception:
            pass
        return d

    def save(self):
        try:
            import json
            self.st.update({"format": self.var_fmt.get(), "model": self.var_model.get(),
                            "out": self.var_out.get(), "open_after": bool(self.var_open.get())})
            SETTINGS.write_text(json.dumps(self.st, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:
            pass

    def build(self):
        top = tk.LabelFrame(self.root, text="НАСТРОЙКИ", padx=10, pady=8)
        top.pack(fill="x", padx=10, pady=8)

        tk.Label(top, text="Формат:").grid(row=0, column=0, sticky="w")
        self.var_fmt = tk.StringVar(value=self.st["format"])
        tk.OptionMenu(top, self.var_fmt, *FORMATS).grid(row=0, column=1, sticky="w", padx=6)

        tk.Label(top, text="Модель (файл или имя в сессии Creo):").grid(row=1, column=0, sticky="w", pady=4)
        self.var_model = tk.StringVar(value=self.st["model"])
        tk.Entry(top, textvariable=self.var_model, width=64).grid(row=1, column=1, padx=6)
        tk.Button(top, text="Обзор…", command=self.browse_model).grid(row=1, column=2)

        tk.Label(top, text="Папка вывода:").grid(row=2, column=0, sticky="w")
        self.var_out = tk.StringVar(value=self.st["out"])
        tk.Entry(top, textvariable=self.var_out, width=64).grid(row=2, column=1, padx=6)
        tk.Button(top, text="Обзор…", command=self.browse_out).grid(row=2, column=2)

        self.var_open = tk.BooleanVar(value=self.st["open_after"])
        tk.Checkbutton(top, text="открыть папку вывода после выгрузки", variable=self.var_open,
                       command=self.save).grid(row=3, column=1, sticky="w", padx=6)

        btns = tk.Frame(self.root)
        btns.pack(fill="x", padx=10)
        self.b_run = tk.Button(btns, text="ВЫГРУЗИТЬ", width=16, command=self.run)
        self.b_run.pack(side="left", padx=4)
        self.b_stop = tk.Button(btns, text="СТОП", width=10, state="disabled", command=self.stop)
        self.b_stop.pack(side="left", padx=4)
        tk.Button(btns, text="Открыть папку вывода", command=lambda: self.open_dir(self.var_out.get())).pack(side="left", padx=4)
        tk.Button(btns, text="Проверить Creo (порт 8080/сессия)", command=self.check_creo).pack(side="left", padx=4)

        self.info = tk.Text(self.root, height=22, font=("Consolas", 9), bg="#f8f9fa")
        self.info.pack(fill="both", expand=True, padx=10, pady=8)

    # ---------- вспомогательное ----------
    def log(self, s):
        self.info.insert("end", s)
        self.info.see("end")

    def open_dir(self, p):
        try:
            if p and os.path.isdir(p):
                os.startfile(p)
        except Exception as e:
            messagebox.showwarning("Не открыть", "%s\n%s" % (p, e))

    def browse_model(self):
        p = filedialog.askopenfilename(filetypes=[("Creo", "*" + CREO_EXT.replace(" ", ";*")), ("Все файлы", "*.*")])
        if p:
            self.var_model.set(p)

    def browse_out(self):
        p = filedialog.askdirectory()
        if p:
            self.var_out.set(p)

    def check_creo(self):
        """Проверка, что Creo запущен: ищем процесс parametric.exe."""
        try:
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq parametric.exe"],
                                 capture_output=True, text=True, encoding="cp866", errors="replace").stdout
        except Exception as e:
            return self.log("проверка не вышла: %s\n" % e)
        ok = "parametric.exe" in out
        self.log("[Creo] %s\n" % ("запущен ✓" if ok else "НЕ найден — выгрузка не сработает, поднимите Creo "
                                                      "(кнопка «Запустить Creo (штатно)» в creo_pdf)"))

    # ---------- выгрузка ----------
    def run(self):
        self.save()
        fmt, model, out = self.var_fmt.get(), self.var_model.get().strip(), self.var_out.get().strip()
        if not model:
            return messagebox.showwarning("Нет модели", "Укажи модель: файл или имя модели в сессии Creo")
        if not os.path.isdir(out):
            try:
                os.makedirs(out, exist_ok=True)
            except Exception as e:
                return messagebox.showerror("Нет папки вывода", str(e))
        self.info.delete("1.0", "end")
        self.log("команда: creo_export.bat %s \"%s\" \"%s\"\n" % (fmt, model, out))
        cmd = [str(BAT), fmt, model, out]
        self.b_run.config(state="disabled")
        self.b_stop.config(state="normal")

        def work():
            try:
                self.proc = subprocess.Popen(cmd, cwd=str(HERE), stdout=subprocess.PIPE,
                                             stderr=subprocess.STDOUT, text=True,
                                             encoding="utf-8", errors="replace", bufsize=1)
                _t0 = time.time()
                for line in self.proc.stdout:
                    self.root.after(0, self.log, line)
                self.proc.wait()
                code = self.proc.returncode
                self.root.after(0, self.log, "\n=== код возврата: %s за %.1f с ===\n"
                                % (code, time.time() - _t0))
            except Exception as e:
                self.root.after(0, self.log, "\nошибка запуска: %s\n" % e)
            self.root.after(0, self.done)

        threading.Thread(target=work, daemon=True).start()

    def stop(self):
        try:
            if self.proc:
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)],
                               capture_output=True)
                self.log("\nпроцесс остановлен по кнопке СТОП\n")
        except Exception as e:
            self.log("не остановить: %s\n" % e)
        self.done()

    def done(self):
        self.proc = None
        self.b_run.config(state="normal")
        self.b_stop.config(state="disabled")
        if self.var_open.get():
            self.open_dir(self.var_out.get())


if __name__ == "__main__":
    r = tk.Tk()
    App(r)
    r.mainloop()