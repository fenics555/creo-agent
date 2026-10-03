# -*- coding: utf-8 -*-
"""dup_scan — ОКНО поиска двойников (настройки + поиск + перенос в урну).

Запуск: dup_scan_gui.bat (или python gui.py). Класс Р: Creo и агент не нужны.
Ничего не удаляет: лишние копии уезжают в `_trash_dup` рядом с файлом.
Движок — `dup_scan.py` в этой же папке (find_dups / move_extras).
"""
import json
import os
import time
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import dup_scan as eng  # noqa: E402
import ui_common as U  # noqa: E402  (волна 1: общий каркас окон, 6 дизайн-констант)

SETTINGS = Path(r"D:\AI\tools\agent\data\dup_scan_settings.json")   # манифест п.19: настройки в data\


class App:
    def __init__(self, root=None):
        self.root = root or U.make_root("V1 — ДВОЙНИКИ (одинаковые файлы)",
                                        "1020x660", minsize=(900, 580))
        self.root.minsize(900, 580)
        self.st = self.load()
        self.res = None
        self.build()

    def load(self):
        d = {"roots": [], "ext": "prt,asm,drw,pdf", "min_mb": 0.0, "mode": "report"}
        try:
            if SETTINGS.exists():
                d.update(json.loads(SETTINGS.read_text(encoding="utf-8")))
        except Exception:
            pass
        # ЖИВАЯ НАХОДКА 03.10.2026 (аудит): список папок лежал в StringVar, и `list(StringVar.get())`
        # давал СПИСОК СИМВОЛОВ — в gui_settings.json попадало ['(', "'", 'D', ':', '\\', …].
        # Перезапуск окна показывал одну «папку» из скобок, и поиск искал несуществующий путь.
        # Раньше это лечили в cmnm_scan — здесь грабля повторилась. Теперь битый список выкидываем.
        roots = [r for r in (d.get("roots") or []) if isinstance(r, str) and len(r) > 2]
        d["roots"] = roots
        try:
            d["min_mb"] = max(0.0, float(d.get("min_mb") or 0.0))
        except Exception:
            d["min_mb"] = 0.0
        if d.get("mode") not in ("report", "apply"):
            d["mode"] = "report"
        return d

    def save(self):
        try:
            # roots читаем ИЗ САМОГО СПИСКА, а не из roots_var: StringVar.get() отдаёт строку
            # «('D:\\AAA', …)», и старая запись клала в настройки список букв.
            self.st.update({"roots": list(self.lst.get(0, "end")), "ext": self.var_ext.get(),
                            "min_mb": float(self.var_min.get()), "mode": self.var_mode.get()})
            SETTINGS.parent.mkdir(parents=True, exist_ok=True)
            SETTINGS.write_text(json.dumps(self.st, ensure_ascii=False, indent=1), encoding="utf-8")
        except Exception:
            pass

    def build(self):
        # --- каркас ui_common: результат СЛЕВА, настройки СПРАВА (константа 5) ---
        U.head(self.root, "V1 — ДВОЙНИКИ (одинаковые файлы)",
               "Ничего не удаляет: лишние копии уезжают в `_trash_dup` рядом с файлом. "
               "Класс Р: Creo и агент не нужны.")
        left, right = U.split_result_left(self.root, right_width=440)

        # --- слева: результат + сводка с процентом (константа 4) ---
        _, self.btns = U.actions(left, primary=(("НАЙТИ ДВОЙНИКОВ", self.run_find),),
                                 secondary=(("ПЕРЕНЕСТИ В УРНУ", self.run_apply),
                                            ("Открыть папку отчётов",
                                             lambda: self.open_dir(eng.LOG_DIR))))
        self.b_apply = self.btns[1]
        self.b_apply.config(state="disabled")
        self.tree = U.result_tree(left, ("st", "size", "keep", "extra", "where"),
                                  ("", "МБ", "Образец (оставляем самый свежий)",
                                   "Двойников", "Где они лежат"),
                                  [40, 70, 300, 90, 280])
        self.sum_var, self.set_summary = U.summary(left)

        # --- справа: вкладки по смыслу (константа 3) ---
        nb, pages = U.tabs(right, ["Основное", "Папки", "Дополнительно"])

        # основное: ТАБЛИЦА настроек Option|Value|Status|Description (константы 1 и 2)
        self.var_ext = tk.StringVar(value=self.st["ext"])
        self.var_min = tk.DoubleVar(value=self.st["min_mb"])
        self.var_mode = tk.StringVar(value=self.st["mode"])
        spec = [{"option": "ext", "value": self.st["ext"],
                 "desc": "расширения через запятую: prt,asm,drw,pdf", "default": "prt,asm,drw,pdf"},
                {"option": "min_mb", "value": str(self.st["min_mb"]),
                 "desc": "не меньше, МБ (0 — искать всё)", "default": "0.0"},
                {"option": "mode", "value": self.st["mode"],
                 "desc": "report = только отчёт; apply = переносить в _trash_dup",
                 "default": "report"}]
        self.tbl = U.SettingsTable(pages[0], spec, log=self.log, on_apply=self._on_apply)
        self.tbl.saved = dict(self.tbl.vals)

        # папки: список остаётся списком (главное — сам список, а не таблица)
        pl = pages[1]
        tk.Label(pl, text="Где искать:", bg=U.BG, anchor="w").pack(anchor="w", padx=8)
        self.roots_var = tk.StringVar(value=self.st["roots"])
        self.lst = tk.Listbox(pl, listvariable=self.roots_var, height=6, bg="#ffffff")
        self.lst.pack(fill="both", expand=True, padx=8)
        row = tk.Frame(pl, bg=U.BG)
        row.pack(fill="x", padx=8, pady=4)
        tk.Button(row, text="Добавить папку…", command=self.add_root).pack(side="left", padx=2)
        tk.Button(row, text="Убрать", command=self.del_root).pack(side="left", padx=2)
        tk.Label(pl, text="(двойной щелчок по папке — открыть в проводнике)",
                 bg=U.BG, fg=U.MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=8)
        self.lst.bind("<Double-1>", lambda e: self.open_dir(self.selected_root()))

        # дополнительно: отчёты и журнал
        ex = pages[2]
        tk.Button(ex, text="Папка отчётов", command=lambda: self.open_dir(eng.LOG_DIR)).pack(anchor="w", padx=8, pady=3)
        U.readme_button(ex, Path(__file__).resolve().parent, self.log)

        self._log_box, self._log_write = U.log_view(self.root, height=6)
        self.status = U.statusbar(self.root)

    def _on_apply(self, vals):
        """Кнопка «Применить»: значения таблицы идут в настройки окна (файл в data\\)."""
        self.var_ext.set(vals.get("ext", self.st["ext"]))
        try:
            self.st["min_mb"] = float(vals.get("min_mb") or 0)
        except ValueError:
            self.st["min_mb"] = 0.0
        if vals.get("mode") in ("report", "apply"):
            self.st["mode"] = vals["mode"]
            self.var_mode.set(self.st["mode"])
        self.save()
        return vals

    # ---------- вспомогательное ----------
    def log(self, s):
        try:
            self._log_write(str(s))
        except Exception:
            pass

    def open_dir(self, p):
        try:
            if p and os.path.isdir(p):
                os.startfile(p)
        except Exception as e:
            messagebox.showwarning("Не открыть", "%s\n%s" % (p, e))

    def roots(self):
        """Список папок ИЗ САМОГО Listbox. StringVar.get() отдаёт строку «('D:\\AAA', …)»,
        и list(...) из неё даёт список СИМВОЛОВ — это и ломало настройки (живая проба 03.10.2026)."""
        return list(self.lst.get(0, "end"))

    def selected_root(self):
        sel = self.lst.curselection()
        return self.roots()[sel[0]] if sel else ""

    def add_root(self):
        p = filedialog.askdirectory()
        if p:
            roots = self.roots()
            if p not in roots:
                roots.append(p)
                self.roots_var.set(roots)

    def del_root(self):
        sel = self.lst.curselection()
        if not sel:
            return
        roots = self.roots()
        roots.pop(sel[0])
        self.roots_var.set(roots)
        self.save()

    # ---------- поиск и перенос ----------
    def run_find(self):
        """Поиск двойников — в потоке каркаса (окно не замирает, константа 5)."""
        roots = self.roots()
        if not roots:
            return messagebox.showwarning("Нет папок", "Добавьте хотя бы одну папку")
        self.save()
        exts = {x.strip().lower() for x in self.var_ext.get().split(",") if x.strip()}
        min_bytes = int(float(self.var_min.get()) * 1048576)
        self._t0 = time.time()
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.res = None
        self.b_apply.config(state="disabled")
        self.status.set("ищу двойники…")
        self.log("ищу двойников: %s (%.1f+ МБ, расширения: %s)" %
                 ("; ".join(roots), float(self.var_min.get()), ", ".join(sorted(exts)) or "все"))

        def work():
            return eng.find_dups(roots, exts, min_bytes,
                                 progress=lambda s: self.root.after(0, self.log, s))

        U.run_in_thread(self.root, work, on_done=self.show,
                        on_error=lambda e: self.status.set("ошибка поиска"),
                        log=self.log)

    def show(self, res):
        self.res = res
        extra_files = sum(len(g["extra"]) for g in res["groups"])
        total_files = extra_files + len(res["groups"])      # +1 образец на группу
        for g in res["groups"]:
            where = os.path.dirname(g["extra"][0][0]) if g["extra"] else ""
            self.tree.insert("", "end", values=(U.ICON_WARN, round(g["size"] / 1048576, 2),
                                                g["keep"][0], len(g["extra"]), where),
                             tags=("warn",))
        pct = self.set_summary(total_files, len(res["groups"]), extra_files,
                               label="групп: %d, лишнего %.2f ГБ, файлов: %d"
                                     % (len(res["groups"]), res["waste"] / 1073741824.0,
                                        res["files"]))
        self.status.set("найдено за %.1f с" % (time.time() - getattr(self, "_t0", time.time())))
        self.log("групп двойников: %d, лишнего объёма %.2f ГБ (проверено файлов %d, за %.1f с)"
                 % (len(res["groups"]), res["waste"] / 1073741824.0, res["files"],
                    time.time() - getattr(self, "_t0", time.time())))
        for e in res["errors"]:
            self.log("   " + e)
        enough = bool(res["groups"]) and self.var_mode.get() == "apply"
        self.b_apply.config(state="normal" if enough else "disabled")
        if res["groups"] and self.var_mode.get() != "apply":
            self.log("режим «только отчёт»: чтобы перенести в урну, переключите настройку выше")

    def run_apply(self):
        if not self.res or not self.res["groups"]:
            return
        cnt = sum(len(g["extra"]) for g in self.res["groups"])
        if not messagebox.askyesno("Подтверждение",
                                   "Перенести %d файлов-двойников в _trash_dup рядом с ними?\n"
                                   "Файлы НЕ удаляются — их можно вернуть." % cnt):
            return
        moved = 0
        for g in self.res["groups"]:
            for one in g["extra"]:
                n, errs = eng.move_extras([one])
                moved += n
                if errs:
                    self.log("   НЕ перенесён: %s (%s)" % (os.path.basename(one[0]), errs[0][1]))
                else:
                    self.log("   → в урну: %s" % os.path.basename(one[0]))
        self.log("перенесено файлов: %d" % moved)
        self.run_find()

    # README теперь показывает каркас (U.readme_button) — свой метод не нужен.


if __name__ == "__main__":
    r = U.make_root("V1 — ДВОЙНИКИ (одинаковые файлы)", "1020x660", minsize=(900, 580))
    App(r)
    r.mainloop()