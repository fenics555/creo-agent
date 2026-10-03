# -*- coding: utf-8 -*-
"""ui_common.py — ОБЩИЙ КАРКАС ОКОН АГЕНТА (волна 1, этапы 1.5 и 8).

ЗАЧЕМ: 15 окон агента писались каждое своё. Дизайн выведен из разбора 9 окон B&W
(`D:\\AI\\repo\\B&W\\17_ДИЗАЙН_ОКОН_И_НАСТРОЕК_B&W.md`, раздел 8) и держится тут ОДИН раз.

ШЕСТЬ ДИЗАЙН-КОНСТАНТ (цитата источника в скобках):
 1. ТАБЛИЦА настроек `Option | Value | Status | Description`, где Status — зелёная
    точка = изменено относительно умолчания, описание В ТОЙ ЖЕ строке (§4 B&W);
 2. КНОПКИ `По умолчанию` / `Отменить изменения` / `Применить` (§4);
 3. ВКЛАДКИ по смыслу, сложное — за «Дополнительно» (§4, §5);
 4. СТАТУС иконкой в дереве + сводка числами + ПРОЦЕНТ соответствия (§6);
 5. ДВЕ главные кнопки действия; результат СЛЕВА, настройки СПРАВА (§8 п.1, п.8);
 6. ПРАВИЛА — и текст, и форма (§3, §9).

ЗАКОН ТРЁХ РУК: каркас ничего не знает про предмет инструмента. Он даёт форму и
кнопки; настройки каждого окна живут файлом в `agent\\data\\<имя>_settings.json`
(манифест п.19) и переживают перезапуск окна.

Пример: config_audit\\gui.py, dup_scan\\gui.py (волна 1); остальные — по очереди.
"""
import io
import json
import os
import queue
import sys
import threading
import time
import traceback
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# --- ДИЗАЙН-КОНСТАНТЫ (меняем тут, а не в каждом окне) ------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"
LOG_DIR = Path(r"D:\AI\log\win_check")

BG = "#f4f4f2"                 # фон окна
FG = "#1c1c1c"                 # основной текст
MUTED = "#5a5a5a"              # подписи и пояснения
ACCENT = "#1f6fb2"             # главные кнопки
WARN = "#b8860b"               # «изменено», но применено не было
OK_C = "#2e7d32"               # зелёная точка «изменено» (B&W: зелёная = изменён)
ERR_C = "#c62828"              # красный статус
ACCENTS = {"cyan": ACCENT, "green": OK_C, "red": ERR_C}

# Иконки статуса в дереве (§6 B&W)
ICON_OK = "✅"      # соответствует
ICON_ERR = "❌"     # нарушение
ICON_WARN = "⚠️"   # предупреждение
ICON_SKIP = "⊘"    # пропущено
ICON_MAP = {"ok": ICON_OK, "fail": ICON_ERR, "warn": ICON_WARN,
            "error": ICON_ERR, "skip": ICON_SKIP, "pass": ICON_OK}
DOT_CHANGED = "●"   # зелёная точка колонки Status = отличается от умолчания
DOT_SAME = "○"


def settings_path(name):
    """Путь настроек окна: agent\\data\\<имя>_settings.json (манифест п.19)."""
    return DATA_DIR / ("%s_settings.json" % name)


def load_settings(name, defaults=None):
    """Читает настройки окна; при ошибке берёт умолчания и говорит почему."""
    d = dict(defaults or {})
    p = settings_path(name)
    try:
        if p.exists():
            d.update(json.loads(p.read_text(encoding="utf-8")))
    except Exception as e:
        d["_error"] = "настройки не прочитаны (%s) — беру умолчания" % e
    return d


def save_settings(name, data):
    """Сохраняет настройки окна; возвращает путь или текст ошибки."""
    p = settings_path(name)
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        payload = {k: v for k, v in data.items() if not k.startswith("_")}
        p.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        return str(p)
    except Exception as e:
        return "ошибка: %s" % e
# --- КАРКАС ОКНА -------------------------------------------------------------
def make_root(title, size="1020x620", minsize=(900, 560), tool_dir=None):
    """Окно с размерами, минимумом и общим фоном. Возвращает root."""
    r = tk.Tk()
    r.title(title)
    r.geometry(size)
    r.minsize(*minsize)
    r.configure(bg=BG)
    s = ttk.Style()
    try:
        s.theme_use("vista")
    except tk.TclError:
        pass
    s.configure("Treeview", rowheight=22)
    return r


def head(root, title, subtitle=""):
    """Шапка окна: название и пояснение в одну строку (мелкий серый текст)."""
    box = tk.Frame(root, bg=BG)
    box.pack(fill="x", padx=10, pady=(10, 0))
    tk.Label(box, text=title, bg=BG, fg=FG,
             font=("Segoe UI", 12, "bold")).pack(anchor="w")
    if subtitle:
        tk.Label(box, text=subtitle, bg=BG, fg=MUTED,
                 font=("Segoe UI", 8), wraplength=960, justify="left").pack(anchor="w")
    return box


def split_result_left(root, right_width=430):
    """КОНСТАНТА 5: результат СЛЕВА, настройки СПРАВА. Возвращает (левая, правая)."""
    paned = tk.PanedWindow(root, orient="horizontal", bg=BG)
    paned.pack(fill="both", expand=True, padx=10, pady=8)
    left = tk.Frame(paned, bg=BG)
    right = tk.Frame(paned, bg=BG, width=right_width)
    paned.add(left, stretch="always")
    paned.add(right, stretch="never")
    return left, right


def tabs(parent, titles):
    """КОНСТАНТА 3: вкладки по смыслу; сложное — последней, с подписью «Дополнительно»."""
    nb = ttk.Notebook(parent)
    nb.pack(fill="both", expand=True, padx=4, pady=4)
    pages = []
    for i, t in enumerate(titles):
        name = t if (t or "").strip() else "Дополнительно"
        f = tk.Frame(nb, bg=BG)
        nb.add(f, text=name)
        pages.append(f)
    return nb, pages


def log_view(parent, height=8, title="ЖУРНАЛ"):
    """Панель журнала внизу окна. Возвращает виджет и функцию log(msg).

    ЖИВАЯ НАХОДКА 03.10.2026 (проверка дизайна окон): заголовок рамки шёл БЕЗ пробелов
    (`text="ЖУРНАЛ"`), а канон дома — «заголовок секции в ПРОБЕЛАХ» (` НАСТРОЙКИ `).
    Это расходилось во всех 8 окнах волны 1 сразу, потому что они зовут каркас."""
    box = tk.LabelFrame(parent, text=" %s " % (title or "ЖУРНАЛ").strip(), bg=BG,
                        padx=6, pady=4)
    box.pack(fill="both", side="bottom", padx=8, pady=6)
    txt = tk.Text(box, height=height, bg="#101418", fg="#d8e2e8", wrap="word",
                  font=("Consolas", 9), relief="flat")
    sb = ttk.Scrollbar(box, command=txt.yview)
    txt.configure(yscrollcommand=sb.set)
    txt.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")

    def log(msg=""):
        txt.insert("end", str(msg) + "\n")
        txt.see("end")

    return box, log


def statusbar(parent):
    """Строка статуса внизу окна. Возвращает (виджет, set_status)."""
    var = tk.StringVar(value="готово")
    bar = tk.Label(parent, textvariable=var, bg=BG, fg=MUTED, anchor="w",
                   font=("Segoe UI", 8))
    bar.pack(fill="x", side="bottom", padx=10, pady=(0, 6))
    return var


def readme_button(parent, readme_dir, log):
    """Кнопка «README» — в каждом окне дома (манифест: три руки, окно самостоятельно)."""
    def show():
        p = Path(readme_dir) / "README.md"
        try:
            text = p.read_text(encoding="utf-8")
        except Exception as e:
            return log("README не прочитан: %s" % e)
        log("=" * 90)
        for line in text.splitlines():
            log(line)
        log("=" * 90)
        log("конец README")
    b = tk.Button(parent, text="README", width=12, command=show, bg=BG, relief="flat",
                  fg=ACCENT, cursor="hand2")
    b.pack(side="right", padx=4)
    return b
# --- КОНСТАНТА 1: ТАБЛИЦА НАСТРОЕК --------------------------------------------
class SettingsTable:
    """Таблица настроек `Option | Value | Status | Description`.

    Status — точка: `●` зелёная = значение отличается от умолчания (B&W §4),
    `○` серая = совпадает. Значение правится двойным щелчком по ячейке Value.
    Кнопки КОНСТАНТЫ 2: «По умолчанию» / «Отменить изменения» / «Применить».

    spec: список словарей:
        {"option": "last_config", "value": "D:\\...\\config.pro",
         "desc": "какой файл проверяем", "default": "..." (необязательно)}
    """
    COLS = ("Опция", "Значение", "Статус", "Описание")

    def __init__(self, parent, spec, log=None, on_apply=None):
        self.spec = spec
        self.log = log or (lambda m: None)
        self.on_apply = on_apply
        self.vals = {s["option"]: str(s.get("value", "")) for s in spec}
        self.box = tk.LabelFrame(parent, text=" НАСТРОЙКИ ", bg=BG, padx=8, pady=6)
        self.box.pack(fill="both", expand=True, padx=4, pady=4)

        self.tree = ttk.Treeview(self.box, columns=("option", "value", "status", "desc"),
                                  show="headings", height=12)
        self.tree.heading("option", text=self.COLS[0])
        self.tree.heading("value", text=self.COLS[1])
        self.tree.heading("status", text=self.COLS[2])
        self.tree.heading("desc", text=self.COLS[3])
        self.tree.column("option", width=150, anchor="w", stretch=False)
        self.tree.column("value", width=230, anchor="w", stretch=True)
        self.tree.column("status", width=60, anchor="center", stretch=False)
        self.tree.column("desc", width=260, anchor="w", stretch=True)
        sb = ttk.Scrollbar(self.box, command=self.tree.yview)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.tree.tag_configure("changed", foreground=OK_C)

        btns = tk.Frame(self.box, bg=BG)
        btns.pack(fill="x", pady=(6, 0))
        tk.Button(btns, text="По умолчанию", width=16, command=self.set_defaults).pack(side="left", padx=2)
        tk.Button(btns, text="Отменить изменения", width=20, command=self.discard).pack(side="left", padx=2)
        tk.Button(btns, text="Применить", width=14, command=self.apply,
                  bg=ACCENT, fg="white").pack(side="left", padx=2)

        self._editor = None
        self.tree.bind("<Double-1>", self._edit)
        self.refresh()

    def defaults(self):
        return {s["option"]: str(s.get("default", s.get("value", ""))) for s in self.spec}

    def changed(self, opt):
        return self.vals.get(opt, "") != self.defaults().get(opt, "")

    def refresh(self):
        self.tree.delete(*self.tree.get_children())
        for s in self.spec:
            o = s["option"]
            ch = self.changed(o)
            self.tree.insert("", "end", iid=o,
                             values=(o, self.vals.get(o, ""), DOT_CHANGED if ch else DOT_SAME,
                                     s.get("desc", "")),
                             tags=("changed",) if ch else ())
        n = sum(1 for s in self.spec if self.changed(s["option"]))
        self.log("настроек: %d, изменено: %d" % (len(self.spec), n))

    def _edit(self, _ev):
        """Двойной щелчок по строке — правка значения ячейки (КОНСТАНТА 1)."""
        sel = self.tree.selection()
        if not sel:
            return None
        opt = sel[0]
        if not any(s["option"] == opt for s in self.spec):
            return None
        r = self.tree.bbox(opt, "value")
        if not r:
            return None
        self._editor = tk.Entry(self.tree, width=28, font=("Consolas", 9))
        self._editor.insert(0, self.vals.get(opt, ""))
        self._editor.select_range(0, "end")
        self._editor.place(x=r[0], y=r[1], width=r[2], height=r[3])
        self._editor.focus_set()
        self._editor.bind("<Return>", lambda e: self._commit(opt))
        self._editor.bind("<FocusOut>", lambda e: self._commit(opt))
        return self._editor

    def _commit(self, opt):
        if self._editor is None:
            return
        val = self._editor.get().strip()
        self._editor.destroy()
        self._editor = None
        if val != self.vals.get(opt):
            self.vals[opt] = val
            self.log("%s = %s" % (opt, val or "(пусто)"))
        self.refresh()

    def set_defaults(self):
        """КНОПКА «По умолчанию»: все значения = умолчания, ещё НЕ применено."""
        self.vals.update(self.defaults())
        self.refresh()
        self.log("возвращены умолчания; нажми «Применить», чтобы сохранить")

    def discard(self):
        """КНОПКА «Отменить изменения»: значения = сохранённые в настройках окна."""
        saved = getattr(self, "saved", None)
        self.vals = dict(saved) if saved else self.defaults()
        self.refresh()
        self.log("изменения отменены")

    def apply(self, save_fn=None):
        """КНОПКА «Применить»: отдаёт значения и (по возможности) сохраняет в файл."""
        self.saved = dict(self.vals)
        res = self.on_apply(dict(self.vals)) if self.on_apply else None
        if save_fn:
            out = save_fn(dict(self.vals))
            self.log("настройки сохранены: %s" % out if not str(out).startswith("ошибка")
                     else str(out))
        self.refresh()
        return res
# --- КОНСТАНТА 4: ДЕРЕВО РЕЗУЛЬТАТОВ + СВОДКА С ПРОЦЕНТОМ ---------------------
def result_tree(parent, columns, titles=None, width=None):
    """Дерево результатов слева: колонки задаёт окно. Иконка статуса — в колонке 0."""
    box = tk.Frame(parent, bg=BG)
    box.pack(fill="both", expand=True, padx=4, pady=4)
    tr = ttk.Treeview(box, columns=columns, show="headings", height=16)
    titles = titles or columns
    for i, (c, t) in enumerate(zip(columns, titles)):
        tr.heading(c, text=t)
        w = (width or [None])[i]
        tr.column(c, width=w or 120, anchor="w",
                  stretch=(w is None))
    sb = ttk.Scrollbar(box, command=tr.yview)
    tr.configure(yscrollcommand=sb.set)
    tr.pack(side="left", fill="both", expand=True)
    sb.pack(side="right", fill="y")
    tr.tag_configure("fail", foreground=ERR_C)
    tr.tag_configure("warn", foreground=WARN)
    tr.tag_configure("ok", foreground=OK_C)
    return tr


def summary(parent):
    """КОНСТАНТА 4: строка сводки числами + ПРОЦЕНТ соответствия с полосой.

    Сводка снизу слева; число процента — одно число, как в B&W §6."""
    box = tk.Frame(parent, bg=BG)
    box.pack(fill="x", padx=6, pady=4)
    var = tk.StringVar(value="проверок: 0 · успешно: 0 · с процентами: нет данных")
    tk.Label(box, textvariable=var, bg=BG, fg=FG, font=("Segoe UI", 9)).pack(anchor="w")
    bar = ttk.Progressbar(box, length=320, mode="determinate", maximum=100)
    bar.pack(anchor="w", pady=(2, 0))

    def set_summary(total, ok_, warn=0, label=""):
        pct = (100.0 * ok_ / total) if total else None
        var.set("проверено: %d · успешно: %d · предупреждений: %d%s%s" % (
            total, ok_, warn,
            " · соответствие: %d %%" % round(pct) if pct is not None else " · соответствие: н/д",
            (" · " + label) if label else ""))
        if pct is not None:
            bar["value"] = pct
        else:
            bar["value"] = 0
        return pct

    return var, set_summary


def actions(parent, primary=(("ПРОВЕРИТЬ", lambda: None),), secondary=()):
    """КОНСТАНТА 5: главные кнопки действия (цветные, крупные), прочие — мелкие.

    primary: пары (текст, команда) ИЛИ просто тексты (тогда команда подставляется позже).
    secondary: то же для второстепенных."""
    box = tk.Frame(parent, bg=BG)
    box.pack(fill="x", padx=6, pady=4)
    made = []

    def norm(items):
        out = []
        for it in items:
            out.append(it if isinstance(it, (tuple, list)) else (it, None))
        return out

    for txt, cmd in norm(primary):
        b = tk.Button(box, text=txt, width=20, command=cmd,
                      bg=ACCENT, fg="white", font=("Segoe UI", 9, "bold"))
        b.pack(side="left", padx=3)
        made.append(b)          # возвращаем САМИ кнопки, а не pack()
    for txt, cmd in norm(secondary):
        b = tk.Button(box, text=txt, width=16, command=cmd)
        b.pack(side="left", padx=3)
        made.append(b)
    return box, made


def run_in_thread(root, fn, on_done=None, on_error=None, log=None):
    """КОНСТАНТА 5/безопасность: тяжёлое — в потоке, UI трогает только главный.

    fn() — работа без Tk; on_done(res) — вывод в главном потоке через root.after(0, …)."""
    res_box = queue.Queue(1)

    def worker():
        try:
            res_box.put(("ok", fn()))
        except Exception:
            res_box.put(("err", traceback.format_exc()))

    th = threading.Thread(target=worker, daemon=True)
    th.start()

    def poll():
        try:
            state, payload = res_box.get_nowait()
        except queue.Empty:
            root.after(120, poll)
            return
        if state == "ok":
            if on_done:
                on_done(payload)
        else:
            if log:
                log("ОШИБКА:\n%s" % payload)
            if on_error:
                on_error(payload)
    root.after(120, poll)
    return th


def stop_button(parent, log=None):
    """Кнопка «Стоп» у тяжёлых прогонов; честно говорит, что прервать нельзя."""
    var = {"flag": False}

    def stop():
        var["flag"] = True
        if log:
            log("STOP запрошен: текущий шаг доработает, длинные циклы читают флаг.")
    b = tk.Button(parent, text="СТОП", width=10, command=stop, bg=BG, fg=ERR_C)
    b.pack(side="right", padx=4)
    return var, b
# --- КОНСТАНТА 6: ПРАВИЛА — И ТЕКСТ, И ФОРМА (B&W §3, §9) ---------------------
class RulesEditor:
    """Правило двустороннее: сверху ТЕКСТ (его читает движок), снизу ФОРМА (правит человек).
    Порядок правил важен → `Move UP` / `Move DOWN` (§3), как у B&W."""

    def __init__(self, parent, rules=None, log=None, on_apply=None):
        self.rules = list(rules or [])
        self._sel = 0
        self.log = log or (lambda m: None)
        self.on_apply = on_apply
        box = tk.LabelFrame(parent, text=" ПРАВИЛА — текст сверху, форма снизу ", bg=BG,
                            padx=8, pady=6)
        box.pack(fill="both", expand=True, padx=4, pady=4)

        self.text = tk.Text(box, height=9, font=("Consolas", 9), wrap="none", bg="#101418",
                            fg="#d8e2e8", insertbackground="#d8e2e8")
        self.text.pack(side="top", fill="both", expand=True)
        form = tk.Frame(box, bg=BG)
        form.pack(side="top", fill="x", pady=(6, 0))
        self.var_param = tk.StringVar(value=self.rules[0]["param"] if self.rules else "")
        self.var_op = tk.StringVar(value=self.rules[0]["op"] if self.rules else "CONTAINS")
        self.var_val = tk.StringVar(value=self.rules[0]["value"] if self.rules else "")
        ttk.Combobox(form, textvariable=self.var_param, width=18,
                     values=["MATERIAL", "PTC_MATERIAL_NAME", "MDL_NAME"],
                     state="normal").grid(row=0, column=0, padx=2, pady=2)
        ttk.Combobox(form, textvariable=self.var_op, width=12,
                     values=["CONTAINS", "==", "!="],
                     state="readonly").grid(row=0, column=1, padx=2)
        ttk.Entry(form, textvariable=self.var_val, width=16).grid(row=0, column=2, padx=2)

        btns = tk.Frame(box, bg=BG)
        btns.pack(side="top", fill="x", pady=(6, 0))
        for txt, cmd in (("Новое правило", self.add), ("Удалить", self.remove),
                         ("Move UP", lambda: self.move(-1)), ("Move DOWN", lambda: self.move(1)),
                         ("Обновить", self.update), ("Применить", self.apply)):
            tk.Button(btns, text=txt, width=14, command=cmd,
                      bg=ACCENT if txt == "Применить" else BG,
                      fg="white" if txt == "Применить" else FG).pack(side="left", padx=2)
        self.sync_text()

    def to_text(self):
        """Движок читает ТЕКСТ (IF … END_IF), форма — для человека."""
        out = []
        for r in self.rules:
            out.append('IF PARAM_STRING %s %s "%s"' % (r["param"], r["op"], r["value"]))
            out.append("%s" % (r.get("act") or "SPACING 10 ANGLE 45"))
            out.append("END_IF")
        return "\n".join(out)

    def sync_text(self):
        self.text.delete("1.0", "end")
        self.text.insert("1.0", self.to_text())

    def add(self):
        self.rules.append({"param": self.var_param.get() or "MATERIAL",
                           "op": self.var_op.get(), "value": self.var_val.get(),
                           "act": "SPACING 10 ANGLE 45"})
        self.sync_text()
        self.log("правило добавлено, всего %d" % len(self.rules))

    def remove(self):
        if self.rules:
            self.rules.pop()
            self._sel = 0
            self.sync_text()
            self.log("правило удалено, осталось %d" % len(self.rules))

    def move(self, d):
        """Порядок правил важен: -1 вверх, +1 вниз (B&W §3)."""
        i, j = self._sel, self._sel + d
        if 0 <= i < len(self.rules) and 0 <= j < len(self.rules):
            self.rules[i], self.rules[j] = self.rules[j], self.rules[i]
            self._sel = j
            self.sync_text()
            self.log("правило перемещено на позицию %d" % (j + 1))

    def update(self):
        if not (0 <= self._sel < len(self.rules)):
            return self.log("не выбрано правило для обновления")
        self.rules[self._sel].update({"param": self.var_param.get() or "MATERIAL",
                                      "op": self.var_op.get(), "value": self.var_val.get()})
        self.sync_text()
        self.log("правило %d обновлено" % (self._sel + 1))

    def apply(self):
        self.sync_text()
        return self.on_apply(list(self.rules)) if self.on_apply else list(self.rules)


def selftest():
    """Проверка каркаса БЕЗ окна Tk: константы и логика правил."""
    assert len(SettingsTable.COLS) == 4, "у таблицы настроек должно быть 4 колонки"
    assert ICON_OK and DOT_CHANGED, "нет иконок статуса"
    r = RulesEditor.__new__(RulesEditor)
    r.rules = [{"param": "MATERIAL", "op": "CONTAINS", "value": "plastic",
                "act": "SPACING 10 ANGLE 45"}]
    txt = r.to_text()
    assert "END_IF" in txt and "MATERIAL" in txt, "правило не выводится текстом"
    return {"cols": list(SettingsTable.COLS), "rule_text_lines": len(txt.splitlines()),
            "rule_text": txt}


if __name__ == "__main__":
    print("ui_common ОК: колонки %s" % (list(SettingsTable.COLS),))
    st = selftest()
    print("правило текстом (%d строк):\n%s" % (st["rule_text_lines"], st["rule_text"]))