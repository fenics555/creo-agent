# -*- coding: utf-8 -*-
"""creo_export — ОКНО выгрузки модели из ЖИВОГО Creo (STEP/IGES/VRML/PDF/NEUTRAL/DXF3D/STL).

Запуск: creo_export_gui.bat. Нужен запущенный Creo (JLINK, без CREOSON).
Движок — `creo_export.bat` в этой же папке (класс Ж): окно только собирает команду и показывает вывод.
"""
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import ui_common as U  # noqa: E402  (общий каркас окон дома)

HERE = Path(__file__).resolve().parent
BAT = HERE / "creo_export.bat"
# НАСТРОЙКИ — в одном месте по шаблону инструмента дома:
# settings\creo_export_settings.json, версионируются, бэкапы с ротацией.
# Старый gui_settings.json из корня мигрируется один раз в settings\backup_settings.
CFG_DIR = HERE / "settings"
SETTINGS = CFG_DIR / "creo_export_settings.json"
BACKUP_DIR = CFG_DIR / "backup_settings"
LEGACY = HERE / "gui_settings.json"
SETTINGS_VERSION = 2
BACKUP_KEEP = 5

FORMATS = ["step", "iges", "vrml", "pdf", "neutral", "dxf3d", "stl"]
CREO_EXT = ".prt .asm .drw .frm .sec .lay"


def _defaults():
    return {"settings_version": SETTINGS_VERSION, "format": "step", "model": "",
            "out": str(HERE / "out"), "open_after": True}


class App:
    def __init__(self, root=None):
        # ПЕРЕВОД НА КАРКАС 04.10.2026: make_root даёт заголовок с версией + размеры + minsize.
        self.root = root or U.make_root("V3 — ВЫГРУЗКА ИЗ ЖИВОГО CREO (JLINK)",
                                        "1020x660", minsize=(900, 560))
        self.st = self.load()
        self.proc = None
        self.build()

    def load(self):
        """Чтение настроек: новый файл в settings\\ главный, старый из корня — только мигрируется.
        Битый json = значения по умолчанию, окно открывается."""
        d = _defaults()
        src = None
        if SETTINGS.exists():
            src = SETTINGS
        elif LEGACY.exists():
            src = LEGACY
        if src is not None:
            try:
                import json
                data = json.loads(src.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    d.update(data)
            except Exception:
                pass
            # миграция со старого файла: копия и новое место
            if src == LEGACY:
                try:
                    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
                    stamp = time.strftime("%Y-%m-%d_%H%M%S")
                    (BACKUP_DIR / ("gui_settings_%s.json" % stamp)).write_text(
                        src.read_text(encoding="utf-8"), encoding="utf-8")
                except Exception:
                    pass
        d["settings_version"] = SETTINGS_VERSION
        return d

    def save(self):
        r"""Запись настроек в settings\creo_export_settings.json: чужие ключи не теряются,
        перед перезаписью копия, ротация последних BACKUP_KEEP бэкапов."""
        import json
        try:
            prev = {}
            if SETTINGS.exists():
                try:
                    prev = json.loads(SETTINGS.read_text(encoding="utf-8")) or {}
                except Exception:
                    prev = {}
            if not isinstance(prev, dict):
                prev = {}
            prev.update({
                "settings_version": SETTINGS_VERSION,
                "format": self.var_fmt.get(),
                "model": self.var_model.get(),
                "out": self.var_out.get(),
                "open_after": bool(self.var_open.get()),
            })
            CFG_DIR.mkdir(parents=True, exist_ok=True)
            if SETTINGS.exists():
                BACKUP_DIR.mkdir(parents=True, exist_ok=True)
                stamp = time.strftime("%Y-%m-%d_%H%M%S")
                (BACKUP_DIR / ("creo_export_settings_%s.json" % stamp)).write_text(
                    json.dumps(prev, ensure_ascii=False, indent=1), encoding="utf-8")
                self._rotate()
            SETTINGS.write_text(json.dumps(prev, ensure_ascii=False, indent=1), encoding="utf-8")
            return True
        except Exception as e:
            self.log("настройки НЕ сохранены: %s\n" % e)
            return False

    @staticmethod
    def _rotate():
        """Ротация бэкапов по времени: остаются последние BACKUP_KEEP файлов."""
        try:
            items = sorted(((BACKUP_DIR / n).stat().st_mtime, n)
                           for n in os.listdir(BACKUP_DIR))
            for _m, n in items[:-BACKUP_KEEP] if len(items) > BACKUP_KEEP else []:
                (BACKUP_DIR / n).unlink()
        except Exception:
            pass

    def build(self):
        # ПЕРЕВОД НА КАРКАС 04.10.2026: окно на каркасе. Настройки НЕ трогаем — у программы
        # своя версионируемая система (settings\creo_export_settings.json, ротация бэкапов),
        # она по шаблону инструмента лучше каркасной.
        U.head(self.root, "ВЫГРУЗКА ИЗ ЖИВОГО CREO (JLINK)",
               "Выгружает модель из запущенного Creo через JLINK. Нужен запущенный Creo "
               "с работающим прокси (порт 8080). Проверка сессии — кнопкой слева.")
        left, right = U.split_result_left(self.root, right_width=380)

        _, btns = U.actions(left,
                            primary=(("ВЫГРУЗИТЬ", self.run),),
                            secondary=(("СТОП", self.stop),
                                       ("Открыть папку вывода", self.open_out),
                                       ("Проверить Creo (порт 8080/сессия)", self.check_creo)))
        self.b_run, self.b_stop = btns[0], btns[1]
        self.b_stop.config(state="disabled")
        self.info, self._log = U.log_view(left, height=18, title="ВЫВОД ВЫГРУЗКИ")

        _nb, pages = U.tabs(right, ["Что выгружать"])
        top = pages[0]

        tk.Label(top, text="Формат:", bg=U.BG).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        self.var_fmt = tk.StringVar(value=self.st["format"])
        tk.OptionMenu(top, self.var_fmt, *FORMATS).grid(row=1, column=0, sticky="w", padx=8)

        tk.Label(top, text="Модель (файл или имя в сессии Creo):", bg=U.BG).grid(
            row=2, column=0, sticky="w", pady=(8, 2))
        self.var_model = tk.StringVar(value=self.st["model"])
        tk.Entry(top, textvariable=self.var_model).grid(row=3, column=0, sticky="ew", padx=8)
        tk.Button(top, text="Обзор…", command=self.browse_model).grid(row=4, column=0, sticky="w", padx=8, pady=4)

        tk.Label(top, text="Папка вывода:", bg=U.BG).grid(row=5, column=0, sticky="w", pady=(4, 2))
        self.var_out = tk.StringVar(value=self.st["out"])
        tk.Entry(top, textvariable=self.var_out).grid(row=6, column=0, sticky="ew", padx=8)
        tk.Button(top, text="Обзор…", command=self.browse_out).grid(row=7, column=0, sticky="w", padx=8, pady=4)

        self.var_open = tk.BooleanVar(value=self.st["open_after"])
        tk.Checkbutton(top, text="открыть папку вывода после выгрузки", bg=U.BG,
                       variable=self.var_open, command=self.save).grid(row=8, column=0, sticky="w", padx=8)
        row = tk.Frame(top, bg=U.BG)
        row.grid(row=9, column=0, sticky="ew", padx=8, pady=8)
        U.readme_button(row, str(HERE), self.log)
        top.columnconfigure(0, weight=1)

    # ---------- вспомогательное ----------
    def open_out(self):
        self.open_dir(self.var_out.get())

    def log(self, s):
        self._log(s)

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

# Метод show_readme удалён 04.10.2026: кнопку README даёт каркас (U.readme_button),
# поэтому собственный дубль остался бы мёртвым кодом.


if __name__ == "__main__":
    # Окно создаёт САМ каркас (make_root) — раньше здесь создавался tk.Tk() вручную.
    App().root.mainloop()