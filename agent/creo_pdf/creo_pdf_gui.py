# -*- coding: utf-8 -*-
r"""CREO PDF V7 — окно «ДИЗАЙН 2»: PDF чертежей (скан/обновление) + дубли + PDF без модели.
Движок: creo_pdf.bat (прямой JLINK, без CREOSON) и питоновские помощники.
Первый дизайн сохранён в design1\ (откат — скопировать обратно).

V7: скан и экспорт классифицируют чертежи по ВНУТРЕННИМ ссылкам .drw (UTF-8) и печатают правду:
    ПЕРЕИМЕНОВАН / НЕТ МОДЕЛИ / СИРОТА — плюс сводка причин в конце скана.
Движок: creo_pdf.bat (прямой JLINK, без CREOSON) и питоновские помощники.
Первый дизайн сохранён в design1\ (откат — скопировать обратно).

V5: папку можно переносить на любой диск — все пути (Creo, Java, логи, индекс, базы) ищутся
    по месту нахождения инструмента и по всем локальным дискам; см. README «ЧТО И ГДЕ ДОЛЖНО СТОЯТЬ».
V4: несколько установок Creo — «Найти Creo» находит ВСЕ и даёт выбрать версию, «Все Creo» показывает список.
V3: пути только в одном файле settings\creo_pdf_settings.json (creo_pdf_env.py --show|--set|--find-all).
Строка «Установка Creo»: Обзор… · Найти Creo · Пути — инструмент переносится на другую версию Creo.
Папка вывода PDF: поле «Папка PDF» + галочка «и копия рядом с чертежом»;
пустое поле = прежнее поведение (PDF рядом с чертежом). Скан учитывает папку вывода.

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
ENV_PY = os.path.join(HERE, "creo_pdf_env.py")     # ЕДИНЫЙ источник путей (Creo, Java, config.pro)
# НАСТРОЙКИ по шаблону инструмента дома: settings\<имя>_settings.json рядом с инструментом,
# версионируются (settings_version). Старый gui_settings.json (02.10.2026) перенесён
# в settings\backup_settings\gui_settings_legacy_2026-10-02.json — в корне остался только код.
CFG_DIR = os.path.join(HERE, "settings")
CFG = os.path.join(CFG_DIR, "creo_pdf_settings.json")
CFG_BACKUP = os.path.join(CFG_DIR, "backup_settings")
LEGACY_CFG = os.path.join(HERE, "gui_settings.json")
LEGACY_BACKUP = os.path.join(CFG_BACKUP, "gui_settings_legacy_2026-10-02.json")
SETTINGS_VERSION = 3
DEFAULT_CFG = r"Z:\PTC\CREO-START\START-STD\config.pro"
DEFAULT_DIR = r"Z:\PTC\Work"
_PATH_KEYS = ("creo_install", "creo_common", "java_bin", "pfcasync_jar",
              "config_pro", "work_dir", "pdf_out")


def env_find_all():
    """Все установки Creo как список словарей (пусто, если не нашлось)."""
    try:
        p = subprocess.run(_env("--find-all"), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=90)
        out = (p.stdout or "")
    except Exception:
        return []
    cands, cur = [], None
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("в настройках сейчас:"):
            cur = s.split(":", 1)[1].strip()
            continue
        if s[:1].isdigit() and ") Creo" in s:
            body = s.split(") ", 1)[1]
            ver, _sp, ins = body.partition("  ")
            cands.append({"version": ver.replace("Creo", "").strip() or "?",
                          "install": ins.strip(), "common": "", "ok": None, "src": ""})
        elif cands and s.startswith("Common Files:"):
            cands[-1]["common"] = s.split(":", 1)[1].strip()
        elif cands and s.startswith("источник"):
            txt = s.split(":", 1)[1].strip()
            cands[-1]["ok"] = ("НЕ ГОДЕН" not in txt)
            cands[-1]["src"] = txt
    for c in cands:
        if cur and cur.endswith(str(cands.index(c) + 1)):
            c["current"] = True
    return cands


def _env(*args):
    """Команда чтения из единого источника настроек (creo_pdf_env.py)."""
    return [sys.executable, "-X", "utf8", ENV_PY] + list(args)


def env_show():
    """Прочитанные пути инструмента: (текст для окна, {ключ: значение})."""
    try:
        p = subprocess.run(_env("--show"), capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        out = (p.stdout or "").strip()
    except Exception as e:
        return ("Не удалось прочитать настройки инструмента:\n%s" % e), {}
    vals = {}
    for line in out.splitlines():
        if "=" in line:
            k, _, v = line.strip().partition("=")
            k = k.strip()
            if k in _PATH_KEYS:
                vals[k] = v.strip()
    return out, vals


class Win:
    def __init__(self, root):
        self.root = root
        self.proc = None
        self.q = queue.Queue()
        self.lines = []
        self.s = self._load()

        root.title("CREO PDF V7 — чертежи, дубли, PDF без модели  ·  дизайн 2")
        root.geometry("1180x740")
        root.minsize(900, 560)
        self._style()

        # ===================== НАСТРОЙКИ =====================
        g1 = ttk.LabelFrame(root, text=" НАСТРОЙКИ ", padding=10)
        g1.pack(fill="x", padx=10, pady=(10, 6))

        ttk.Label(g1, text="Установка Creo:").grid(row=0, column=0, sticky="w", pady=(8, 0))
        _txt, self.paths = env_show()
        self.creo_var = tk.StringVar(value=self.s.get("creo_install") or self.paths.get("creo_install", ""))
        ttk.Entry(g1, textvariable=self.creo_var).grid(row=0, column=1, columnspan=2, sticky="ew", padx=6, pady=(8, 0))
        ttk.Button(g1, text="Обзор…", width=10, command=self.pick_creo).grid(row=0, column=3, padx=2, pady=(8, 0))
        ttk.Button(g1, text="Найти Creo", width=12, command=self.find_creo).grid(row=0, column=4, padx=2, pady=(8, 0))
        ttk.Button(g1, text="Пути", width=8, command=self.show_paths).grid(row=0, column=5, padx=2, pady=(8, 0))

        ttk.Label(g1, text="config.pro:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.cfg_var = tk.StringVar(value=self.s.get("config") or self.paths.get("config_pro") or DEFAULT_CFG)
        ttk.Entry(g1, textvariable=self.cfg_var).grid(row=1, column=1, columnspan=2, sticky="ew", padx=6, pady=(6, 0))
        ttk.Button(g1, text="Обзор…", width=10, command=self.pick_cfg).grid(row=1, column=3, padx=2, pady=(6, 0))
        ttk.Button(g1, text="Из сессии", width=12, command=self.from_session).grid(row=1, column=4, padx=2, pady=(6, 0))
        ttk.Button(g1, text="Применить к Creo", width=17, command=self.apply_cfg).grid(row=1, column=5, padx=2, pady=(6, 0))

        ttk.Label(g1, text="Папка проверки:").grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.dir_var = tk.StringVar(value=self.s.get("folder") or self.paths.get("work_dir") or DEFAULT_DIR)
        ttk.Entry(g1, textvariable=self.dir_var).grid(row=2, column=1, columnspan=2, sticky="ew", padx=6, pady=(6, 0))
        ttk.Button(g1, text="Обзор…", width=10, command=self.pick_dir).grid(row=2, column=3, padx=2, pady=(6, 0))
        ttk.Button(g1, text="Где config.pro", width=15, command=self.scan_cfg).grid(row=2, column=4, padx=2, pady=(6, 0))
        ttk.Button(g1, text="Все Creo", width=10, command=self.show_all_creo).grid(row=2, column=5, padx=2, pady=(6, 0))

        ttk.Label(g1, text="Папка PDF (куда выводить):").grid(row=3, column=0, sticky="w", pady=(6, 0))
        self.out_var = tk.StringVar(value=self.s.get("pdf_out", ""))
        ttk.Entry(g1, textvariable=self.out_var).grid(row=3, column=1, columnspan=2, sticky="ew", padx=6, pady=(6, 0))
        ttk.Button(g1, text="Обзор…", width=10, command=self.pick_out).grid(row=3, column=3, padx=2, pady=(6, 0))
        self.dup_near = tk.BooleanVar(value=bool(self.s.get("dup_near", False)))
        ttk.Checkbutton(g1, text="и копия рядом с чертежом", variable=self.dup_near).grid(
            row=3, column=4, columnspan=2, sticky="w", padx=2, pady=(6, 0))
        ttk.Label(g1, text="(пусто = PDF рядом с чертежом, как раньше)", foreground="#8a8a8a").grid(
            row=4, column=1, columnspan=4, sticky="w", padx=6)

        g1b = ttk.Frame(g1)
        g1b.grid(row=5, column=0, columnspan=6, sticky="ew", pady=(8, 0))
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
        """Читает настройки. Порядок: новый settings\\creo_pdf_settings.json, затем старый
        gui_settings.json (миграция, копия в backup_settings). Пустой/битый файл = {} без падения."""
        data = {}
        if os.path.isfile(CFG):
            # Новый файл есть — он главный. Если он битый, молча откатываться к старому НЕЛЬЗЯ:
            # пользователь увидит старые настройки и не поймёт, почему его правки пропали.
            try:
                with open(CFG, encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, dict):
                    data = {}
            except Exception:
                data = {}
        else:
            # старый файл настроек: ищем в корне (старые копии) и в settings\backup_settings (перенесённый)
            src = next((p for p in (LEGACY_CFG, LEGACY_BACKUP) if os.path.isfile(p)), None)
            if src:
                try:
                    with open(src, encoding="utf-8") as f:
                        data = json.load(f)
                    if not isinstance(data, dict):
                        data = {}
                except Exception:
                    data = {}
                try:
                    os.makedirs(CFG_BACKUP, exist_ok=True)
                    stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
                    with open(os.path.join(CFG_BACKUP, "gui_settings_%s.json" % stamp), "w",
                              encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=1)
                except Exception:
                    pass
        return data

    def _save(self):
        """Пишет настройки в settings\\creo_pdf_settings.json. Прочие поля файла сохраняются
        (незнакомые ключи не теряются). Перед перезаписью — копия в backup_settings с ротацией."""
        try:
            prev = {}
            if os.path.isfile(CFG):
                with open(CFG, encoding="utf-8") as f:
                    prev = json.load(f) or {}
            if not isinstance(prev, dict):
                prev = {}
            prev.update({
                "settings_version": SETTINGS_VERSION,
                "creo_install": self.creo_var.get().strip(),
                "config": self.cfg_var.get(),
                "folder": self.dir_var.get(),
                "pdf_out": self.out_var.get(),
                "dup_near": bool(self.dup_near.get()),
                "limit": self.limit.get(),
                "open_pdf": bool(self.open_pdf.get()),
                "del_dups": bool(self.del_dups.get()),
                "del_nomodel": bool(self.del_nomodel.get()),
            })
            os.makedirs(CFG_DIR, exist_ok=True)
            if os.path.isfile(CFG):
                os.makedirs(CFG_BACKUP, exist_ok=True)
                stamp = datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
                with open(os.path.join(CFG_BACKUP, "creo_pdf_settings_%s.json" % stamp), "w",
                          encoding="utf-8") as f:
                    json.dump(prev, f, ensure_ascii=False, indent=1)
                self._rotate_backups(5)
            with open(CFG, "w", encoding="utf-8") as f:
                json.dump(prev, f, ensure_ascii=False, indent=1)
            return True
        except Exception as e:
            self.log("настройки НЕ сохранены: %s" % e)
            return False

    @staticmethod
    def _rotate_backups(keep):
        """Ротация бэкапов настроек: оставить последние N файлов ПО ВРЕМЕНИ (шаблон инструмента).
        Сортировка по имени не годится: имена с разными префиксами чередуются."""
        try:
            items = [(os.path.getmtime(os.path.join(CFG_BACKUP, n)), n)
                     for n in os.listdir(CFG_BACKUP)]
            items.sort()
            for _mtime, name in items[:-keep] if len(items) > keep else []:
                os.remove(os.path.join(CFG_BACKUP, name))
        except Exception:
            pass

    def log(self, line):
        self.lines.append(line)
        self.q.put(line)

    def _dump_log(self):
        text = "\n".join(self.lines) + "\n"
        # Путь логов — из единого источника (инструмент может лежать на любом диске).
        # ЗАКОН ДОМА: логи программ живут в D:\AI\log\<имя>\ ; при переносе инструмента —
        # рядом с ним; при полном отсутствии — в %LOCALAPPDATA%\creo_pdf\logs.
        import importlib.util as _ilu
        try:
            _s = _ilu.spec_from_file_location("_env", ENV_PY)
            _env = _ilu.module_from_spec(_s)
            _s.loader.exec_module(_env)
            LOG_DIR = _env.find_logs_dir()
        except Exception:
            LOG_DIR = os.path.join(HERE, "logs")
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
        """Копирование отчёта. Проба в 3 ступени, потому что буфер Tk ненадёжен:
        текст пропадает при переходе в другое приложение, хотя сразу после вставки
        проверка проходит. Поэтому главный путь — WinAPI (буфер переживает окно),
        PowerShell — запасной, Tk — только последний."""
        t = self.txt.get("1.0", "end-1c")
        n = len(t.splitlines())
        ok, how = self._clip_winapi(t), "WinAPI"
        if not ok:
            ok, how = self._clip_via_powershell(t), "PowerShell"
        if not ok:
            ok, how = self._clip_tk(t), "буфер окна"
        if ok:
            self.status.config(text="отчёт скопирован: %d строк (%s)" % (n, how))
            self.log("— скопировано в буфер: %d строк, %d символов, способ: %s —" % (n, len(t), how))
        else:
            self.status.config(text="копирование не удалось")
            self.log("— КОПИРОВАНИЕ НЕ УДАЛОСЬ (все 3 способа). Нажми «Сохранить…» — "
                     "файл пишется всегда. —")

    @staticmethod
    def _clip_winapi(text):
        """Копирование прямо в буфер обмена Windows (CF_UNICODETEXT). Не зависит от
        окна: буфер остаётся после переключения на другое приложение."""
        try:
            import ctypes
            k32, u32 = ctypes.windll.kernel32, ctypes.windll.user32
            # ОБЯЗАТЕЛЬНО: без этих объявлений ctypes трактует 64-битные указатели как int,
            # и адрес обрезается — буфер «записывается», но читается мусор (проверено 02.10.2026).
            k32.GlobalAlloc.restype = ctypes.c_void_p
            k32.GlobalLock.restype = ctypes.c_void_p
            u32.GetClipboardData.restype = ctypes.c_void_p
            GMEM_MOVEABLE = 0x0002
            CF_UNICODETEXT = 13
            data = text + "\0"
            size = len(data) * ctypes.sizeof(ctypes.c_wchar)
            k32.GlobalAlloc.restype = ctypes.c_void_p
            handle = k32.GlobalAlloc(GMEM_MOVEABLE, size)
            if not handle:
                return False
            locked = k32.GlobalLock(ctypes.c_void_p(handle))
            if not locked:
                return False
            ctypes.memmove(locked, ctypes.create_unicode_buffer(data), size)
            k32.GlobalUnlock(ctypes.c_void_p(handle))
            if not u32.OpenClipboard(None):
                return False
            try:
                u32.EmptyClipboard()
                ok = u32.SetClipboardData(CF_UNICODETEXT, ctypes.c_void_p(handle))
            finally:
                u32.CloseClipboard()
            if not ok:
                k32.GlobalFree(ctypes.c_void_p(handle))
                return False
            # ПРОВЕРКА: читаем обратно из буфера — верим только факту чтения
            if not u32.OpenClipboard(None):
                return False
            try:
                got = u32.GetClipboardData(CF_UNICODETEXT)
                if not got:
                    return False
                p = ctypes.wstring_at(ctypes.c_void_p(k32.GlobalLock(ctypes.c_void_p(got))))
            finally:
                u32.CloseClipboard()
            return p.rstrip("\r\n") == text.rstrip("\r\n")
        except Exception:
            return False

    def _clip_tk(self, text):
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            return self.root.clipboard_get() == text
        except Exception:
            return False

    def _clip_via_powershell(self, text):
        """Запасной способ: файл UTF-16 → Set-Clipboard. Проверяем ЧТЕНИЕМ из буфера."""
        tmp = os.path.join(HERE, "_clip_tmp.txt")
        try:
            with open(tmp, "w", encoding="utf-16") as f:
                f.write(text)
            subprocess.run(["powershell", "-NoProfile", "-Command", "Set-Clipboard -Path '%s'" % tmp],
                           capture_output=True, timeout=90)
            back = subprocess.run(["powershell", "-NoProfile", "-Command",
                                   "Get-Clipboard -Raw"],
                                  capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=90)
            got = (back.stdout or "").replace("\r\n", "\n").rstrip("\n")
            return got == text.replace("\r\n", "\n").rstrip("\n")
        except Exception as e:
            self.log("PowerShell-буфер не сработал: %s" % e)
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

    # ---------------- единый источник путей ----------------
    def pick_creo(self):
        """Ручной выбор корня установки Creo: указываем папку с parametric.exe (…\\Parametric\\bin)."""
        start = self.creo_var.get().strip() or (self.paths.get("creo_install") or DEFAULT_DIR)
        p = filedialog.askdirectory(title="Выбрать папку установки Creo (…\\Parametric)", initialdir=start)
        if not p:
            return
        # если указали корень уровнем выше (…\\Creo 12.4.2.0) — спускаемся в Parametric
        if not os.path.isfile(os.path.join(p, "bin", "parametric.exe")):
            sub = os.path.join(p, "Parametric")
            if os.path.isfile(os.path.join(sub, "bin", "parametric.exe")):
                p = sub
        self.creo_var.set(p)
        self.log("установка Creo указана вручную: " + p)

    def find_creo(self):
        """ВЫБОР версии: показываем ВСЕ найденные установки и даём выбрать нужную.
        Если установка одна — сразу записываем её, без лишнего вопроса."""
        cands = env_find_all()
        for line in ["=" * 100, "ПОИСК УСТАНОВОК CREO (реестр + диски)"]:
            self.log(line)
        if not cands:
            self.log("  НИ ОДНОЙ УСТАНОВКИ НЕ НАЙДЕНО — укажи путь кнопкой «Обзор…»")
            messagebox.showwarning("Creo", "Установки Creo не найдены.\n"
                                          "Укажи папку вручную кнопкой «Обзор…».")
            return
        for i, c in enumerate(cands, 1):
            self.log("  %d) Creo %-10s %s  [%s]" % (i, c["version"], c["install"],
                                                     "годен" if c["ok"] else "НЕ ГОДЕН"))
        cur = self.creo_var.get().strip().lower()
        cur_i = next((i for i, c in enumerate(cands, 1) if c["install"].lower() == cur), 0)
        pick = cur_i or 1
        if len(cands) > 1:
            dlg = tk.Toplevel(self.root)
            dlg.title("Выбор установки Creo")
            dlg.transient(self.root)
            ttk.Label(dlg, text="Найдено установок: %d. Какую использовать?" % len(cands),
                      padding=10).pack(anchor="w")
            lb = tk.Listbox(dlg, width=110, height=min(len(cands) + 1, 8), font=("Consolas", 9))
            for i, c in enumerate(cands, 1):
                mark = " ← сейчас в настройках" if i == cur_i else ""
                lb.insert("end", "%d) Creo %-10s %s%s" % (i, c["version"], c["install"], mark))
            lb.selection_set(pick - 1)
            lb.pack(padx=10, pady=4)
            chosen = {"i": pick}

            def ok(_ev=None):
                chosen["i"] = lb.curselection()[0] + 1 if lb.curselection() else pick
                dlg.destroy()

            row = ttk.Frame(dlg)
            row.pack(pady=8)
            ttk.Button(row, text="Выбрать", command=ok).pack(side="left", padx=4)
            ttk.Button(row, text="Отмена", command=dlg.destroy).pack(side="left", padx=4)
            lb.bind("<Double-Button-1>", ok)
            self.root.wait_window(dlg)
            pick = chosen["i"]
        c = cands[pick - 1]
        self.creo_var.set(c["install"])
        self._save()
        self.log("— выбрана установка: Creo %s → %s (записано в настройки)" % (c["version"], c["install"]))
        if not c["ok"]:
            self.log("  ВНИМАНИЕ: у этой установки не найдена JLINK-библиотека — проверь путь.")

    def show_all_creo(self):
        """Просто показать в логе ВСЕ найденные установки — ничего не меняя."""
        cands = env_find_all()
        self.log("=" * 100)
        self.log("ВСЕ УСТАНОВКИ CREO НА МАШИНЕ: %d" % len(cands))
        for i, c in enumerate(cands, 1):
            self.log("  %d) Creo %-10s %s  [%s]" % (i, c["version"], c["install"],
                                                     "годен" if c["ok"] else "НЕ ГОДЕН"))
            self.log("     %s" % c["common"])
        if not cands:
            self.log("  ничего не найдено")
        else:
            self.log("  выбрать одну: кнопка «Найти Creo» в строке «Установка Creo»")

    def show_paths(self):
        """Показать все пути инструмента: где что лежит и откуда взято."""
        text, _vals = env_show()
        self.log("=" * 100)
        for line in text.splitlines():
            self.log(line)
        self.log("— единый файл настроек: " + CFG + " —")

    def pick_dir(self):
        p = filedialog.askdirectory(title="Выбрать папку проверки", initialdir=self.dir_var.get() or DEFAULT_DIR)
        if p:
            self.dir_var.set(p)

    def pick_out(self):
        start = self.out_var.get().strip() or self.dir_var.get().strip() or DEFAULT_DIR
        p = filedialog.askdirectory(title="Выбрать папку для PDF", initialdir=start)
        if p:
            self.out_var.set(p)

    # ---------------- папка вывода PDF ----------------
    def _out_dir(self, for_scan=False):
        """Папка назначения PDF. Пустая строка = «рядом с чертежом» (прежнее поведение),
        это НЕ ошибка. Непустая должна быть папкой (создаём) либо её нельзя создать."""
        o = self.out_var.get().strip().strip('"')
        if not o:
            return None
        if os.path.isfile(o):
            messagebox.showerror("Папка PDF", "Это ФАЙЛ, а не папка:\n" + o)
            return False
        if not os.path.isdir(o):
            try:
                os.makedirs(o, exist_ok=True)
            except Exception as e:
                messagebox.showerror("Папка PDF", "Папку создать не удалось:\n%s\n\n%s" % (o, e))
                return False
        if not os.access(o, os.W_OK):
            messagebox.showerror("Папка PDF", "Нет прав на запись в:\n" + o)
            return False
        return o

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
        # Пути с пробелами: каждый аргумент в кавычках (иначе cmd режет строку по пробелу)
        cmd = ["cmd", "/c", "call", BAT] + ['"%s"' % x if " " in x else x for x in args]
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
        o = self._out_dir()          # None = рядом с чертежом, False = ошибка (уже показана)
        if o is False:
            return
        out_flags = []
        if o:
            out_flags = ["--out", o]
            if self.dup_near.get():
                out_flags.append("--dup")
        if mode == "scan":
            self._spawn(["scan", d] + out_flags, "СКАН ПДФ (отчёт)")
        else:
            args = ["export", d, self.limit.get().strip() or "50"] + out_flags
            if self.open_pdf.get():
                args.append("open")
            self._save()
            self._spawn(args, "СОЗДАТЬ / ОБНОВИТЬ ПДФ" + (" (с открытием)" if self.open_pdf.get() else "")
                       + (" [в папку: %s%s]" % (o, " + копия рядом" if self.dup_near.get() else "")
                          if o else " [рядом с чертежом]"))

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