# -*- coding: utf-8 -*-
"""V87 smoke: GenealogyWindow + граф — проверка без участия человека."""
import os
import sys

if hasattr(sys.stdout, "reconfigure"):          # консоль cp1251 не должна ронять печать «▲»
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import engine
import plm_toolwin

assert hasattr(plm_toolwin, "GenealogyWindow"), "GenealogyWindow отсутствует"
GW = plm_toolwin.GenealogyWindow
assert hasattr(GW, "open") and hasattr(GW, "_sec_up") and hasattr(GW, "_sec_hist")

# движок живой: известные изделия владельца (богатая родословная), иначе — первое из derived, иначе — крупное
con = engine.connect()
model = ""
for cand in ("АЛ116-2-1_323927", "ЧСЗ-Л_801_04_75-401-10"):
    n = con.execute("SELECT COUNT(*) FROM snapshots WHERE model=?", (cand,)).fetchone()[0]
    if n:
        model = cand
        break
if not model:
    row = con.execute(
        "SELECT child FROM derived WHERE child GLOB '[A-Za-zА-Яа-я]*' AND base != '' "
        "ORDER BY child LIMIT 1").fetchone()
    if not row:
        row = con.execute(
            "SELECT model FROM snapshots WHERE model GLOB '[A-Za-zА-Яа-я]*' "
            "ORDER BY model LIMIT 1").fetchone()
    model = row[0] if row else ""
con.close()
assert model, "база пуста — модели для пробы нет"
print("модель пробы:", model)

# --- данные GenealogyWindow (без Tk: только логика секций) ----------------
bases = engine.derived_bases(model)
der = engine.made_of_list(model, 500)
kids = engine.plm_children(model)
up = engine.plm_up_data(model, 8)
print("происхождение: %d · производных: %d · состав: %d · входимость (ключей): %d"
      % (len(bases), len(der), len(kids), len(up)))

# --- данные графа ----------------------------------------------------------
# _graph_data/_graph_layout живут внутри run_gui (замыкания) — проверяем через интроспекцию исходника
import inspect
src = inspect.getsource(plm_toolwin)
for needle in ("def _graph_data", "def _graph_layout", "def _graph_show",
               "for a, b, kind, q in edges:", "#8aa0b5"):
    assert needle in src, "нет фрагмента: %s" % needle
assert "leg_items" not in src, "легенда графа вернулась — владелец заказал СТАРЫЙ вариант (V92)"
assert "8ac48a" not in src, "цветные рёбра вернулись — владелец заказал СТАРЫЙ вариант (V92)"
print("граф: СТАРЫЙ вариант (V85/V86) — рёбра #8aa0b5 единым цветом, без легенды — на месте")

# --- V90: кнопка «Перезапустить» в итоге обновления -------------------------
for needle in ("def _upd_done_dialog", "def _restart_app", "subprocess.Popen", "os._exit(0)"):
    assert needle in src, "нет фрагмента V90: %s" % needle
_upd = src.split("def _apply_update")[1].split("\n    def ")[0]
assert "_upd_done_dialog" in _upd, "_apply_update всё ещё зовёт messagebox вместо окна с «Перезапустить»"
print("обновление: окно итога с «Перезапустить» (spawn + os._exit) на месте")

# --- V91: «Карта» (treemap вверху) + «Роза» (sunburst-окно) ----------------
for needle in ("class SunburstWindow", "def _map_show", "def _squarify", "def _heat_color",
               "nb.add(tab_map", "text=\"Роза\"", "_map_click", "def _sunburst_open",
               "def _map_open", "btn_map_back", "mp_folder"):
    assert needle in src, "нет фрагмента V91: %s" % needle
assert "str(tab_map)" in src, "on_tab не показывает карту при входе на вкладку"
assert "_draw_tail" not in src, "остался временный заглушечный метод _draw_tail"
assert "Солнце" not in src, "осталось старое имя «Солнце» — окно переименовано в «Роза» (V92)"
assert "УРОВЕНЬ ПАПОК" in src and "УРОВЕНЬ МОДЕЛЕЙ" in src, "нет drill-down уровней карты (V93)"
assert "_place_center" in src, "нет центрирования окна обновления (V93)"
print("карта+роза: drill-down (папки/модели), кнопка назад, центры окон — на месте")

# --- V88: «Обзор» живёт в ВЕРХНЕМ ноутбуке (nb), из нижнего убран ----------------
assert "nb.add(lov" in src, "вкладка «Обзор» не добавлена в ВЕРХНИЙ ноутбук"
assert "lnb.add(lov" not in src, "вкладка «Обзор» всё ещё в нижнем ноутбуке"
assert "if nb.select() == str(lov)" in src, "on_tab не показывает обзор при входе на вкладку"
_dbl = src.split("def _ov_dbl")[1].split("\n    def ")[0]
assert "_bottom_show(m, pick=True)" in _dbl, "_ov_dbl не приравнен к выбору сверху"
assert "_goto_model" not in _dbl, "_ov_dbl всё ещё зовёт старый переход"
# dispatch нижнего окна больше не знает про обзор
_render = src.split("def _bottom_render")[1].split("def _bottom_show")[0]
assert "str(lov)" not in _render, "_bottom_render всё ещё рисует «Обзор»"
print("обзор: вкладка в nb, on_tab лениво показывает, двойной клик = pick, dispatch низа чист")

# --- GenealogyWindow: Tk headless-проба ------------------------------------
os.environ.setdefault("PLM_SELFCHECK", "0")
try:
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    w = GW(root, model)
    # секции обязаны были построиться
    secs = w.tv.get_children(w.tv.get_children()[0])
    assert len(secs) == 5, "секций %d, ожидалось 5" % len(secs)
    # раскрываем каждую секцию вручную (событие <<TreeviewOpen>> эмулируем вызовом)
    for s in secs:
        w.tv.item(s, open=True)
        w.tv.focus(s)                        # фокус КЛАВИАТУРЫ на узле (его читает _on_open)
        w.tv.selection_set(s)
        w._on_open()
        kids2 = w.tv.get_children(s)
        assert kids2, "секция %s пуста" % w.tv.item(s, "text")
        assert w.tv.item(kids2[0], "text") != "загрузка…", "секция %s не догрузилась" % w.tv.item(s, "text")
        print("  секция OK:", w.tv.item(s, "text"))
    # повторный вызов поднимает ТО ЖЕ окно (не плодит копий)
    w2 = GW.open(root, model)
    assert w2 is None or w2.win is w.win, "повторное открытие создало копию окна"
    w._close()
    # --- V91: SunburstWindow — Tk-проба (дуги рисуются без показа окна) -------
    SW = plm_toolwin.SunburstWindow
    sw = SW(root, model)
    items = sw._cv.find_all()
    assert items, "роза ничего не нарисовала"
    n_arcs = len([i for i in items if "arc" in sw._cv.gettags(i)])
    sw._close()
    assert SW._inst is None, "_inst не очистился после закрытия"
    print("SunburstWindow: Tk-проба OK (объектов %d, дуг %d, закрытие чистит _inst)"
          % (len(items), n_arcs))
    root.destroy()
    print("GenealogyWindow: Tk-проба OK (5 секций, повтор = поднять)")
except ImportError:
    print("tkinter недоступен — Tk-проба пропущена (логика класса проверена выше)")

print("SMOKE OK")
