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
        ttk.Label(bar, text="   лимит:").pack(side="left")
        self.limit = tk.StringVar(value=str(self.s.get("limit", 50)))
        ttk.Entry(bar, width=6, textvariable=self.limit).pack(side="left")
        self.b_exp = ttk.Button(bar, text="СОЗДАТЬ / ОБНОВИТЬ PDF", command=lambda: self.run("export"))
        self.b_exp.pack(side="left", padx=6)
        self.b_stop = ttk.Button(bar, text="СТОП", command=self.stop, state="disabled")
        self.b_stop.pack(side="left")
        ttk.Button(bar, text="Очистить лог", command=self.clear).pack(side="left", padx=6)
        self.status = ttk.Label(bar, text="готов")
        self.status.pack(side="right")

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
                {"config": self.cfg_var.get(), "folder": self.dir_var.get(), "limit": self.limit.get()},
                ensure_ascii=False, indent=1))
        except Exception:
            pass

    def log(self, line):
        self.q.put(line)

    def pump(self):
        try:
            while True:
                line = self.q.get_nowait()
                if line == "__done__":
                    self.proc = None
                    self.b_scan.config(state="normal"); self.b_exp.config(state="normal")
                    self.b_stop.config(state="disabled")
                    self.status.config(text="готов")
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
            self._spawn(["export", d, self.limit.get().strip() or "50"], "ЭКСПОРТ PDF")

    def from_session(self):
        self._spawn(["config-find"], "ПОИСК КОНФИГА (папка старта Creo и config.pro)")

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