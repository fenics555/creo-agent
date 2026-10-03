# -*- coding: utf-8 -*-
"""rules — ОКНО РЕДАКТОРА ПРАВИЛ (каркас ui_common, волна 4).

КОНСТАНТА 6 волны 1 — «правила и текст, и форма»: ТЕКСТ читает человек, форма — правит.
Порядок правил важен (Move UP / Move DOWN, как у вендора B&W §3).
Движок — `rules_engine.py`, данные — `data\\rules.json` (тот же файл у агента и консоли).

Запуск: rules_gui.bat
"""
import io
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import tkinter as tk                       # noqa: E402
from tkinter import messagebox            # noqa: E402
import rules_engine as RE                  # noqa: E402
import ui_common as U                      # noqa: E402


class App:
    def __init__(self, root=None):
        self.root = root or U.make_root("V1 — ПРАВИЛА ДОМА (редактор)", "1160x700",
                                        minsize=(980, 620))
        self.root.minsize(980, 620)
        self.doc, self.err = RE.load()
        if self.doc is None:
            self.doc = {"schema": RE.SCHEMA_VERSION, "rules": []}
        self.build()

    def rules(self):
        return self.doc.setdefault("rules", [])

    def _fill_list(self):
        self.lst.delete(0, "end")
        for r in self.rules():
            self.lst.insert("end", "[%s] %-24s %s"
                            % ("вкл" if r.get("enabled", True) else "выкл",
                               r.get("id"), r.get("label", "")))

    def _fill_tree(self):
        self.tree.delete(*self.tree.get_children())
        for i, r in enumerate(self.rules(), 1):
            self.tree.insert("", "end", values=(i, r.get("id"), r.get("label"),
                                               (r.get("action") or {}).get("value", "")),
                             tags=("ok",) if r.get("enabled", True) else ("warn",))
        s = RE.stats(self.doc)
        self.set_summary(s["rules"], s["enabled"], s["rules"] - s["enabled"],
                         label="критериев: %d" % s["criteria"])

    def build(self):
        U.head(self.root, "Правила дома",
               "Слева — правила (порядок важен), справа — вид IF…THEN…END_IF и форма. "
               "Правила читает и агент, и окно, и консоль — из одного файла rules.json.")
        left, right = U.split_result_left(self.root, right_width=470)

        U.actions(left, primary=(("ПРОВЕРИТЬ ФОРМУ", self.validate),),
                  secondary=(("Сохранить", self.save), ("Показать текстом", self.show_text),
                             ("Прогнать на модели", self.run)))
        tk.Label(left, text="Код изделия для прогона на живой модели (без Creo):",
                 bg=U.BG, fg=U.MUTED, font=("Segoe UI", 8)).pack(anchor="w", padx=8)
        self.code = tk.Entry(left, width=24, font=("Consolas", 9))
        self.code.pack(anchor="w", padx=8, pady=(0, 6))
        self.code.insert(0, "G11074")
        self.tree = U.result_tree(left, ("n", "id", "label", "action"),
                                  ("№", "id", "Подпись", "Что применить"),
                                  [40, 170, 240, 280])
        self.sum_var, self.set_summary = U.summary(left)
        self._fill_tree()

        nb, pages = U.tabs(right, ["Текст правил", "Форма", "О файле"])
        self.txt = tk.Text(pages[0], height=16, font=("Consolas", 9), wrap="none",
                           bg="#101418", fg="#d8e2e8", insertbackground="#d8e2e8")
        self.txt.pack(fill="both", expand=True)
        self.txt.insert("1.0", RE.all_text(self.doc))

        form = pages[1]
        tk.Label(form, text="Порядок и включение правил:", bg=U.BG,
                 font=("Segoe UI", 9, "bold"), anchor="w").pack(anchor="w", padx=8, pady=(8, 2))
        self.lst = tk.Listbox(form, height=12, font=("Consolas", 9), bg="#ffffff")
        self.lst.pack(fill="both", expand=True, padx=8)
        self._fill_list()
        row = tk.Frame(form, bg=U.BG)
        row.pack(fill="x", padx=8, pady=6)
        for txt, cmd in (("▲ вверх", lambda: self.shift(-1)), ("▼ вниз", lambda: self.shift(1)),
                         ("Вкл/Выкл", self.toggle), ("Удалить", self.delete_rule)):
            tk.Button(row, text=txt, width=12, command=cmd).pack(side="left", padx=2)

        about = pages[2]
        info = ("Движок: rules_engine.py\nДанные: %s\nСхема: %d\n\n"
                "Операции: %s\n\nТипы критериев: %s\n\n"
                "Порядок правил ВАЖЕН: первое совпавшее правило идёт первым в отчёте.\n"
                "Если файл правил нарушает схему, он НЕ сохраняется."
                % (RE.RULES_FILE, RE.SCHEMA_VERSION, ", ".join(RE.OPS),
                   ", ".join(RE.CRITERIA_TYPES)))
        tk.Label(about, text=info, bg=U.BG, fg=U.MUTED, font=("Segoe UI", 9),
                 justify="left", anchor="nw").pack(fill="both", expand=True, padx=10, pady=8)
        U.readme_button(about, _HERE, self.log)

        self._log_box, self._log_write = U.log_view(self.root, height=6)
        self.status = U.statusbar(self.root)
        if self.err:
            self.log("⚠ %s" % self.err)
        self.log("правил: %d" % len(self.rules()))

    def log(self, s):
        try:
            self._log_write(str(s))
        except Exception:
            pass

    def run(self):
        """Применяет правила к ЖИВОЙ модели (код из таблицы) — в потоке каркаса."""
        code = self.code.get().strip() if hasattr(self, "code") else ""
        if not code:
            return self.log("введи код изделия, например G11074")
        self.status.set("собираю факты из %s…" % code)
        t0 = time.time()

        def work():
            import facts as FT
            import rules_engine as RE2
            objs, info = FT.collect(code)
            doc = RE2.load()[0]
            return objs, info, RE2.run(objs, doc) if doc else {"hits": []}

        U.run_in_thread(self.root, work, on_done=lambda r: self.show_rules(r, t0, code),
                        on_error=lambda e: self.status.set("ошибка прогона"), log=self.log)

    def show_rules(self, r, t0, code):
        objs, info, res = r
        if not objs:
            self.status.set("факты не собраны")
            self.tree.delete(*self.tree.get_children())
            return self.log("факты не собраны: %s" % info.get("error", "?"))
        self.tree.delete(*self.tree.get_children())
        for h in res["hits"]:
            self.tree.insert("", "end", values=(h["rule"], h["label"], h["object"]),
                             tags=("ok",))
        self.set_summary(len(objs), len(res["hits"]), 0,
                         label="совпадений: %d, %.2f с" % (len(res["hits"]), time.time() - t0))
        self.status.set("%s: объектов %d, совпадений %d" % (code, len(objs), len(res["hits"])))
        self.log("живая модель %s (%s): параметров %d, фактов %d, совпадений правил %d"
                 % (code, Path(info["file"]).name, info["params"], len(objs), len(res["hits"])))
        self.show_text()

    def sel(self):
        i = self.lst.curselection()
        return self.rules()[i[0]] if i else None

    def validate(self):
        errs = RE.validate(self.doc)
        if errs:
            for e in errs[:6]:
                self.log("✗ %s" % e)
            self.status.set("ошибок в правилах: %d" % len(errs))
            messagebox.showwarning("Правила неполны", "\n".join(errs[:8]))
            return False
        self.status.set("правила корректны")
        self.log("✓ правила корректны: %d, критериев: %d"
                 % (len(self.rules()),
                    sum(len(r.get("criteria") or []) for r in self.rules())))
        return True

    def save(self):
        try:
            p = RE.save(self.doc)
            self.status.set("сохранено")
            self.log("сохранено: %s" % p)
        except RE.RuleError as e:
            self.status.set("не сохранено")
            self.log("✗ %s" % e)
            messagebox.showerror("Не сохранено", str(e))

    def show_text(self):
        self.txt.delete("1.0", "end")
        self.txt.insert("1.0", RE.all_text(self.doc))
        self.log("показано текстом: %d правил" % len(self.rules()))

    def shift(self, d):
        i = self.lst.curselection()
        if not i:
            return self.log("сначала выбери правило в списке")
        try:
            j = RE.move(self.doc, self.rules()[i[0]].get("id"), d)
        except RE.RuleError as e:
            return self.log(str(e))
        self._fill_list()
        self._fill_tree()
        self.lst.selection_set(j)
        self.log("порядок изменён: правило теперь на позиции %d (порядок важен)" % (j + 1))

    def toggle(self):
        i = self.lst.curselection()
        if not i:
            return self.log("сначала выбери правило")
        r = self.rules()[i[0]]
        r["enabled"] = not r.get("enabled", True)
        self._fill_list()
        self._fill_tree()
        self.lst.selection_set(i[0])
        self.log("правило %s: %s" % (r["id"], "включено" if r["enabled"] else "выключено"))

    def delete_rule(self):
        i = self.lst.curselection()
        if not i:
            return self.log("сначала выбери правило")
        r = self.rules()[i[0]]
        if not messagebox.askyesno("Удалить правило", "Удалить правило %s?" % r["id"]):
            return
        self.rules().remove(r)
        self._fill_list()
        self._fill_tree()
        self.log("удалено правило %s (нажми «Сохранить», чтобы записать в файл)" % r["id"])


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    r = U.make_root("V1 — ПРАВИЛА ДОМА (редактор)", "1160x700", minsize=(980, 620))
    App(r)
    r.mainloop()