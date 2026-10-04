# -*- coding: utf-8 -*-
r"""gui.py - ОКНО очистки пост-регенерации (каркас ui_common, закон трёх рук).

Запуск: postregen_clean_gui.bat (без агента, без Cline — окно самостоятельно).
Логика: ПРОВЕРИТЬ строит план и НИЧЕГО не пишет; ОЧИСТИТЬ пишет в Creo только
с галочкой согласия и только по ПРОВЕРЕННОМУ плану; СТОП рвёт цикл между
моделями. Настройки живут файлом data\postregen_clean_settings.json и переживают
перезапуск окна.
"""
import io
import sys
import time
from pathlib import Path

# НЕ переназначаем sys.stdout при импорте (урок волны 3).
_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(0, str(_HERE.parent))

import tkinter as tk                                    # noqa: E402
from tkinter import filedialog, messagebox            # noqa: E402
import plan as P                                       # noqa: E402
import apply as A                                      # noqa: E402
import ui_common as U                                  # noqa: E402

SETTINGS = "postregen_clean"

ICON_TAG = {"clear": ("warn", U.ICON_WARN), "delete": ("warn", U.ICON_WARN),
            "rename": ("warn", U.ICON_WARN), "same": ("ok", U.ICON_OK),
            "read_fail": ("fail", U.ICON_ERR)}

DEFAULTS = [
    {"option": "root", "value": P.DEFAULT_ROOT, "desc": "папка с моделями",
     "default": P.DEFAULT_ROOT},
    {"option": "mask", "value": "*.asm", "desc": "маска файлов: *.asm, *.prt",
     "default": "*.asm"},
    {"option": "only", "value": "", "desc": "только эти имена (через ;) — пусто = все",
     "default": ""},
    {"option": "postregen", "value": "да",
     "desc": "очистить уравнения ПОСТ-РЕГЕНЕРАЦИИ: да/нет", "default": "да"},
    {"option": "param_masks", "value": "",
     "desc": "удалить параметры по маскам через ; (пусто = не удалять)", "default": ""},
    {"option": "rename_map", "value": "",
     "desc": "переименовать виды: СТАРОЕ=НОВОЕ через ; (пусто = не переименовывать)",
     "default": ""},
    {"option": "limit", "value": "100", "desc": "сколько моделей просмотреть",
     "default": "100"},
    {"option": "approve", "value": "нет",
     "desc": "СОГЛАСИЕ на запись в Creo: нет/да (без «да» кнопка ОЧИСТИТЬ откажет)",
     "default": "нет"},
    {"option": "dry_run", "value": "да", "desc": "проба без записи: да/нет",
     "default": "да"},
]


class App:
    def __init__(self, root=None):
        # ПРАВКА 04.10.2026: окно найдено дизайн-сканером — «title с версией V<N>» (единственное
    # замечание из 23 окон). Окно уже на каркасе, но версия в заголовок не передавалась.
        self.root = root or U.make_root("V1 — ОЧИСТКА ПОСТ-РЕГЕНЕРАЦИИ", "1200x740",
                                        minsize=(1020, 640))
        self.plan = None
        self.res = None
        self.build()

    def build(self):
        U.head(self.root, "Очистка пост-регенерации: удаление параметров и уравнений, "
                          "переименование видов",
               "Сначала ПРОВЕРИТЬ (ничего не пишет). ОЧИСТИТЬ пишет в Creo только "
               "с галочкой согласия. Файлы на Z: программа не трогает.")
        left, right = U.split_result_left(self.root, right_width=450)
        self.stop_flag, _ = U.stop_button(left, log=self.log)
        U.actions(left, primary=(("ПРОВЕРИТЬ", self.run), ("ОЧИСТИТЬ", self.apply)),
                  secondary=(("Планы", self.open_plans),))
        self.tree = U.result_tree(left, ("st", "kind", "file", "target", "note"),
                                  ("Статус", "Вид", "Модель", "Цель", "Что найдено"),
                                  [60, 100, 190, 190, 430])
        self.sum_var, self.set_summary = U.summary(left)

        # ПОРЯДОК ВАЖЕН (живой краш 04.10.2026): журнал создаётся ДО таблицы настроек,
        # потому что SettingsTable.refresh() пишет в log при самом создании, а
        # раньше self._log_write ещё не существовал -> AttributeError, окно падало.
        self._log_box, self._log_write = U.log_view(self.root, height=6)
        self.status = U.statusbar(self.root)

        # Настройки окна живут файлом (манифест п.19) и подставляются В SPEC:
        # SettingsTable берёт значения из spec, параметра values у него нет.
        saved = U.load_settings(SETTINGS) or {}
        spec = [dict(d) for d in DEFAULTS]
        for d in spec:
            if d["option"] in saved and saved[d["option"]] is not None:
                d["value"] = str(saved[d["option"]])
        self.tbl = U.SettingsTable(right, spec, log=self.log,
                                   on_apply=self.save_settings)
        self.tbl.saved = dict(self.tbl.vals)
        U.readme_button(right, _HERE, self.log)
        self.log("сначала ПРОВЕРИТЬ: план ничего не пишет, только показывает")

    def log(self, s):
        self._log_write(s)

    def save_settings(self, vals):
        out = U.save_settings(SETTINGS, vals)
        self.log("настройки сохранены: %s" % out)
        return out

    def opts(self):
        """Настройки окна -> аргументы build_plan."""
        v = self.tbl.vals

        def yes(key):
            return (v.get(key) or "").lower() in ("да", "yes", "1", "true")

        return {"root": (v.get("root") or "").strip() or None,
                "mask": (v.get("mask") or "*.asm").strip(),
                "limit": int(v.get("limit") or 100),
                "postregen": yes("postregen"),
                "param_masks": v.get("param_masks") or "",
                "rename_map": v.get("rename_map") or "",
                "only": (v.get("only") or "").strip() or None}

    def pick_folder(self):
        d = filedialog.askdirectory(title="Папка с моделями")
        if d:
            self.tbl.vals["root"] = d
            self.tbl.refresh()
            self.log("папка: %s" % d)

    def open_plans(self):
        try:
            p = filedialog.askopenfilename(title="Планы очистки",
                                           initialdir=str(P.LOG_DIR),
                                           filetypes=[("План JSON", "*.json")])
        except Exception as e:
            self.log("диалог не открылся: %s" % e)
            return
        if p:
            self.load_plan(p)

    def load_plan(self, path):
        import json
        try:
            self.plan = json.loads(Path(path).read_text(encoding="utf-8"))
        except Exception as e:
            self.status.set("план не прочитан")
            self.log("план не прочитан: %s" % e)
            return
        self.show_plan(self.plan)
        self.status.set("план загружен: %s" % Path(path).name)
        self.log("план загружен: %s" % path)

    def run(self):
        """ПРОВЕРИТЬ: строит план и НИЧЕГО не пишет."""
        for i in self.tree.get_children():
            self.tree.delete(i)
        P.STOP["flag"] = False
        self.status.set("строю план…")
        t0 = time.time()
        o = self.opts()
        ready, why = P.stack_ready()
        if not ready:
            self.status.set("стек не готов")
            self.log("ПРОВЕРИТЬ отказ: %s" % why)
            messagebox.showwarning("Стек не готов", why)
            return

        def work():
            def prog(i, total, name):
                self.status.set("читаю %d/%d: %s" % (i, total, name))
            return P.build_plan(**o, on_step=prog)

        def done(pl):
            self.plan = pl
            if pl.get("error"):
                self.status.set("ошибка плана")
                self.log("ошибка плана: %s" % pl["error"])
                messagebox.showerror("Ошибка плана", pl["error"])
                return
            self.show_plan(pl)
            rp, jp = P.write_plan(pl)
            self.log("план записан: %s / %s (%.2f с)" % (rp, jp, time.time() - t0))
            self.status.set("план готов за %.2f с; ОЧИСТИТЬ = запись, нужно согласие"
                            % (time.time() - t0))

        U.run_in_thread(self.root, work, on_done=done,
                        on_error=lambda e: self.status.set("ошибка плана"),
                        log=self.log)

    def show_plan(self, pl):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for s in pl.get("steps", []):
            tag, icon = ICON_TAG.get(s["verdict"], ("ok", U.ICON_OK))
            self.tree.insert("", "end",
                             values=(icon, P.KIND_RU.get(s["kind"], s["kind"]),
                                     s["name"], s["target"],
                                     str(s.get("note", "")).replace("|", "/")[:300]),
                             tags=(tag,))
        c = pl.get("counts", {})
        self.set_summary(pl.get("total", 0), c.get("same", 0),
                         c.get("clear", 0) + c.get("delete", 0)
                         + c.get("rename", 0) + c.get("read_fail", 0),
                         label="изменится: %d" % pl.get("will_change", 0))

    def apply(self):
        """ОЧИСТИТЬ: пишет в Creo по ПРОВЕРЕННОМУ плану и только с согласием."""
        def yes(key):
            return (self.tbl.vals.get(key) or "").lower() in ("да", "yes", "1", "true")
        if not self.plan or not self.plan.get("steps"):
            self.status.set("сначала ПРОВЕРИТЬ (плана нет)")
            self.log("ОЧИСТИТЬ без плана: отказ")
            return
        if not yes("approve"):
            self.status.set("нет согласия — запись не начата")
            self.log("ОЧИСТИТЬ без согласия: запись НЕ началась (RC 3)")
            messagebox.showinfo(
                "Нет согласия",
                "Поставь «Согласие на запись» = да в настройках и нажми «Применить» "
                "под таблицей. Запись не начиналась.")
            return
        dry = yes("dry_run")
        files = {s["file"] for s in self.plan["steps"] if s["verdict"] in A.TO_WRITE}
        if not dry and not messagebox.askyesno(
                "Запись в Creo",
                "Прогон изменит %d моделей.\nЗАПИСЬ НЕОБРАТИМА.\nПродолжить?"
                % len(files)):
            self.status.set("отменено человеком")
            self.log("запись отменена человеком")
            return
        A.STOP["flag"] = False
        self.status.set("пишу в Creo…")
        pl = self.plan

        def work():
            return A.apply_plan(pl, approve=True, dry_run=dry, on_log=self.log)

        def done(res):
            self.res = res
            self.status.set("готово: RC %d — %s" % (res.get("rc", 0),
                                                    res.get("detail", "")))
            self.log("RC %d: %s" % (res.get("rc", 0), res.get("detail", "")))
            if res.get("results"):
                self.log("отчёт: %s" % A.write_apply_report(res))

        U.run_in_thread(self.root, work, on_done=done,
                        on_error=lambda e: self.status.set("ошибка записи"),
                        log=self.log)


if __name__ == "__main__":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    r = U.make_root("V1 — ОЧИСТКА ПОСТ-РЕГЕНЕРАЦИИ", "1200x740", minsize=(1020, 640))
    App(r)
    r.mainloop()