# -*- coding: utf-8 -*-
r"""CREO PDF — окно «ДИЗАЙН 2»: PDF чертежей (скан/обновление) + дубли + PDF без модели.
Движок: creo_pdf.bat (прямой JLINK, без CREOSON) и питоновские помощники.
Первый дизайн сохранён в design1\ (откат — скопировать обратно).

Раскладка:
  НАСТРОЙКИ   — пути (config.pro, папка), обзор, «Из сессии», «Применить», найти/запустить Creo, README, логи
  ИСПОЛНИТЕЛИ — СКАН ПДФ · СОЗДАТЬ/ОБНОВИТЬ ПДФ · СТОП (лимит, «открывать PDF»)
                Искать дубли ПДФ (+ «перемещать в корзину инструмента») · Искать ПДФ без модели (+ то же)
  ОТЧЁТ       — живой лог/таблица, копирование и сохранение
"""
import datetime, json, os, queue, subprocess, sys, threading
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
        self.lines = []
        self.s = self._load()

        root.title("CREO PDF V1 — чертежи, дубли, PDF без модели  ·  дизайн 2")
        root.geometry("1180x740")
        root.minsize(900, 560)
        self._style()

        # ===================== НАСТРОЙКИ =====================
        g1 = ttk.LabelFrame(root, text=" НАСТРОЙКИ ", padding=10)
        g1.pack(fill="x", padx=10, pady=(10, 6))

        ttk.Label(g1, text="config.pro:").grid(row=0, column=0, sticky="w")
        self.cfg_var = tk.StringVar(value=self.s.get("config", DEFAULT_CFG))
        ttk.Entry(g1, textvariable=self.cfg_var).grid(row=0, column=1, columnspan=2, sticky="ew", padx=6)
        ttk.Button(g1, text="Обзор…", width=10, command=self.pick_cfg).grid(row=0, column=3, padx=2)
        ttk.Button(g1, text="Из сессии", width=12, command=self.from_session).grid(row=0, column=4, padx=2)
        ttk.Button(g1, text="Применить к Creo", width=17, command=self.apply_cfg).grid(row=0, column=5, padx=2)

        ttk.Label(g1, text="Папка проверки:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.dir_var = tk.StringVar(value=self.s.get("folder", DEFAULT_DIR))
        ttk.Entry(g1, textvariable=self.dir_var).grid(row=1, column=1, columnspan=2, sticky="ew", padx=6, pady=(6, 0))
        ttk.Button(g1, text="Обзор…", width=10, command=self.pick_dir).grid(row=1, column=3, padx=2, pady=(6, 0))
        ttk.Button(g1, text="Где config.pro", width=15, command=self.scan_cfg).grid(row=1, column=4, padx=2, pady=(6, 0))
        ttk.Button(g1, text="Найти Creo", width=12, command=self.creo_find).grid(row=1, column=5, padx=2, pady=(6, 0))

        g1b = ttk.Frame(g1)
        g1b.grid(row=2, column=0, columnspan=6, sticky="ew", pady=(8, 0))
        ttk.Button(g1b, text="Запустить Creo", command=self.start_creo).pack(side="left")
        ttk.Button(g1b, text="README", command=self.show_readme).pack(side="left", padx=6)
        ttk.Separator(g1b, orient="vertical").pack(side="left", fill="y", padx=8)
        ttk.Label(g1b, text="отчёт:").pack(side="left")
        ttk.Button(g1b, text="Копировать", command=self.copy_log).pack(side="left", padx=4)
        ttk.Button(g1b, text="Сохранить…", command=self.save_log).pack(side="left", padx=2)
        ttk.Button(g1b, text="Очистить", command=self.clear).pack(side="left", padx=2)
        ttk.Label(g1b, text="(правый клик по отчёту — то же меню)", foreground="#8a8a8a").pack(side="left", padx=10)
        g1.columnconfigure(1, weight=1)

        # ===================== ИСПОЛНИТЕЛИ =====================
        g2 = ttk.LabelFrame(root, text=" ИСПОЛНИТЕЛИ ", padding=10)
        g2.pack(fill="x", padx=10, pady=6)

        r1 = ttk.Frame(g2)
        r1.pack(fill="x")
        self.b_scan = ttk.Button(r1, text="СКАН ПДФ (отчёт)", width=20, command=lambda: self.run("scan"))
        self.b_scan.pack(side="left")
        self.b_exp = ttk.Button(r1, text="СОЗДАТЬ / ОБНОВИТЬ ПДФ", width=26, command=lambda: self.run("export"))
        self.b_exp.pack(side="left", padx=6)
        self.b_stop = ttk.Button(r1, text="СТОП", width=10, command=self.stop, state="disabled")
        self.b_stop.pack(side="left")
        ttk.Label(r1, text="   лимит:").pack(side="left")
        self.limit = tk.StringVar(value=str(self.s.get("limit", 50)))
        ttk.Entry(r1, width=6, textvariable=self.limit).pack(side="left")
        ttk.Label(r1, text="(0 = без ограничения)", foreground="#8a8a8a").pack(side="left", padx=4)
        self.open_pdf = tk.BooleanVar(value=bool(self.s.get("open_pdf", False)))
        ttk.Checkbutton(r1, text="открывать PDF", variable=self.open_pdf).pack(side="left", padx=10)

        r2 = ttk.Frame(g2)
        r2.pack(fill="x", pady=(10, 0))
        self.del_dups = tk.BooleanVar(value=bool(self.s.get("del_dups", False)))
        ttk.Button(r2, text="Искать дубли ПДФ и не рядом", width=30, command=self.run_dups).pack(side="left")
        ttk.Checkbutton(r2, text="перемещать в корзину инструмента",
                        variable=self.del_dups).pack(side="left", padx=6)
        ttk.Separator(r2, orient="vertical").pack(side="left", fill="y", padx=12)
        self.del_nomodel = tk.BooleanVar(value=bool(self.s.get("del_nomodel", False)))
        ttk.Button(r2, text=" Искать ПДФ без модели ", width=26, command=self.run_nomodel).pack(side="left")
        ttk.Checkbutton(r2, text="перемещать в корзину инструмента",
                        variable=self.del_nomodel).pack(side="left", padx=6)

        # ===================== ОТЧЁТ =====================
        g3 = ttk.LabelFrame(root, text=" ОТЧЁТ ", padding=6)
        g3.pack(fill="both", expand=True, padx=10, pady=(6, 4))
        self.txt = tk.Text(g3, wrap="none", font=("Consolas", 9), bg="#15171A", fg="#E6E6E6",
                           insertbackground="#E6E6E6", selectbackground="#3A5A8A", padx=6, pady=4)
        ys = ttk.Scrollbar(g3, orient="vertical", command=self.txt.yview)
        xs = ttk.Scrollbar(g3, orient="horizontal", command=self.txt.xview)
        self.txt.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.txt.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        g3.rowconfigure(0, weight=1)
        g3.columnconfigure(0, weight=1)

        self.status = ttk.Label(root, text="готов", anchor="w", padding=(12, 3))
        self.status.pack(fill="x", side="bottom")

        self.menu = tk.Menu(root, tearoff=0)
        self.menu.add_command(label="Копировать выделенное", command=lambda: self.txt.event_generate("<<Copy>>"))
        self.menu.add_command(label="Копировать ВЕСЬ отчёт", command=self.copy_log)
        self.menu.add_command(label="Сохранить отчёт в файл…", command=self.save_log)
        self.menu.add_command(label="Показать, что в буфере", command=self.show_clip)
        self.menu.add_separator()
        self.menu.add_command(label="Выделить всё (Ctrl+A)", command=self.sel_all)
        self.menu.add_command(label="Очистить", command=self.clear)
        self.txt.bind("<Button-3>", lambda e: self.menu.tk_popup(e.x_root, e.y_root))
        self.txt.bind("<Control-a>", self.sel_all)
        self.txt.bind("<Control-A>", self.sel_all)
        self.txt.bind("<Control-c>", lambda e: self.txt.event_generate("<<Copy>>"))

        root.after(120, self.pump)
        self.log("Готово. Порядок: «СКАН ПДФ (отчёт)» → «СОЗДАТЬ / ОБНОВИТЬ ПДФ» → «Искать дубли ПДФ и не рядом».")
        self.log("Дубли убираются в корзину инструмента creo_pdf\\_trash (галочка «удалять дубли»).")
        self.log("Движок: " + BAT)

    def _style(self):
        try:
            st = ttk.Style()
            if "vista" in st.theme_names():
                st.theme_use("vista")
            st.configure("TButton", padding=(8, 4))
            st.configure("LabelFrame", padding=8)
            st.configure("TLabelframe.Label", font=("Segoe UI", 9, "bold"))
        except Exception:
            pass

    # =============== служебное ===============
    def _load(self):
        try:
            return json.loads(open(CFG, encoding="utf-8").read())
        except Exception:
            return {}

    def _save(self):
        try:
            open(CFG, "w", encoding="utf-8").write(json.dumps(
                {"config": self.cfg_var.get(), "folder": self.dir_var.get(), "limit": self.limit.get(),
                 "open_pdf": bool(self.open_pdf.get()), "del_dups": bool(self.del_dups.get()),
                 "del_nomodel": bool(self.del_nomodel.get())}, ensure_ascii=False, indent=1))
        except Exception:
            pass

    def log(self, line):
        self.lines.append(line)
        self.q.put(line)

    def _dump_log(self):
        text = "\n".join(self.lines) + "\n"
        # ЗАКОН ДОМА: логи программ живут в D:\AI\log\<имя>\ (мигрировано 23.09.2026)
        LOG_DIR = r"D:\AI\log\creo_pdf"
        try:
            os.makedirs(os.path.join(LOG_DIR, "runs"), exist_ok=True)
            with open(os.path.join(LOG_DIR, "last_run_log.txt"), "w", encoding="utf-8") as f:
                f.write(text)
            name = "run_" + datetime.datetime.now().strftime("%Y-%m-%d_%H%M") + ".txt"
            with open(os.path.join(LOG_DIR, "runs", name), "w", encoding="utf-8") as f:
                f.write(text)
            self.status.config(text="готов · отчёт: " + os.path.join(LOG_DIR, "runs", name))
        except Exception:
            pass

    def pump(self):
        try:
            while True:
                line = self.q.get_nowait()
                if line == "__done__":
                    self.proc = None
                    for b in (self.b_scan, self.b_exp):
                        b.config(state="normal")
                    self.b_stop.config(state="disabled")
                    self._dump_log()
                    continue
                self.txt.insert("end", line + "\n")
                self.txt.see("end")
                if line.startswith("ИТОГО") or line.startswith("чертежей:"):
                    self.status.config(text=line.strip()[:160])
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
            self.root.update()
            ok = (self.root.clipboard_get() == t)
        except Exception as e:
            self.log("tk-буфер не сработал (%s) — пробую через PowerShell" % e)
        if not ok:
            ok = self._clip_via_powershell(t)
        if ok:
            self.status.config(text="отчёт скопирован: %d строк" % n)
            self.log("— скопировано в буфер: %d строк (%d символов) —" % (n, len(t)))
        else:
            self.status.config(text="копирование не удалось")
            self.log("— КОПИРОВАНИЕ НЕ УДАЛОСЬ. Нажми «Сохранить…» — файл пишется всегда. —")

    def _clip_via_powershell(self, text):
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
        self.log("— в буфере пусто —" if not t else "— в буфере %d символов, начало: %r —" % (len(t), t[:200]))

    def save_log(self):
        p = filedialog.asksaveasfilename(title="Сохранить отчёт", defaultextension=".txt",
                                         initialfile="creo_pdf_report.txt",
                                         filetypes=[("текст", "*.txt"), ("все файлы", "*.*")])
        if not p:
            return
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(self.txt.get("1.0", "end-1c"))
            self.status.config(text="отчёт сохранён")
            self.log("— отчёт сохранён: %s —" % p)
        except Exception as e:
            self.log("не удалось сохранить отчёт: %s" % e)

    def pick_cfg(self):
        p = filedialog.askopenfilename(title="Выбрать config.pro", initialdir=os.path.dirname(DEFAULT_CFG),
                                       filetypes=[("config", "*.pro"), ("все файлы", "*.*")])
        if p:
            self.cfg_var.set(p)

    def pick_dir(self):
        p = filedialog.askdirectory(title="Выбрать папку проверки", initialdir=self.dir_var.get() or DEFAULT_DIR)
        if p:
            self.dir_var.set(p)

    # =============== движок ===============
    def _busy(self):
        if self.proc:
            messagebox.showinfo("Занято", "Сначала дождись окончания или нажми СТОП")
            return True
        return False

    def _begin(self, title):
        self._save()
        self.t0 = datetime.datetime.now()
        self.log("-" * 110)
        self.log(title)
        self.status.config(text="работаю…")
        self.b_scan.config(state="disabled")
        self.b_exp.config(state="disabled")
        self.b_stop.config(state="normal")

    def _spawn(self, args, title):
        if self._busy():
            return
        self._begin(title + ": creo_pdf " + " ".join(args))
        cmd = ["cmd", "/c", "call", BAT] + list(args)
        threading.Thread(target=self._worker, args=(cmd,), daemon=True).start()

    def _spawn_py(self, script, args, title):
        if self._busy():
            return
        self._begin(title + ": python " + script + " " + " ".join(args))
        cmd = [sys.executable, "-X", "utf8", os.path.join(HERE, script)] + list(args)
        threading.Thread(target=self._worker, args=(cmd,), daemon=True).start()

    def _worker(self, cmd):
        try:
            self.proc = subprocess.Popen(cmd, cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                         text=True, encoding="utf-8", errors="replace", bufsize=1)
            for line in self.proc.stdout:
                self.log(line.rstrip())
            _code = self.proc.wait()
            _secs = (datetime.datetime.now() - self.t0).total_seconds() if getattr(self, "t0", None) else 0.0
            self.log("готово, код %s за %.1f с" % (_code, _secs))
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

    def _folder(self):
        d = self.dir_var.get().strip()
        if not d or not os.path.isdir(d):
            messagebox.showwarning("Папка", "Выбери существующую папку проверки")
            return None
        return d

    # ---------------- рутины ----------------
    def run(self, mode):
        d = self._folder()
        if not d:
            return
        if mode == "scan":
            self._spawn(["scan", d], "СКАН ПДФ (отчёт)")
        else:
            args = ["export", d, self.limit.get().strip() or "50"]
            if self.open_pdf.get():
                args.append("open")
            self._spawn(args, "СОЗДАТЬ / ОБНОВИТЬ ПДФ" + (" (с открытием)" if self.open_pdf.get() else ""))

    def run_dups(self):
        """ОДНА кнопка: дубли PDF + PDF не рядом со своим чертежом. Галочка = ещё и убрать лишние."""
        d = self._folder()
        if not d:
            return
        args, title = [d, "--limit", "300"], "ДУБЛИ ПДФ И НЕ РЯДОМ (отчёт)"
        if self.del_dups.get():
            if not messagebox.askyesno("Переместить дубли в корзину инструмента",
                                       "Найду дубли и PDF, лежащие НЕ рядом со своим чертёжем,\n"
                                       "и ПЕРЕМЕЩУ лишние копии в корзину инструмента:\n"
                                       "creo_pdf\\_trash\\<дата>  (вернуть — руками, ничего не пропадёт).\n\n"
                                       "• единственная копия без пары рядом НЕ трогается;\n"
                                       "• документация (PDF без чертежа) НЕ трогается.\n\n"
                                       "Папка: " + d):
                return
            args, title = [d, "--apply", "--limit", "1000"], "ДУБЛИ ПДФ: УБОРКА ЛИШНИХ КОПИЙ"
        self._spawn_py("creo_pdf_misplaced.py", args, title)

    def run_nomodel(self):
        """PDF без модели рядом (документация/каталоги). Галочка = ещё и убрать (в _trash)."""
        d = self._folder()
        if not d:
            return
        args, title = [d, "--limit", "300"], "ПДФ БЕЗ МОДЕЛИ РЯДОМ (отчёт)"
        if self.del_nomodel.get():
            if not messagebox.askyesno("Переместить PDF без модели в корзину инструмента",
                                       "Будут перемещены PDF, у которых нет одноимённой модели рядом\n"
                                       "(каталоги, руководства, сканы документов):\n"
                                       "creo_pdf\\_trash\\<дата>_nomodel — вернуть можно руками.\n\n"
                                       "Папка: " + d + "\n\nПродолжить?"):
                return
            args, title = [d, "--apply", "--limit", "1000"], "ПДФ БЕЗ МОДЕЛИ: УБОРКА"
        self._spawn_py("creo_pdf_orphans.py", args, title)

    # ---------------- конфиг и Creo ----------------
    def from_session(self):
        self._spawn(["config-find"], "ГДЕ CREO ВЗЯЛ КОНФИГ (папка старта и config.pro)")

    def scan_cfg(self):
        self._spawn(["config-scan"], "ПОИСК config.pro БЕЗ СЕССИИ")

    def creo_find(self):
        self._spawn(["creo-find"], "ПОИСК УСТАНОВКИ CREO (реестр Windows)")

    def apply_cfg(self):
        c = self.cfg_var.get().strip()
        if not c or not os.path.isfile(c):
            messagebox.showwarning("config.pro", "Укажи существующий файл config.pro")
            return
        self._spawn(["config-load", c], "ПРИМЕНЕНИЕ КОНФИГА К Creo")

    def show_readme(self):
        p = os.path.join(HERE, "README.md")
        try:
            text = open(p, encoding="utf-8").read()
        except Exception as e:
            self.log("README не прочитан: %s" % e)
            return
        self.log("=" * 110)
        self.log("README: " + p)
        self.log("=" * 110)
        for line in text.splitlines():
            self.log(line)
        self.log("=" * 110)
        self.log("конец README")

    def start_creo(self):
        cfg = self.cfg_var.get().strip() or DEFAULT_CFG
        if not os.path.isfile(cfg):
            messagebox.showwarning("config.pro",
                                   "Сначала выбери существующий config.pro —\nего папка станет рабочей папкой Creo")
            return
        if not messagebox.askyesno("Штатный запуск Creo",
                                   "Запустить Creo штатно?\n\nparametric.exe с рабочей папкой:\n" +
                                   os.path.dirname(cfg) +
                                   "\n\nCreo читает config.pro из рабочей папки — оттуда придут форматки,"
                                   " MY_ESKD.dtl и table.pnt.\n(домашний CREO-START.bat не используется)"):
            return
        self._spawn(["creo-start", cfg], "ШТАТНЫЙ ЗАПУСК CREO")


def selftest(folder):
    """Проверка движка без окна (для приёмки)."""
    p = subprocess.run(["cmd", "/c", "call", BAT, "scan", folder], cwd=HERE,
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    print(out)
    return "чертежей:" in out


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--selftest":
        sys.exit(0 if selftest(sys.argv[2]) else 1)
    root = tk.Tk()
    Win(root)
    root.mainloop()