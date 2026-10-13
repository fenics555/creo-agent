# -*- coding: utf-8 -*-
r"""skills_index — ОКНО поиска по смыслу (рука 2 канона; рука 1 — skills_index.py CLI).

Поиск скилла/инструмента/закона по СМЫСЛУ (эмбеддинги), перестройка индекса кнопкой,
статус. Настройки окна — в settings\settings.json (tool_dir=HERE). Класс Р.
Движок тянет Ollama только в рантайме (поиск/перестройка), не при импорте окна.
"""
import sys
import tkinter as tk
from argparse import Namespace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
import skills_index as eng  # noqa: E402
import ui_common as U       # noqa: E402

TITLE = "ПОИСК ПО СМЫСЛУ (скиллы дома)"
DEFAULTS = {"last_query": "", "top": 5}


class App:
    def __init__(self, root=None):
        self.root = root or U.make_root(TITLE, "1020x640", minsize=(900, 560), tool_dir=HERE)
        self.st = U.load_settings("skills_index", DEFAULTS, tool_dir=HERE)
        self.build()
        self.refresh_status()

    def log(self, s):
        self._log_write(s)

    def build(self):
        U.head(self.root, TITLE,
               "Ищет скилл/инструмент/закон по СМЫСЛУ (векторный поиск, nomic-embed), "
               "а не по словам. Кнопка «ПЕРЕСОБРАТЬ» обновляет индекс из файлов дома. "
               "Класс Р: Creo не нужен; Ollama нужна только для поиска/перестройки.")
        top = tk.Frame(self.root); top.pack(fill="x", padx=10, pady=6)
        tk.Label(top, text="Запрос:").pack(side="left")
        self.var_q = tk.StringVar(value=self.st.get("last_query", ""))
        tk.Entry(top, textvariable=self.var_q, width=70).pack(side="left", padx=6)
        self.var_top = tk.IntVar(value=int(self.st.get("top", 5)))
        tk.Spinbox(top, from_=1, to=20, width=4, textvariable=self.var_top).pack(side="left")
        U.actions(top, primary=(("НАЙТИ ПО СМЫСЛУ", self.do_search),
                                ("ПЕРЕСОБРАТЬ ИНДЕКС", self.do_build)))
        left, _ = U.split_result_left(self.root)
        self.tree = U.result_tree(left, ("score", "file"),
                                  ("Оценка", "Файл"), [90, 700])
        self.sum_var, self.set_summary = U.summary(left)
        self._log_box, self._log_write = U.log_view(self.root, height=6)
        self.status = U.statusbar(self.root)
        self.tree.bind("<Double-1>", self.open_path)
        self.var_q.trace_add("write", lambda *_: self.save())

    def save(self):
        try:
            self.st["last_query"] = self.var_q.get()
            self.st["top"] = int(self.var_top.get())
        except Exception:
            pass
        U.save_settings("skills_index", self.st, tool_dir=HERE)

    def refresh_status(self):
        try:
            c = eng.ro(eng.DB)
            meta = dict(c.execute("SELECT k,v FROM meta").fetchall())
            nch = c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
            c.close()
            self.status.set("индекс: %s · чанков %d · модель %s"
                            % (meta.get("version", "нет"), nch, meta.get("model", "—")))
        except Exception:
            self.status.set("индекса нет — нажми ПЕРЕСОБРАТЬ")

    def do_search(self, _=None):
        q = self.var_q.get().strip()
        if not q:
            return
        self.save()
        self.status.set("ищу по смыслу…")
        self.tree.delete(*self.tree.get_children())

        def work():
            qv = eng.embed(eng.settings().get("model") or "nomic-embed-text-v2-moe:latest",
                           ["search_query: " + q])[0]
            c = eng.ro(eng.DB)
            rows = c.execute("SELECT path,vec FROM chunks").fetchall(); c.close()
            scored = sorted(((eng.cos(qv, eng.vunpack(v)), p) for p, v in rows), reverse=True)
            seen, out = set(), []
            for s_, p in scored:
                if p in seen:
                    continue
                seen.add(p); out.append((round(s_, 3), p))
                if len(out) >= int(self.var_top.get()):
                    break
            return out

        def done(res):
            for s_, p in res:
                self.tree.insert("", "end", values=("%.3f" % s_, p))
            self.set_summary(len(res), 0, 0, "запрос: %s" % q)
            self.status.set("найдено файлов: %d" % len(res))
            self.log("поиск «%s»: %d файлов" % (q, len(res)))

        U.run_in_thread(self.root, work, on_done=done, on_error=self._err, log=self.log)

    def do_build(self):
        self.status.set("перестройка индекса… (долго, Ollama)")
        self.log("перестройка индекса: полная (--full)")

        def work():
            a = Namespace(full=True, keep=None, model=None)
            return eng.cmd_build(a)

        def done(_):
            self.refresh_status()
            self.log("индекс пересобран")

        U.run_in_thread(self.root, work, on_done=done, on_error=self._err, log=self.log)

    def _err(self, e):
        self.status.set("ошибка: %s" % e)
        self.log("ошибка: %s" % e)

    def open_path(self, _=None):
        sel = self.tree.selection()
        if not sel:
            return
        p = self.tree.item(sel[0], "values")[1]
        try:
            import os
            os.startfile(str(Path(p).parent))
        except Exception as e:
            self.log("не открыть: %s" % e)


if __name__ == "__main__":
    App().root.mainloop()
