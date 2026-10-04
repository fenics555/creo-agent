# -*- coding: utf-8 -*-
r"""probe_tk - ПРОБА: живой ли tkinter в этой среде (04.10.2026).

WHY: окно gui.py завершается без следа и без traceback. Проверяем по шагам:
импорт tkinter, создание корня, создание окна. Пишем в файл каждый шаг.
"""
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "postregen_clean" / "probe_tk_out.txt"
lines = []


def main():
    lines.append("python: %s" % sys.version)
    try:
        import tkinter as tk
        lines.append("импорт tkinter: ОК")
    except Exception as e:
        lines.append("импорт tkinter: ОШИБКА %s" % e)
        OUT.write_text("\n".join(lines), encoding="utf-8")
        return 2
    try:
        r = tk.Tk()
        lines.append("создание Tk(): ОК")
        r.update()
        r.title("ПРОБА TK")
        nb = ttk_probe(r)
        lines.append("виджет на окне: ОК")
        r.after(1500, r.destroy)
        r.mainloop()
        lines.append("mainloop завершён")
    except Exception as e:
        import traceback
        lines.append("ОШИБКА Tk: %s\n%s" % (e, traceback.format_exc()))
    OUT.write_text("\n".join(lines), encoding="utf-8")
    return 0


def ttk_probe(r):
    from tkinter import ttk
    box = ttk.Treeview(r, columns=("a",), show="headings", height=3)
    box.heading("a", text="Колонка")
    box.insert("", "end", values=("значение",))
    box.pack()
    lbl = r.Label(text="Плашка", bg="#f4f4f2")
    lbl.pack()
    return box


if __name__ == "__main__":
    sys.exit(main())