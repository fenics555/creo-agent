# -*- coding: utf-8 -*-
"""creo_comb — ОКНО «чесалки» (параметры, уравнения, ограничения, кто есть кто).

Запуск: creo_comb_gui.bat. Большинству режимов нужен запущенный Creo (JLINK, без CREOSON);
`tpl-plan` работает без Creo.
Движок — `creo_comb.bat` в этой же папке (класс Ж): окно собирает команду и показывает вывод.
ЗАПИСЬ в модели делает только режим `add` и только с флагом `--apply` (копии ложатся в `_pre`).
"""
import json
import os
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

HERE = Path(__file__).resolve().parent
BAT = HERE / "creo_comb.bat"
SETTINGS = HERE / "gui_settings.json"

MODES = [
    ("tpl-plan — шаблоны конфига: что прописано и есть ли файл (без Creo)", "tpl-plan"),
    ("refs — ЭТАЛОНЫ: уравнения и параметры шаблонов", "refs"),
    ("dump — одна модель: уравнения+параметры", "dump"),
    ("scan — чего не хватает моделям ПАПКИ против эталонов", "scan"),
    ("scan-here — то же по текущей папке Creo", "scan-here"),
    ("roles — кто есть кто: заготовка/ссылочная/оснастка/производство", "roles"),
    ("typcheck — проверить ТИП по фактам Creo", "typcheck"),
    ("mfgcheck — проверка производственных моделей", "mfgcheck"),
    ("add — ДОБАВИТЬ недостающие параметры и уравнения (запись!)", "add"),
    ("setparam — поставить параметр вручную (запись с --save)", "setparam"),
    ("mkparam — создать параметр (запись с --save)", "mkparam"),
    ("probe-open — проба открытия моделей", "probe-open"),
]
NO_CREO = {"tpl-plan"}
WRITE_MODES = {"add", "setparam", "mkparam"}


class App:
    def __init__(self, root):
        self.root = root
        self.root.title("V1 — ЧЕСАЛКА CREO (creo_comb)")
        self.root.geometry("980x640")
        self.st = self.load()
        self.proc = None
        self.build()

    def load(self):
        d = {"mode": "tpl-plan", "arg1": "", "arg2": "",
             "apply": False, "empty_first": False, "force": False, "save": False}
        try:
            if SETTINGS.exists():
                d.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
        except Exception:
            pass
        return d

    def save(self):
        try:
            self.st.update({"mode": self.lab2mode.get(self.var_label.get(), "tpl-plan"),
                            "arg1": self.var_arg1.get(), "arg2": self.var_arg2.get(),
                            "apply": bool(self.var_apply.get()), "empty_first": bool(self.var_empty.get()),
                            "force": bool(self.var_force.get()), "save": bool(self.var_save.get())})
            SETTINGS.write_text(json.dumps(self.st, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:
            pass

    def build(self):
        top = tk.LabelFrame(self.root, text="НАСТРОЙКИ", padx=10, pady=8)
        top.pack(fill="x", padx=10, pady=8)

        tk.Label(top, text="Режим:").grid(row=0, column=0, sticky="w")
        labels = [m[0] for m in MODES]
        self.lab2mode = {m[0]: m[1] for m in MODES}
        self.mode2lab = {m[1]: m[0] for m in MODES}
        self.var_label = tk.StringVar(value=self.mode2lab.get(self.st["mode"], labels[0]))
        om = tk.OptionMenu(top, self.var_label, *labels, command=lambda *_: self.mode_changed())
        om.config(width=72, anchor="w")
        om.grid(row=0, column=1, columnspan=2, sticky="w", padx=6)

        tk.Label(top, text="Папка / файл:").grid(row=1, column=0, sticky="w", pady=4)
        self.var_arg1 = tk.StringVar(value=self.st["arg1"])
        tk.Entry(top, textvariable=self.var_arg1, width=64).grid(row=1, column=1, padx=6)
        tk.Button(top, text="Папка…", command=self.browse_dir).grid(row=1, column=2, sticky="w")
        tk.Button(top, text="Файл…", command=self.browse_file).grid(row=2, column=2, sticky="w")

        tk.Label(top, text="Второй аргумент (config.pro / имя модели / ASM|PART):").grid(row=3, column=0, sticky="w", pady=4)
        self.var_arg2 = tk.StringVar(value=self.st["arg2"])
        tk.Entry(top, textvariable=self.var_arg2, width=64).grid(row=3, column=1, padx=6)
        tk.Button(top, text="config.pro…", command=self.browse_cfg).grid(row=3, column=2, sticky="w")

        flags = tk.Frame(top)
        flags.grid(row=4, column=0, columnspan=3, sticky="w", pady=6)
        self.var_apply = tk.BooleanVar(value=self.st["apply"])
        self.var_empty = tk.BooleanVar(value=self.st["empty_first"])
        self.var_force = tk.BooleanVar(value=bool(self.st.get("force")))
        self.var_save = tk.BooleanVar(value=bool(self.st.get("save")))
        tk.Checkbutton(flags, text="--apply (ПИСАТЬ в модели)", variable=self.var_apply,
                       command=self.save).pack(side="left", padx=4)
        tk.Checkbutton(flags, text="--empty-first", variable=self.var_empty,
                       command=self.save).pack(side="left", padx=4)
        tk.Checkbutton(flags, text="-f", variable=self.var_force, command=self.save).pack(side="left", padx=4)
        tk.Checkbutton(flags, text="--save", variable=self.var_save, command=self.save).pack(side="left", padx=4)

        btns = tk.Frame(self.root)
        btns.pack(fill="x", padx=10)
        self.b_run = tk.Button(btns, text="ЗАПУСТИТЬ", width=16, command=self.run)
        self.b_run.pack(side="left", padx=4)
        self.b_stop = tk.Button(btns, text="СТОП", width=10, state="disabled", command=self.stop)
        self.b_stop.pack(side="left", padx=4)
        tk.Button(btns, text="Проверить Creo", command=self.check_creo).pack(side="left", padx=4)
        tk.Button(btns, text="Открыть папку _pre (копии перед записью)",
                  command=lambda: self.open_dir(str(Path(self.var_arg1.get()) / "_pre"))).pack(side="left", padx=4)

        self.warn = tk.Label(self.root, text="", anchor="w", bg="#fff1c7", padx=8, pady=4)
        self.warn.pack(fill="x", padx=10, pady=(6, 0))

        self.info = tk.Text(self.root, height=20, font=("Consolas", 9), bg="#f8f9fa")
        self.info.pack(fill="both", expand=True, padx=10, pady=8)
        self.mode_changed()

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

    def mode_changed(self):
        mode = self.lab2mode.get(self.var_label.get(), "tpl-plan")
        notes = []
        if mode in WRITE_MODES:
            notes.append("режим ПИШЕТ в модели; без --apply только план, копии ложатся в _pre рядом с моделью")
        notes.append("Creo не нужен" if mode in NO_CREO else "нужен запущенный Creo")
        if mode == "setparam":
            notes.append("второй аргумент: TYP ASM (сборка) или TYP PART (деталь)")
        self.warn.config(text=" • ".join(notes))
        self.save()

    def browse_dir(self):
        p = filedialog.askdirectory()
        if p:
            self.var_arg1.set(p)

    def browse_file(self):
        p = filedialog.askopenfilename()
        if p:
            self.var_arg1.set(p)

    def browse_cfg(self):
        p = filedialog.askopenfilename(filetypes=[("config.pro", "*.pro"), ("Все файлы", "*.*")])
        if p:
            self.var_arg2.set(p)

    def check_creo(self):
        try:
            out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq parametric.exe"],
                                 capture_output=True, text=True, encoding="cp866", errors="replace").stdout
            ok = "parametric.exe" in out
            self.log("[Creo] %s\n" % ("запущен ✓" if ok else "НЕ найден — большинство режимов не сработает"))
        except Exception as e:
            self.log("проверка не вышла: %s\n" % e)

    # ---------- прогон ----------
    def run(self):
        self.save()
        mode = self.lab2mode.get(self.var_label.get(), "tpl-plan")
        if mode in WRITE_MODES and self.var_apply.get():
            if not messagebox.askyesno("ВНИМАНИЕ: запись в модели",
                                       "Режим «%s» с флагом --apply изменит модели и сохранит новые версии.\n"
                                       "Копии прежних файлов лягут в _pre рядом с моделью.\n\nПродолжить?"
                                       % mode):
                return
        args = [str(BAT), mode]
        if self.var_arg1.get().strip():
            args.append(self.var_arg1.get().strip())
        if self.var_arg2.get().strip():
            args.append(self.var_arg2.get().strip())
        if self.var_apply.get() and mode in WRITE_MODES:
            args.append("--apply")
        if self.var_empty.get() and mode == "add":
            args.append("--empty-first")
        if self.var_force.get():
            args.append("-f")
        if self.var_save.get() and mode in ("setparam", "mkparam"):
            args.append("--save")

        self.info.delete("1.0", "end")
        self.log("команда: %s\n\n" % " ".join('"%s"' % a if " " in a else a for a in args[1:]))
        self.b_run.config(state="disabled")
        self.b_stop.config(state="normal")

        def work():
            try:
                self.proc = subprocess.Popen(args, cwd=str(HERE), stdout=subprocess.PIPE,
                                             stderr=subprocess.STDOUT, text=True,
                                             encoding="utf-8", errors="replace", bufsize=1)
                for line in self.proc.stdout:
                    self.root.after(0, self.log, line)
                self.proc.wait()
                self.root.after(0, self.log, "\n=== код возврата: %s ===\n" % self.proc.returncode)
            except Exception as e:
                self.root.after(0, self.log, "\nошибка запуска: %s\n" % e)
            self.root.after(0, self.done)

        threading.Thread(target=work, daemon=True).start()

    def stop(self):
        try:
            if self.proc:
                subprocess.run(["taskkill", "/T", "/F", "/PID", str(self.proc.pid)], capture_output=True)
                self.log("\nпроцесс остановлен по кнопке СТОП\n")
        except Exception as e:
            self.log("не остановить: %s\n" % e)
        self.done()

    def done(self):
        self.proc = None
        self.b_run.config(state="normal")
        self.b_stop.config(state="disabled")


if __name__ == "__main__":
    r = tk.Tk()
    App(r)
    r.mainloop()