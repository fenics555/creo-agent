# -*- coding: utf-8 -*-
"""drawing_audit - ОКНО аудита чертежа (каркас ui_common, волна 6, этап 4 плана).

Запуск: drawing_audit_gui.bat. Класс Р: Creo и агент не нужны, только чтение PDF.
Движок - `drawing_audit.py` в этой же папке (check_file/scan/preview).

Что показывает окно: замечания по чек-листу плашек, формат листа, читаемость текста,
наличие графики (вектор/растр) и кнопку «Превью» - картинку выбранного чертежа.
"""
import io
import os
import sys
import time
from pathlib import Path

# НЕ переназначаем sys.stdout при импорте: проба может импортировать это окно,
# и вторая обёртка TextIOWrapper закрыла бы первый поток (урок волны 3).
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import tkinter as tk                         # noqa: E402
from tkinter import filedialog               # noqa: E402
import drawing_audit as eng                  # noqa: E402
import ui_common as U                         # noqa: E402

ICON_TAG = {"ok": ("ok", U.ICON_OK), "warn": ("warn", U.ICON_WARN),
            "error": ("fail", U.ICON_ERR)}


class App:
    def __init__(self, root=None):
        self.root = root or U.make_root("V1 — АУДИТ ЧЕРТЕЖА (проверка)", "1150x700",
                                        minsize=(980, 620))
        self.root.minsize(980, 620)
        self.st = eng.load_settings()
        self.res = None
        self.rows = []
        self.build()

    def build(self):
        U.head(self.root, "Аудит чертежа (PDF): плашки, штриховка, листы",
               "Проверяет результат, а не рисует: что есть на чертеже и чего не хватает "
               "по чек-листу. Ничего не чинит и не меняет (класс Р).")
        left, right = U.split_result_left(self.root, right_width=450)
        U.actions(left, primary=(("ПРОВЕРИТЬ", self.run),),
                  secondary=(("Превью чертежа", self.preview),))
        self.tree = U.result_tree(left, ("st", "file", "check", "note"),
                                  ("Статус", "Чертёж", "Проверка", "Что не так"),
                                  [60, 200, 170, 430])
        self.sum_var, self.set_summary = U.summary(left)

        nb, pages = U.tabs(right, ["Чек-лист", "Отчёты"])
        self.tbl = U.SettingsTable(pages[0], [
            {"option": "folders", "value": "; ".join(self.st.get("folders") or []),
             "desc": "папки с PDF-чертежами через «;» (пусто = боевые)",
             "default": "; ".join(str(d) for d in eng.DEFAULT_DIRS)},
            {"option": "notes", "value": self.st.get("notes", ""),
             "desc": "обязательные плашки через «;» - правьте без кода",
             "default": eng.DEFAULTS["notes"]},
            {"option": "hatch_pages", "value": str(self.st.get("hatch_pages", 1)),
             "desc": "сколько листов с графикой считать «есть штриховка»", "default": "1"},
            {"option": "vector_min", "value": str(self.st.get("vector_min", 50)),
             "desc": "меньше примитивов на листе - лист без графики", "default": "50"},
            {"option": "show_ok", "value": self.st.get("show_ok", "нет"),
             "desc": "показывать ли успешные проверки: нет/да", "default": "нет"},
        ], log=self.log, on_apply=self._on_apply)
        self.tbl.saved = dict(self.tbl.vals)

        rep = pages[1]
        tk.Button(rep, text="Открыть папку отчётов",
                  command=self.open_reports).pack(anchor="w", padx=8, pady=6)
        tk.Button(rep, text="Добавить папку…",
                  command=self.pick_folder).pack(anchor="w", padx=8, pady=3)
        U.readme_button(rep, _HERE, self.log)

        self._log_box, self._log_write = U.log_view(self.root, height=6)
        self.status = U.statusbar(self.root)
        self.log("проверка ничего не меняет на диске - только читает PDF-чертежи")

    def log(self, s):
        try:
            self._log_write(str(s))
        except Exception:
            pass

    def _on_apply(self, vals):
        """Применить: пишем чек-лист в data\\drawing_audit_settings.json (без правки кода)."""
        out = dict(vals)
        out["folders"] = [x.strip() for x in vals.get("folders", "").split(";") if x.strip()]
        for k in ("hatch_pages", "vector_min"):
            try:
                out[k] = int(vals.get(k) or 0)
            except ValueError:
                out[k] = eng.DEFAULTS[k]
        path = eng.save_settings(out)
        self.log("настройки сохранены: %s" % path)
        return vals

    def settings(self):
        """Настройки ровно как в таблице окна (не из файла - иначе правка не видна)."""
        v = self.tbl.vals
        st = dict(self.st)
        st["notes"] = v.get("notes", "")
        st["folders"] = [x.strip() for x in v.get("folders", "").split(";") if x.strip()]
        for k in ("hatch_pages", "vector_min"):
            try:
                st[k] = int(v.get(k) or eng.DEFAULTS[k])
            except ValueError:
                st[k] = eng.DEFAULTS[k]
        st["show_ok"] = v.get("show_ok", "нет")
        return st

    def open_reports(self):
        try:
            os.startfile(str(eng.REPORT_DIR))
        except Exception as e:
            self.log("не открыть папку отчётов: %s" % e)

    def pick_folder(self):
        p = filedialog.askdirectory()
        if not p:
            return
        cur = [x for x in self.tbl.vals.get("folders", "").split(";") if x.strip()]
        if p not in cur:
            cur.append(p)
            self.tbl.vals["folders"] = "; ".join(cur)
            self.tbl.refresh()
        self.log("добавлена папка: %s" % p)

    def selected_file(self):
        sel = self.tree.selection()
        if not sel:
            return None
        vals = self.tree.item(sel[0], "values")
        return vals[1] if vals else None

    def run(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        st = self.settings()
        self.status.set("проверяю...")
        t0 = time.time()

        def work():
            dirs = [Path(d) for d in (st.get("folders") or eng.DEFAULT_DIRS)]
            return eng.scan(dirs, st)

        U.run_in_thread(self.root, work,
                        on_done=lambda r: self.show(r, t0, st),
                        on_error=lambda e: self.status.set("ошибка проверки"),
                        log=self.log)

    def show(self, res, t0, st):
        self.res = res
        self.rows = res["rows"]
        show_ok = st.get("show_ok") == "да"
        n = 0
        for r in res["rows"]:
            if r["verdict"] == "ok" and not show_ok:
                continue
            n += 1
            tag, icon = ICON_TAG[r["verdict"]]
            self.tree.insert("", "end",
                             values=(icon, Path(r["path"]).name, r["id"], r["note"]),
                             tags=(tag,))
        ok_rows = sum(1 for r in res["rows"] if r["verdict"] == "ok")
        self.set_summary(len(res["rows"]), ok_rows, res["warns"],
                         label="строк в таблице: %d, %.2f с" % (n, time.time() - t0))
        self.status.set("готово за %.2f с: ошибок %d, предупреждений %d"
                        % (time.time() - t0, res["errors"], res["warns"]))
        folders = len({os.path.dirname(r["path"]) for r in res["rows"]})
        self.log("проверено папок: %d, чертежей: %d, ошибок: %d, предупреждений: %d"
                 % (folders, res["checked"], res["errors"], res["warns"]))
        try:
            rp, cp = eng.write_report(res, time.time() - t0)
            self.log("отчёт: %s" % rp)
            self.log("CSV: %s" % cp)
        except Exception as e:
            self.log("отчёт не записан: %s" % e)

    def preview(self):
        """Превью выбранного чертежа: картинка в log\\drawing_audit, тоже в потоке."""
        name = self.selected_file()
        if not name:
            self.status.set("сначала выберите чертёж в таблице")
            self.log("превью: не выбран чертёж")
            return
        target = next((r["path"] for r in self.rows
                       if Path(r["path"]).name == name), None)
        if not target:
            self.status.set("чертёж не найден в прогоне - сначала нажмите ПРОВЕРИТЬ")
            return
        self.status.set("строю превью...")

        def work():
            return eng.preview(target, page=1, dpi=110)

        def done(path):
            self.log("превью: %s" % path)
            self.status.set("превью готово: %s" % path)

        U.run_in_thread(self.root, work, on_done=done,
                        on_error=lambda e: self.status.set("превью не построилось"),
                        log=self.log)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    r = U.make_root("V1 — АУДИТ ЧЕРТЕЖА (проверка)", "1150x700", minsize=(980, 620))
    App(r)
    r.mainloop()