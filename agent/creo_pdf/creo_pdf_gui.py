# -*- coding: utf-8 -*-
"""CREO PDF — окно: скан и обновление PDF рядом с чертежами.
Движок: D:\\AI\\tools\\agent\\creo_pdf\\creo_pdf.bat (прямой JLINK, без CREOSON).
Рутина дома: рядом с <имя>.drw[.N] должен лежать <имя>.pdf и быть не старше чертежа.
Обход — по ВСЕМ подпапкам выбранной папки.
Запуск: python creo_pdf_gui.py                      (окно)
        python creo_pdf_gui.py --selftest "<папка>"  (проверка движка без окна)
"""
import json, os, queue, subprocess, sys, threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

HERE = os.path.dirname(os.path.abspath(__file__))
BAT = os.path.join(HERE, "creo_pdf.bat")
CFG = os.path.join(HERE, "gui_settings.json")
DEFAULT_CFG = r"Z:\PTC\CREO-START\START-STD\config.pro"
DEFAULT_DIR = r"Z:\PTC\Work"


class Win:
    def __init__(self, root):
        self.root = root
        self.proc = None
        self.q = queue.Queue()
        self.lines = []                     # весь лог — ещё и в файл, чтобы не терялся
        self.s = self._load()
        root.title("CREO PDF — скан и обновление PDF чертежей")
        root.geometry("980x620")
        root.minsize(760, 460)

        frm = ttk.Frame(root, padding=8)
        frm.pack(fill="x")

        ttk.Label(frm, text="Путь к config.pro:").grid(row=0, column=0, sticky="w", pady=2)
        self.cfg_var = tk.StringVar(value=self.s.get("config", DEFAULT_CFG))
        ttk.Entry(frm, textvariable=self.cfg_var).grid(row=0, column=1, sticky="ew", padx=4)
        ttk.Button(frm, text="Обзор…", width=10, command=self.pick_cfg).grid(row=0, column=2, padx=2)
        ttk.Button(frm, text="Из сессии", width=12, command=self.from_session).grid(row=0, column=3, padx=2)
        ttk.Button(frm, text="Применить к Creo", width=17, command=self.apply_cfg).grid(row=0, column=4, padx=2)

        ttk.Label(frm, text="Папка проверки:").grid(row=1, column=0, sticky="w", pady=2)
        self.dir_var = tk.StringVar(value=self.s.get("folder", DEFAULT_DIR))
        ttk.Entry(frm, textvariable=self.dir_var).grid(row=1, column=1, sticky="ew", padx=4)
        ttk.Button(frm, text="Обзор…", width=10, command=self.pick_dir).grid(row=1, column=2, padx=2)
        frm.columnconfigure(1, weight=1)

        bar = ttk.Frame(root, padding=(8, 0))
        bar.pack(fill="x")
        self.b_scan = ttk.Button(bar, text="СКАН (отчёт)", command=lambda: self.run("scan"))
        self.b_scan.pack(side="left")
        ttk.Label(bar, text="   лимит (0 = без ограничения):").pack(side="left")
        self.limit = tk.StringVar(value=str(self.s.get("limit", 50)))
        ttk.Entry(bar, width=6, textvariable=self.limit).pack(side="left")
        self.open_pdf = tk.BooleanVar(value=bool(self.s.get("open_pdf", False)))
        ttk.Checkbutton(bar, text="открывать PDF", variable=self.open_pdf).pack(side="left", padx=4)
        self.b_exp = ttk.Button(bar, text="СОЗДАТЬ / ОБНОВИТЬ PDF", command=lambda: self.run("export"))
        self.b_exp.pack(side="left", padx=6)
        self.b_stop = ttk.Button(bar, text="СТОП", command=self.stop, state="disabled")
        self.b_stop.pack(side="left")
        ttk.Button(bar, text="Копировать лог", command=self.copy_log).pack(side="left", padx=(6, 2))
        ttk.Button(bar, text="Сохранить…", command=self.save_log).pack(side="left", padx=2)
        ttk.Button(bar, text="Очистить", command=self.clear).pack(side="left", padx=2)
        self.status = ttk.Label(bar, text="готов")
        self.status.pack(side="right")

        bar2 = ttk.Frame(root, padding=(8, 4))
        bar2.pack(fill="x")
        ttk.Button(bar2, text="README", width=12, command=self.show_readme).pack(side="left")
        ttk.Button(bar2, text="Где config.pro (без сессии)", width=26, command=self.scan_cfg).pack(side="left", padx=4)
        ttk.Button(bar2, text="Найти Creo (реестр)", width=19, command=self.creo_find).pack(side="left", padx=4)
        ttk.Button(bar2, text="Запустить Creo (штатно)", width=22, command=self.start_creo).pack(side="left", padx=4)
        ttk.Label(bar2, text="PDF делает только ЖИВАЯ сессия Creo", foreground="#7a7a7a").pack(side="left", padx=8)

        box = ttk.Frame(root, padding=8)
        box.pack(fill="both", expand=True)
        self.txt = tk.Text(box, wrap="none", font=("Consolas", 9), bg="#1B1C1E", fg="#E8E8E8")
        ys = ttk.Scrollbar(box, orient="vertical", command=self.txt.yview)
        xs = ttk.Scrollbar(box, orient="horizontal", command=self.txt.xview)
        self.txt.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.txt.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)

        # --- лог: выделение, копирование, сохранение, правый клик ---
        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="Копировать выделенное", command=lambda: self.txt.event_generate("<<Copy>>"))
        self.menu.add_command(label="Копировать ВЕСЬ лог", command=self.copy_log)
        self.menu.add_command(label="Сохранить лог в файл…", command=self.save_log)
        self.menu.add_command(label="Показать, что в буфере", command=self.show_clip)
        self.menu.add_separator()
        self.menu.add_command(label="Выделить всё (Ctrl+A)", command=self.sel_all)
        self.menu.add_command(label="Очистить", command=self.clear)
        self.txt.bind("<Button-3>", lambda e: self.menu.tk_popup(e.x_root, e.y_root))
        self.txt.bind("<Control-a>", self.sel_all)
        self.txt.bind("<Control-A>", self.sel_all)
        self.txt.bind("<Control-c>", lambda e: self.txt.event_generate("<<Copy>>"))

        root.after(100, self.pump)
        self.log("Готов. Порядок: «СКАН (отчёт)» → «СОЗДАТЬ / ОБНОВИТЬ PDF» (нужен запущенный Creo).")
        self.log("Движок: " + BAT)

    # ---------- служебное ----------
    def _load(self):
        try:
            return json.loads(open(CFG, encoding="utf-8").read())
        except Exception:
            return {}

    def _save(self):
        try:
            open(CFG, "w", encoding="utf-8").write(json.dumps(
                {"config": self.cfg_var.get(), "folder": self.dir_var.get(),
                 "limit": self.limit.get(), "open_pdf": bool(self.open_pdf.get())},
                ensure_ascii=False, indent=1))
        except Exception:
            pass

    def log(self, line):
        self.lines.append(line)
        self.q.put(line)

    def _dump_log(self):
        """Автосохранение лога рядом с программой: last_run_log.txt + logs\\run_<дата>.txt."""
        import datetime
        text = "\n".join(self.lines) + "\n"
        try:
            with open(os.path.join(HERE, "last_run_log.txt"), "w", encoding="utf-8") as f:
                f.write(text)
            d = os.path.join(HERE, "logs")
            os.makedirs(d, exist_ok=True)
            name = "run_" + datetime.datetime.now().strftime("%Y-%m-%d_%H%M") + ".txt"
            with open(os.path.join(d, name), "w", encoding="utf-8") as f:
                f.write(text)
            self.status.config(text="готов · лог: logs\\" + name)
        except Exception:
            pass

    def pump(self):
        try:
            while True:
                line = self.q.get_nowait()
                if line == "__done__":
                    self.proc = None
                    self.b_scan.config(state="normal"); self.b_exp.config(state="normal")
                    self.b_stop.config(state="disabled")
                    self._dump_log()
                    self.status.config(text="готов · лог: last_run_log.txt")
                    continue
                self.txt.insert("end", line + "\n")
                self.txt.see("end")
                if line.startswith("чертежей:"):
                    self.status.config(text=line.strip())
        except queue.Empty:
            pass
        self.root.after(120, self.pump)

    def clear(self):
        self.txt.delete("1.0", "end")

    def sel_all(self, e=None):
        self.txt.tag_add("sel", "1.0", "end")
        self.txt.mark_set("insert", "1.0")
        return "break"

    def copy_log(self):
        t = self.txt.get("1.0", "end-1c")
        n = len(t.splitlines())
        ok = False
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(t)
            self.root.update()                                  # чтобы буфер закрепился сразу
            ok = (self.root.clipboard_get() == t)               # и сразу проверили чтением
        except Exception as e:
            self.log("tk-буфер не сработал (%s) — пробую через PowerShell" % e)
        if not ok:
            ok = self._clip_via_powershell(t)
        if ok:
            self.status.config(text="лог скопирован: %d строк" % n)
            self.log("— скопировано в буфер: %d строк (%d символов) —" % (n, len(t)))
        else:
            self.status.config(text="копирование не удалось")
            self.log("— КОПИРОВАНИЕ НЕ УДАЛОСЬ. Нажми «Сохранить…» — файл лога пишется всегда. —")

    def _clip_via_powershell(self, text):
        """Резервный путь: буфер через PowerShell (файл в UTF-16 — кириллица цела)."""
        tmp = os.path.join(HERE, "_clip_tmp.txt")
        try:
            with open(tmp, "w", encoding="utf-16") as f:
                f.write(text)
            subprocess.run(["powershell", "-NoProfile", "-Command", "Set-Clipboard -Path '%s'" % tmp],
                           capture_output=True, timeout=90)
            return True
        except Exception as e:
            self.log("PowerShell-буфер тоже не сработал: %s" % e)
            return False

    def show_clip(self):
        try:
            t = self.root.clipboard_get()
        except Exception:
            t = ""
        if not t:
            self.log("— в буфере пусто (или недоступно) —")
        else:
            self.log("— в буфере %d символов, начало: %r —" % (len(t), t[:200]))

    def save_log(self):
        p = filedialog.asksaveasfilename(title="Сохранить лог", defaultextension=".txt",
                                         initialfile="creo_pdf_log.txt",
                                         filetypes=[("текст", "*.txt"), ("все файлы", "*.*")])
        if not p:
            return
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(self.txt.get("1.0", "end-1c"))
            self.status.config(text="лог сохранён")
            self.log("— лог сохранён: %s —" % p)
        except Exception as e:
            self.log("не удалось сохранить лог: %s" % e)

    def pick_cfg(self):
        p = filedialog.askopenfilename(title="Выбрать config.pro", initialdir=os.path.dirname(DEFAULT_CFG),
                                       filetypes=[("config", "*.pro"), ("все файлы", "*.*")])
        if p:
            self.cfg_var.set(p)

    def pick_dir(self):
        p = filedialog.askdirectory(title="Выбрать папку проверки", initialdir=self.dir_var.get() or DEFAULT_DIR)
        if p:
            self.dir_var.set(p)

    # ---------- движок ----------
    def _spawn(self, args, title):
        if self.proc:
            messagebox.showinfo("Занято", "Сначала дождись окончания или нажми СТОП")
            return
        self._save()
        self.log("-" * 90)
        self.log("%s: creo_pdf %s" % (title, " ".join(args)))
        self.status.config(text="работаю…")
        self.b_scan.config(state="disabled"); self.b_exp.config(state="disabled")
        self.b_stop.config(state="normal")
        threading.Thread(target=self._worker, args=(args,), daemon=True).start()

    def _worker(self, args):
        try:
            self.proc = subprocess.Popen(["cmd", "/c", "call", BAT] + list(args), cwd=HERE,
                                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, encoding="utf-8", errors="replace", bufsize=1)
            for line in self.proc.stdout:
                self.log(line.rstrip())
            code = self.proc.wait()
            self.log("движок завершён, код %s" % code)
        except Exception as e:
            self.log("ОШИБКА запуска: %s" % e)
        finally:
            self.q.put("__done__")

    def stop(self):
        if self.proc:
            try:
                subprocess.run(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"], capture_output=True)
                self.log("остановлено пользователем")
            except Exception as e:
                self.log("стоп: %s" % e)

    def run(self, mode):
        d = self.dir_var.get().strip()
        if not d or not os.path.isdir(d):
            messagebox.showwarning("Папка", "Выбери существующую папку проверки")
            return
        if mode == "scan":
            self._spawn(["scan", d], "СКАН")
        else:
            args = ["export", d, self.limit.get().strip() or "50"]
            if self.open_pdf.get():
                args.append("open")
            self._spawn(args, "ЭКСПОРТ PDF" + (" (с открытием)" if self.open_pdf.get() else " (не открывать)"))

    def from_session(self):
        self._spawn(["config-find"], "ПОИСК КОНФИГА (папка старта Creo и config.pro)")

    def scan_cfg(self):
        self._spawn(["config-scan"], "ПОИСК config.pro БЕЗ СЕССИИ CREO")

    def show_readme(self):
        p = os.path.join(HERE, "README.md")
        try:
            text = open(p, encoding="utf-8").read()
        except Exception as e:
            self.log("README не прочитан: %s" % e)
            return
        self.log("=" * 92)
        self.log("README: " + p)
        self.log("=" * 92)
        for line in text.splitlines():
            self.log(line)
        self.log("=" * 92)
        self.log("конец README")

    def creo_find(self):
        self._spawn(["creo-find"], "ПОИСК УСТАНОВКИ CREO (реестр Windows)")

    def start_creo(self):
        cfg = self.cfg_var.get().strip() or DEFAULT_CFG
        if not os.path.isfile(cfg):
            messagebox.showwarning("config.pro",
                                   "Сначала выбери существующий config.pro —\nего папка станет рабочей папкой Creo")
            return
        d = os.path.dirname(cfg)
        if not messagebox.askyesno("Штатный запуск Creo",
                                   "Запустить Creo штатно?\n\nparametric.exe с рабочей папкой:\n" + d +
                                   "\n\nCreo читает config.pro из рабочей папки — оттуда придут форматки,"
                                   " MY_ESKD.dtl и table.pnt.\n(домашний CREO-START.bat не используется)"):
            return
        self._spawn(["creo-start", cfg], "ШТАТНЫЙ ЗАПУСК CREO")

    def apply_cfg(self):
        c = self.cfg_var.get().strip()
        if not c or not os.path.isfile(c):
            messagebox.showwarning("config.pro", "Укажи существующий файл config.pro")
            return
        self._spawn(["config-load", c], "ПРИМЕНЕНИЕ КОНФИГА К Creo")


def selftest(folder):
    """Проверка движка без окна: скан папки и признак работы (для приёмки)."""
    print("движок:", BAT)
    p = subprocess.run(["cmd", "/c", "call", BAT, "scan", folder], cwd=HERE,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    print(out)
    print("код:", p.returncode)
    return "чертежей:" in out


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--selftest":
        sys.exit(0 if selftest(sys.argv[2]) else 1)
    root = tk.Tk()
    Win(root)
    root.mainloop()