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

# --- V94: «Карта» (drill-down + мышь) + «Роза» (вкладка нижнего окна) --------
for needle in ("def _map_show", "def _squarify", "def _heat_color",
               "nb.add(tab_map", "_map_click", "def _map_open", "btn_map_back", "mp_folder",
               "lnb.add(lroz", "def _roza_show", "def _roza_draw", "def _cv_wheel_smart",
               "def _map_press", "def _roza_release"):
    assert needle in src, "нет фрагмента V94: %s" % needle
assert "str(tab_map)" in src, "on_tab не показывает карту при входе на вкладку"
assert "str(lroz)" in src, "_bottom_render не знает про вкладку «Роза»"
assert "_draw_tail" not in src, "остался временный заглушечный метод _draw_tail"
assert "Солнце" not in src, "осталось старое имя «Солнце»"
assert "SunburstWindow" not in src, "класс SunburstWindow остался — «Роза» теперь вкладка (V94)"
assert "_sunburst_open" not in src, "остался обработчик кнопки «Роза» (V94: кнопки больше нет)"
assert "УРОВЕНЬ ПАПОК" in src and "УРОВЕНЬ МОДЕЛЕЙ" in src, "нет drill-down уровней карты (V93)"
assert "_place_center" in src, "нет центрирования окна обновления (V93)"
assert "canvasx(ev.x)" in src, "клики без canvasx/canvasy сломаются при зуме/пане (V94)"
print("карта+роза: drill-down, мышь (зум/пан/клик), «Роза» — вкладка низа — на месте")

# --- V95/V96: «Река времени» — таймлайн правок журнала -----------------------
for needle in ("nb.add(tab_river", "def _river_show", "def _river_data",
               "def _river_release", "river_canvas", "create_polygon",
               "rv_step", "rv_back", "rv_new", "kind IN"):
    assert needle in src, "нет фрагмента V95/V96: %s" % needle
assert "str(tab_river)" in src, "on_tab не показывает «Реку» при входе на вкладку"
assert "__prc__" not in src, "«прочие» вернулись в стек — доминируют над топом (V96)"
assert "rv_months" not in src, "остался спинбокс «месяцев» — нужен авто-шаг (V96)"
print("река: авто-шаг (день/неделя/месяц), только modify, топ-N потоков, клик — на месте")

# --- V97: стартовые вкладки и шаг «неделя» -----------------------------------
for needle in ("rv_step.set(\"неделя\")", "nb.select(tab_river)", "lnb.select(lgr)"):
    assert needle in src, "нет фрагмента V97: %s" % needle
assert "nb.select(tabs[0])" not in src, "selfcheck всё ещё сбрасывает вкладку на первую (V97)"
print("старт: сверху «Река» (шаг неделя), снизу «Граф» — на месте")

# --- V98: стартовый «Граф» = рекордсмен недели из «Реки» ---------------------
for needle in ("def _startup_top_model", "root.after(300, _startup_top_model)"):
    assert needle in src, "нет фрагмента V98: %s" % needle
_st = src.split("def _startup_top_model")[1].split("\n    def ")[0]
assert "rv_streams" in _st, "стартовый граф не берёт рекордсмена недели из «Реки»"
assert "ORDER BY c DESC" in _st, "нет фолбэка на крупнейшую сборку"
print("старт: граф рекордсмена недели (фолбэк — крупнейшая сборка) — на месте")

# --- V99: папка бэкапа Purge настраивается в «⚙ НАСТРОЙКИ» ------------------
import plm_paths_window
src2 = inspect.getsource(plm_paths_window)
for needle in ("purge_backup_dir", "e_purge_dir"):
    assert needle in src2, "нет фрагмента V99 (окно путей): %s" % needle
assert "purge_backup_dir" in src, "purge_run не читает настройку purge_backup_dir"
assert "eng.purge_execute(folder, keep, bdir" in src, "purge_execute не получает папку владельца"
import plm_settings
assert "purge_backup_dir" in plm_settings.DEFAULT_SETTINGS, "нет ключа purge_backup_dir в DEFAULT_SETTINGS"
print("purge: папка бэкапа настраивается («⚙ НАСТРОЙКИ») и передаётся в движок — на месте")

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
    root.destroy()
    print("GenealogyWindow: Tk-проба OK (5 секций, повтор = поднять)")
except ImportError:
    print("tkinter недоступен — Tk-проба пропущена (логика класса проверена выше)")

# --- V140: ОТВЕТСТВЕННАЯ ПРОВЕРКА — ЦЕЛОСТНОСТЬ ПОСТАВКИ --------------------
# Повод (живая авария 28.10.2026): модули plm_queries/plm_links/plm_build_links были
# вынесены из engine.py, но НЕ попали в CODE_FILES -> version.json их не содержал.
# На шаре Z: код оказался V140, а манифест V134: пользователь получил бы новый
# engine.py БЕЗ plm_queries.py -> ImportError. Этот блок ловит такой разрыв.
import json
import make_version_json as MVJ

_here = os.path.dirname(os.path.abspath(__file__))
_manifest_path = os.path.join(_here, "version.json")
assert os.path.isfile(_manifest_path), "version.json отсутствует — манифест не собран"
with open(_manifest_path, encoding="utf-8") as f:
    man = json.load(f)

# 1) версия манифеста обязана совпадать с APP_VERSION (иначе шара «не видит» обновлений)
import plm_reader as PR
assert man.get("version") == PR.APP_VERSION, \
    "манифест %s != APP_VERSION %s — шара не увидит обновление" % (man.get("version"), PR.APP_VERSION)

# 2) все файлы поставки обязаны ЛЕЖАТЬ НА ДИСКЕ (CODE_FILES — источник истины)
_missing = [n for n in MVJ.CODE_FILES if not os.path.isfile(os.path.join(_here, n))]
assert not _missing, "файлы поставки отсутствуют на диске: %s" % ", ".join(_missing)

# 3) манифест обязан содержать РОВНО файлы поставки (ни больше, ни меньше)
_in_man = set(man.get("files") or {})
_in_code = set(n for n in MVJ.CODE_FILES if os.path.isfile(os.path.join(_here, n)))
assert _in_man == _in_code, \
    "манифест расходится с поставкой: нет в манифесте=%s, лишние=%s" \
    % (sorted(_in_code - _in_man), sorted(_in_man - _in_code))

# 4) хеши обязаны совпадать с содержимым (иначе обновление подменит файл молча)
_bad = [n for n in sorted(_in_code) if MVJ.sha256(os.path.join(_here, n)).lower() != str(man["files"][n]).lower()]
assert not _bad, "SHA256 не совпал (манифест устарел — пересобери make_version_json): %s" % ", ".join(_bad)
print("поставка: манифест %s (%d файлов), версия и ВСЕ SHA256 совпадают — OK"
      % (man.get("version"), len(_in_code)))

# 5) модули, которые engine.py импортирует, обязаны входить в поставку
#    (иначе приезд нового engine.py ломает инструмент на импорте)
_imports = ("plm_queries", "plm_links", "plm_build_links")
_miss_mod = [m for m in _imports
             if m + ".py" not in _in_code and ("import " + m) in inspect.getsource(engine)]
assert not _miss_mod, "engine импортирует, но не в поставке: %s" % ", ".join(_miss_mod)
print("импорты engine: %d модулей из поставки — OK" % len(_imports))

# --- СЕТ НА ПРОВЕРКУ (STRATEGY_PLM §2.5, GRABLI §106) -----------------------
# Закон владельца: «пробуй не на всей базе 40К, а на нескольких файлах».
# Сет мерит БОЕВЫМ путём (engine.scan_item) на эталонных файлах. Файлы только читаются,
# база не открывается, на шару Z: ничего не пишется. Если склада нет (нет шары) — сет
# ПРОПУСКАЕТСЯ с явной строкой, а не молча (молчание = ложное «зелено»).
try:
    import _test_set as _SET
    _set_ok = not _SET.run(negative=False)
except Exception as _ex_set:                    # noqa: BLE001
    _set_ok = False
    print("сет: НЕ ЗАПУСТИЛСЯ: %r" % (_ex_set,))
assert _set_ok, "СЕТ НА ПРОВЕРКУ КРАСНЫЙ — см. вывод выше (STRATEGY_PLM §2.5)"

print("SMOKE OK")
