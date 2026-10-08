# -*- coding: utf-8 -*-
"""Окно PLM Reader (вынесено из plm_reader.py распилом; см. СПЕКА_РАСПИЛА_PLM_READER.md).

Весь интерфейс: панели, вкладки, деревья, меню, буфер, самопроверка, обновление.
Вызов: plm_reader.main() -> from plm_toolwin import run_gui (ленивый импорт, без цикла).

ВНИМАНИЕ: это ОДНА большая функция run_gui() со ~110 ВЛОЖЕННЫМИ функциями, живущими в общих
локальных (root, tk, ttk, settings, виджеты, _ROWS, _last, cols, shown…). Правки — по якорю
`def <имя>`; рефакторить в класс/миксины — отдельная задача (спека §8).

КАРТА ВЛОЖЕННЫХ ФУНКЦИЙ (порядок = порядок в файле; ищи по `    def <имя>`):
* окно/панель/статус: _lwheel, _paths_text, show_paths, pull_paths, open_paths, limit_changed, _row,
  _auto_changed, stop_scan, _vgrid, _upd_status, _apply_update, check_updates_ui, show_facts,
  _copy_status, _status_menu, _wrap_data, _half_sash, _half_try
* Проводник (верх): _e_short, _expl_root_paths, _expl_data, _expl_node, _expl_file_row, _expl_more,
  _expl_fill, fill_explorer, _expl_dbl
* Дерево/таблица (верх): debounce, _short, _file_row, node_add, _vals9, _fill_node, _model_values,
  _kind, _resolve, node_add_model, on_open, _dbl_click, fill_tree_view, expand_all, row_uid, make_tree
* инструменты ряда: purge_folder, _text_window, purge_show, purge_run, _lout, say, cap, _sel_model,
  where_selected, tree_down, tree_up, changes_selected, open_detail, lt_apply, _fmt
* НИЖНЕЕ окно (вкладки): _prop_show, _live_vals, _branch_updown, _ltv_model, ltv_open, _plm_data_ref,
  live_auto, _prod_show (Родословная), _links_show + _fill_up + ltv2_open (Связи), _made_window,
  _text_tree_show (Текст), _hist_show (История), _bottom_render, _bottom_show (pick= — верхний выбор),
  _goto_model + _goto_node (двойной клик = перейти на деталь), _return_to_pick (кнопка «вернуться»),
  live_tree, expl_live, tree_live, on_tab
* таблица/сорт/база: sort_key, set_sort, redraw, rebuild_tree, show_readme, check_base, show_check,
  load_base, _active_stamp, refresh_from_db, watch_db, save_settings, save_ui, on_close
* окна истории/скан: split_list, choose_columns, hist_settings, show_history, show_folder_history,
  poll_scan, worker, go, export, _offer_archive_cleanup
* КОПИРОВАТЬ/ПКМ (в конце файла): _has_native, _foc, _clip_ev, _on_copy, _on_paste, _on_cut, _sel_all,
  _menu_pop, _bind_clip, _bind_clip_all, _clip_ctrl
"""
import os
import re
import json
import datetime
import time
import threading
import queue
import sys

from plm_reader import (
    APP_TITLE,
    COLS_WIDTH,
    DEFAULT_SETTINGS,
    PathsWindow,
    REPORTS_DIR,
    _WINS,
    _active_db_file,
    _vol_str,
    apply_db_paths,
    archive_dims,
    archive_history,
    copy_source_of,
    db_conn,
    db_facts,
    db_rows,
    db_search_rows,
    db_summary,
    db_total,
    dwg_models,
    exclude_list,
    history_folder,
    history_rows,
    history_rows_copy_aware,
    history_window,
    latest_path,
    load_settings_file,
    log_line,
    match_filter,
    norm_path,
    numeric_params,
    outline_mm,
    parse_dt,
    path_under,
    read_bytes,
    read_dims_all,
    read_history,
    real_value,
    roots_of,
    save_csv,
    save_settings_file,
    scan_roots,
    sections,
    tech_notes,
)


def run_gui():
    import tkinter as tk
    from tkinter import ttk, filedialog, messagebox

    settings = load_settings_file()                     # битый/чужой файл не роняет окно
    import engine as _eng_start                      # движок нужен ДО первого чтения базы
    _db_dir, _db_mirrors = apply_db_paths(settings, _eng_start)   # база может жить на другом диске
    if settings.get("db_dir") or settings.get("db_mirror"):
        log_line("база: папка %s · зеркал: %s"
                 % (_db_dir, ", ".join(_db_mirrors) if _db_mirrors else "нет"))
    _cols = settings.get("columns")                     # новые колонки дат — и для старых настроек
    if isinstance(_cols, list):
        _off = 0
        for _c in ("Создан", "Изменён"):
            if _c not in _cols:
                _i = (_cols.index("Дата") + 1 + _off) if "Дата" in _cols else len(_cols)
                _cols.insert(_i, _c)
                _off += 1

    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("1520x900")         # 07.10.2026: настройки СЛЕВА + основное поле пополам
    root.minsize(980, 620)            # панель слева + два окна видно и в небольшом окне

    # 07.10.2026: НАСТРОЙКИ И КНОПКИ — В ЛЕВОЙ КОЛОНКЕ (узкая колонка ПРОКРУЧИВАЕТСЯ,
    # поэтому настройки не «срываются» за край при коротком окне)
    lhost = ttk.Frame(root, width=330)
    lhost.pack_propagate(False)            # колонка держит свою ширину
    lcanv = tk.Canvas(lhost, width=312, bg="#f8f9fa", highlightthickness=0)
    lsb = ttk.Scrollbar(lhost, orient="vertical", command=lcanv.yview)
    lcanv.configure(yscrollcommand=lsb.set)
    lsb.pack(side="right", fill="y")
    lcanv.pack(side="left", fill="both", expand=True)

    def _lwheel(ev):
        try:
            lcanv.yview_scroll(int(-1 * (ev.delta / 120)), "units")
        except Exception:
            pass

    top = ttk.Frame(lcanv, padding=2)      # панель настроек живёт В КАНВЕ (прокрутка колесом)
    lcanv.create_window((0, 0), window=top, anchor="nw")
    top.bind("<Configure>", lambda e: lcanv.configure(scrollregion=lcanv.bbox("all")))
    for _lw in (lcanv, top):
        _lw.bind("<MouseWheel>", _lwheel)
    row1 = ttk.Frame(top)                  # группы 1 (СВЕРХУ ВНИЗ): ПАПКИ · СКАН · ПОКАЗ
    row1.pack(fill="x")
    row2 = ttk.Frame(top)                  # группы 2: Purge · СКАНИРОВАНИЕ · ИНСТРУМЕНТЫ
    row2.pack(fill="x")
    grp_paths = ttk.LabelFrame(row1, text=" ПАПКИ ", padding=8)
    grp_paths.pack(fill="x", pady=(0, 6))
    grp_scan = ttk.LabelFrame(row1, text=" СКАН ", padding=8)
    grp_scan.pack(fill="x", pady=(0, 6))
    grp_show = ttk.LabelFrame(row1, text=" ПОКАЗ ", padding=8)
    grp_show.pack(fill="x", pady=(0, 6))
    grp_purge = ttk.LabelFrame(row2, text=" Purge — старые версии в бэкап, удаления нет ", padding=8)
    grp_purge.pack(fill="x", pady=(0, 6))
    grp_do = ttk.LabelFrame(row2, text=" СКАНИРОВАНИЕ ", padding=8)
    grp_do.pack(fill="x", pady=(0, 6))
    grp_tools = ttk.LabelFrame(row2, text=" ИНСТРУМЕНТЫ ", padding=8)
    grp_tools.pack(fill="x", pady=(0, 6))
    spath = grp_paths                      # панель путей живёт в группе «ПАПКИ»
    _hidden = ttk.Frame(top)               # невидимый держатель (совместимость разметки)
    class _Field:
        """Поле-путь БЕЗ виджета: ввод путей живёт в окне «Пути и исключения…», тут только значение."""

        def __init__(self, value=""):
            self.v = value or ""

        def get(self):
            return self.v

        def delete(self, *_a):
            self.v = ""

        def insert(self, _i, val):
            self.v = str(val)

    _flds = settings.get("folders") or []
    e_folder = _Field(_flds[0] if len(_flds) > 0 else "")
    e_folder2 = _Field(_flds[1] if len(_flds) > 1 else "")

    def _paths_text(items, max_chars=64):
        """Все пути СЛИТНО через запятую; если длинно — обрезка с «…» (не больше 2 строк)."""
        if not items:
            return "—"
        joined = ", ".join(items)
        if len(joined) > max_chars:
            return joined[:max_chars - 1] + "…"
        return joined

    def show_paths():
        """Что настроено: папки скана и исключения — слитно через запятую, максимум в 2 строки."""
        flds = scan_roots(e_folder.get(), e_folder2.get(), settings.get("folders"))
        exc = exclude_list(settings.get("exclude"))
        lbl_p.config(text="Папок скана: %d. %s" % (len(flds), _paths_text(flds)))
        lbl_e.config(text="Исключено: %d. %s" % (len(exc), _paths_text(exc)))

    def pull_paths():
        """После окна «Пути и исключения…»: значения — в поля-держатели, подписи — на панель."""
        flds = settings.get("folders") or []
        e_folder.v = flds[0] if flds else ""
        e_folder2.v = flds[1] if len(flds) > 1 else ""
        show_paths()

    def open_paths():
        PathsWindow(root, settings, tk, ttk, filedialog, on_save=pull_paths)

    btn_paths = ttk.Button(spath, text="Пути и исключения…", command=open_paths, width=26)
    btn_paths.grid(row=0, column=0, sticky="w")
    lim = ttk.Frame(grp_show)
    lim.pack(fill="x")
    ttk.Label(lim, text="строк в таблице и в фильтре:").pack(side="left")
    sp_limit = ttk.Spinbox(lim, from_=1000, to=1000000, increment=5000, width=9)
    sp_limit.set(int(settings.get("show_limit") or 50000))
    sp_limit.pack(side="left", padx=4)
    ttk.Label(grp_show, text="(столько же строк отдаёт поиск по фильтру)", foreground="#666").pack(anchor="w")

    def limit_changed(*_):
        try:
            settings["show_limit"] = max(1000, min(1000000, int(sp_limit.get() or 50000)))
            save_settings()
        except Exception:
            pass

    sp_limit.bind("<FocusOut>", limit_changed)
    sp_limit.bind("<Return>", limit_changed)
    lbl_p = ttk.Label(spath, text="", foreground="#666", justify="left", wraplength=282)
    lbl_p.grid(row=1, column=0, sticky="w", pady=(4, 0))
    lbl_e = ttk.Label(spath, text="", foreground="#666", justify="left", wraplength=282)
    lbl_e.grid(row=2, column=0, sticky="w")
    show_paths()

    def _row(parent, label, width=5):
        """Строка «подпись + поле» внутри группы."""
        f = ttk.Frame(parent)
        f.pack(fill="x", pady=1)
        ttk.Label(f, text=label).pack(side="left")
        e = ttk.Entry(f, width=width)
        e.pack(side="left", padx=4)
        return e

    e_depth = _row(grp_scan, "Глубина папок (0 = все):", 5)
    e_depth.delete(0, "end")
    e_depth.insert(0, str(settings.get("depth", 0)))
    e_max = _row(grp_scan, "Пропускать файлы > МБ:", 5)
    e_max.delete(0, "end")
    e_max.insert(0, str(settings.get("max_size_mb", 24)))
    var_rec = tk.BooleanVar(value=settings.get("recurse", True))
    ttk.Checkbutton(grp_scan, text="с подпапками", variable=var_rec).pack(anchor="w")
    var_lat = tk.BooleanVar(value=settings.get("latest_only", True))
    ttk.Checkbutton(grp_scan, text="только последние версии", variable=var_lat).pack(anchor="w")

    e_keep = _row(grp_purge, "оставить версий:", 4)
    e_keep.delete(0, "end")
    e_keep.insert(0, str(settings.get("purge_keep", 2)))
    ttk.Label(grp_purge, text="ПЛАН — что уйдёт; «в бэкап» — перенести",
              foreground="#666").pack(anchor="w", pady=(2, 3))
    b_purge_plan = ttk.Button(grp_purge, text="Purge: ПЛАН", width=20,
                              command=lambda: purge_show())
    b_purge_plan.pack(anchor="w", pady=1)
    b_purge_run = ttk.Button(grp_purge, text="Purge: в бэкап…", width=20,
                             command=lambda: purge_run())
    b_purge_run.pack(anchor="w", pady=1)

    def _auto_changed():
        try:
            settings["auto_refresh"] = bool(var_auto.get())
            save_settings()
        except Exception:
            pass

    var_auto = tk.BooleanVar(value=settings.get("auto_refresh", True))
    ttk.Checkbutton(grp_show, text="автообновление", variable=var_auto,
                    command=_auto_changed).pack(anchor="w", pady=(4, 0))
    var_full = tk.BooleanVar(value=settings.get("full", False))
    ttk.Checkbutton(grp_show, text="перечитать всё", variable=var_full).pack(anchor="w")

    btn = ttk.Button(grp_do, text="Сканировать", width=18)
    btn.pack(anchor="w", pady=1)

    def stop_scan():
        root._plm_stop = True
        lbl.config(text="останавливаю…")

    b_stop = ttk.Button(grp_do, text="Стоп", command=stop_scan, state="disabled", width=18)
    b_stop.pack(anchor="w", pady=1)
    b_check = ttk.Button(grp_do, text="Актуально?", width=18, command=lambda: check_base())
    b_check.pack(anchor="w", pady=1)

    def _vgrid(parent, items, per_col=4, width=18):
        """Кнопки ВЕРТИКАЛЬНО: не больше per_col в столбик, дальше — следующий столбец правее.
        per_col=4 при 7 кнопках даёт РОВНО 2 столбца = 2 инструмента В СТРОКУ — влезает в узкую панель."""
        for i, (text, cmd) in enumerate(items):
            col, row = divmod(i, per_col)
            ttk.Button(parent, text=text, width=width, command=cmd).grid(
                row=row, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0), pady=1)

    _vgrid(grp_tools, [
        ("История выбранного", lambda: show_history()),
        ("История по папке", lambda: show_folder_history()),
        ("Столбцы и параметры…", lambda: choose_columns()),
        ("Выгрузить в CSV", lambda: export()),
        ("README", lambda: show_readme()),
        ("Проверить обновление", lambda: check_updates_ui(True)),
        ("Дополнительно", lambda: show_facts()),
    ], per_col=4)
    def _upd_status(text):
        try:
            root.after(0, lambda: lbl.config(text=text))
        except Exception:
            pass

    def _apply_update(files, remote):
        def work():
            _upd_status("обновление: качаю файлы…")
            res = eng.sync_by_manifest(files)
            if res.get("ok"):
                warns = res.get("warnings") or []
                note = ("\n\nПримечание: у части файлов SHA не совпал с манифестом (манифест "
                        "отстал от кода) — они всё равно установлены: %s. Это не ошибка."
                        % ", ".join(warns)) if warns else ""
                _upd_status("обновлено до %s — перезапустите программу" % remote)
                root.after(0, lambda: messagebox.showinfo(
                    "Обновление",
                    "Обновлено до %s.\nФайлов: %d, устаревших убрано: %d.%s\n\n"
                    "Перезапустите программу." % (remote, len(res.get("updated", [])),
                                                  len(res.get("obsolete", [])), note)))
            else:
                _upd_status("обновление не удалось: %s" % res.get("error"))
                root.after(0, lambda: messagebox.showwarning(
                    "Обновление", "Не удалось: %s" % res.get("error")))
        threading.Thread(target=work, daemon=True).start()

    def check_updates_ui(manual=False):
        def work():
            _upd_status("проверяю обновления…")
            r = eng.check_updates()
            if not r.get("ok"):
                _upd_status("проверка обновлений: %s" % r.get("error"))
                if manual:
                    root.after(0, lambda: messagebox.showwarning(
                        "Обновление", "Не удалось проверить: %s" % r.get("error")))
                return
            if r.get("available"):
                _upd_status("есть обновление: %s" % r.get("remote"))
                msg = ("Доступна версия %s (у вас %s).\n\n%s\n\nОбновить сейчас?"
                       % (r.get("remote"), r.get("local"), r.get("notes") or ""))
                def ask():
                    if messagebox.askyesno("Есть обновление", msg):
                        _apply_update(r.get("files") or {}, r.get("remote"))
                root.after(0, ask)
            else:
                _upd_status("обновлений нет (версия %s)" % r.get("local"))
                if manual:
                    root.after(0, lambda: messagebox.showinfo(
                        "Обновление", "У вас последняя версия: %s" % r.get("local")))
        threading.Thread(target=work, daemon=True).start()

    def show_facts():
        """Окно «Дополнительно»: интересные факты по активной базе (расчёт в фоне)."""
        win = tk.Toplevel(root)
        win.title("PLM Reader — дополнительно (интересные факты по базе)")
        win.geometry("660x470")
        win.transient(root)
        head = ttk.Label(win, text="считаю…", padding=8)
        head.pack(anchor="w")
        tv = ttk.Treeview(win, columns=("k", "v"), show="headings", height=16)
        tv.heading("k", text="Показатель")
        tv.heading("v", text="Значение")
        tv.column("k", width=210, anchor="w")
        tv.column("v", width=430, anchor="w")
        tv.pack(fill="both", expand=True, padx=8)
        warn = ttk.Label(win, text="", foreground="#a00", wraplength=630,
                         justify="left", padding=8)
        warn.pack(anchor="w")

        def work():
            lines, wrn = db_facts()

            def done():
                try:
                    tv.delete(*tv.get_children())
                    for k, v in lines:
                        tv.insert("", "end", values=(k, v))
                    head.config(text="Интересные факты по активной базе")
                    warn.config(text=wrn)
                except Exception:
                    pass
            root.after(0, done)

        threading.Thread(target=work, daemon=True).start()
        ttk.Button(win, text="Пересчитать",
                   command=lambda: threading.Thread(target=work, daemon=True).start()).pack(pady=6)
        ttk.Button(win, text="Закрыть", command=win.destroy).pack(pady=(0, 8))



    data = ttk.Frame(root, padding=6)
    data.pack(side="bottom", fill="x", padx=6, pady=(0, 4))    # полоса статуса — ВНИЗУ окна

    vpan = ttk.PanedWindow(root, orient="vertical")   # ВЕРХ (окно) / НИЗ (деревья) — разделитель тянется

    def _copy_status():
        """Скопировать нижнюю строку в буфер (удобно переслать ошибку целиком)."""
        try:
            txt = lbl.cget("text")
            root.clipboard_clear()
            root.clipboard_append(str(txt))
            lbl.config(text="✓ строку скопировано — вставь в чат/письмо (Ctrl+V)")
            root.after(1500, lambda: lbl.config(text=txt))
        except Exception:
            pass

    btn_copy = ttk.Button(data, text="Копировать", width=12, command=_copy_status)
    btn_copy.pack(side="right", padx=(6, 0))
    lbl = ttk.Label(data, text="готов", anchor="w", justify="left")
    lbl.pack(side="left", fill="x", expand=True)

    # НИЖНЯЯ ПОЛОСА (дерево производства) — прижата к низу окна, видна на ЛЮБОЙ вкладке
    lpane = ttk.Frame(vpan)
    # lpane добавляем в разделитель ПОСЛЕ nb (ниже) — иначе верх/низ поменяются местами

    def _status_menu(event):
        m = tk.Menu(root, tearoff=0)
        m.add_command(label="Копировать строку", command=_copy_status)
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    lbl.bind("<Button-3>", _status_menu)          # ПКМ по строке = меню «Копировать»

    def _wrap_data(event=None):
        try:
            lbl.config(wraplength=max(240, root.winfo_width() - 80))   # текст не пропадает в узком окне
        except Exception:
            pass

    root.bind("<Configure>", _wrap_data)

    nb = ttk.Notebook(vpan)
    vpan.add(nb, weight=1)                    # ВЕРХ: список изделий (Проводник/Дерево/Таблица)
    vpan.add(lpane, weight=1)                 # НИЗ: детали (4 вкладки) — поле делится ПОПОЛАМ
    lhost.pack(side="left", fill="y", padx=(6, 0), pady=6)     # 07.10.2026: настройки — СЛЕВА
    vpan.pack(side="left", fill="both", expand=True, padx=6, pady=(0, 6))

    def _half_sash():
        """Разделитель — ровно в половину. Ложь, пока окно ещё не разложено (иначе sash
        встаёт на минимум и получается «верх свёрнут, низ на всё окно»)."""
        try:
            h = vpan.winfo_height()
            if h < 200:
                return False
            vpan.sashpos(0, max(150, h // 2))
            return True
        except Exception:
            return False

    def _half_try(n=0):
        """07.10.2026: повторяем, пока у разделителя не появится настоящая высота."""
        if getattr(root, "_plm_sash_user", False):
            return
        if not _half_sash() and n < 15:
            root.after(150, lambda: _half_try(n + 1))

    vpan.bind("<ButtonRelease-1>", lambda e: setattr(root, "_plm_sash_user", True))
    root.after(200, _half_try)
    tab_table = ttk.Frame(nb)                 # Таблица — плоский вид данных базы (третья вкладка)
    tab_tree = ttk.Frame(nb)                  # Дерево — иерархия ТЕХ ЖЕ данных (папки → файлы) (вторая)
    nb.add(tab_tree, text=" Дерево ")
    nb.add(tab_table, text=" Таблица ")

    # --- ДЕРЕВО: фильтр по ВСЕЙ базе + иерархия папок (ленивая, из базы) ---
    import engine as eng

    # --- ПРОВОДНИК: папки склада иерархией (ленивая, из базы) — как в Проводнике Windows ---
    tab_expl = ttk.Frame(nb)
    nb.insert(0, tab_expl, text=" Проводник ")     # Проводник — ПЕРВАЯ вкладка
    ebar = ttk.Frame(tab_expl, padding=(6, 4))
    ebar.pack(fill="x")
    ttk.Button(ebar, text="Обновить", command=lambda: fill_explorer()).pack(side="left", padx=4)
    esum = ttk.Label(ebar, text="")
    esum.pack(side="left", padx=10)
    ebody = ttk.Frame(tab_expl)
    ebody.pack(fill="both", expand=True, padx=6, pady=(0, 6))
    ebody.rowconfigure(0, weight=1)
    ebody.columnconfigure(0, weight=1)
    ECOLS = ("Тип", "Файл", "Обозначение", "Наименование", "Материал", "Объём, мм³",
             "Ревизия", "Роль", "Путь")
    eview = ttk.Treeview(ebody, columns=ECOLS, show="tree headings", height=18)
    eview.heading("#0", text="папка / файл")
    eview.column("#0", width=300, anchor="w")
    for c in ECOLS:
        eview.heading(c, text=c)
        eview.column(c, width=COLS_WIDTH.get(c, 130), anchor="w")
    evs = ttk.Scrollbar(ebody, orient="vertical", command=eview.yview)
    ehs = ttk.Scrollbar(ebody, orient="horizontal", command=eview.xview)
    eview.configure(yscrollcommand=evs.set, xscrollcommand=ehs.set)
    eview.grid(row=0, column=0, sticky="nsew")
    evs.grid(row=0, column=1, sticky="ns")
    ehs.grid(row=1, column=0, sticky="ew")
    _EFOLD, _EFILE, _EDONE = {}, {}, set()

    def _e_short(p):
        return p if len(p) <= 90 else "…" + p[-88:]

    def _expl_root_paths():
        """Корни ПРОВОДНИКА: сначала папки окна (основная + Папка2), затем корни базы."""
        win = [r for r in roots_of(e_folder.get(), e_folder2.get()) if os.path.isdir(r)]
        if win:
            try:
                c = db_conn()
                have = set(r[0] for r in c.execute("SELECT path FROM folders"))
                c.close()
                known = [r for r in win if r in have]
                return known or win
            except Exception:
                return win
        try:
            c = db_conn()
            rows = [r[0] for r in c.execute(
                "SELECT path FROM folders WHERE parent NOT IN (SELECT path FROM folders) ORDER BY path")]
            c.close()
            if rows:
                return rows
        except Exception:
            pass
        try:
            import engine as _e
            return json.loads(_e.meta_get("roots") or "null") or []
        except Exception:
            return []

    def _expl_data(parent):
        """Подпапки (с числами) и файлы папки — ОДНИМ соединением (без COUNT на каждую подпапку)."""
        c = db_conn()
        try:
            subs = c.execute(
                "SELECT f.path,"
                " (SELECT COUNT(*) FROM folders g WHERE g.path LIKE f.path || '\\%'),"
                " (SELECT COUNT(*) FROM snapshots s WHERE s.path LIKE f.path || '\\%')"
                " FROM folders f WHERE f.parent=? ORDER BY f.path", (parent,)).fetchall()
            files = c.execute("SELECT path,designation,name FROM snapshots WHERE folder=? "
                              "ORDER BY path", (parent,)).fetchall()
        finally:
            c.close()
        return subs, files

    def _expl_node(parent, folder, subs_n=0, files_n=0):
        n = eview.insert(parent, "end",
                         text="%s  [%d папок, %d файлов]" % (os.path.basename(folder) or folder,
                                                              subs_n, files_n),
                         values=("папка", "", "", "", "", "", "", "", _e_short(folder)))
        _EFOLD[n] = folder
        eview.insert(n, "end", text="…")          # «плюсик»: дети читаются при раскрытии
        return n

    def _expl_file_row(node, p, desig, name):
        n = eview.insert(node, "end", text=os.path.basename(p), values=(
            "файл", os.path.basename(p), desig or "", name or "", "", "", "", "", _e_short(p)))
        _EFILE[n] = p
        return n

    def _expl_more(node, rest, subs):
        """Порциями по 150 — окно не замирает, строки появляются по мере чтения."""
        for p, desig, name in rest[:150]:
            _expl_file_row(node, p, desig, name)
        if len(rest) > 150:
            root.after(1, lambda: _expl_more(node, rest[150:], subs))
        else:
            for s, sc, fc in subs:
                _expl_node(node, s, sc, fc)
            _EDONE.add(node)

    def _expl_fill(node, res=None):
        """ЛЕНИВО: показали «читаю…» → фоном читаем → рисуем порциями. Повтор не перечитывает."""
        folder = _EFOLD.get(node)
        if folder is None:
            return
        if res is None:
            if node in _EDONE:
                return
            for ch in eview.get_children(node):
                eview.delete(ch)
            eview.insert(node, "end", text="… читаю")

            def work():
                try:
                    data = _expl_data(folder)
                except Exception:
                    data = ([], [])
                try:
                    root.after(0, lambda: _expl_fill(node, data))
                except Exception:
                    pass
            threading.Thread(target=work, daemon=True).start()
            return
        subs, files = res
        for ch in eview.get_children(node):
            try:
                if eview.item(ch, "text") == "… читаю":
                    eview.delete(ch)
            except Exception:
                pass
        _expl_more(node, files, subs)

    def fill_explorer():
        eview.delete(*eview.get_children())
        _EFOLD.clear()
        _EFILE.clear()
        _EDONE.clear()
        roots = _expl_root_paths()
        cnt = {}
        if roots:
            c = db_conn()
            try:
                cnt = dict((r[0], (r[1], r[2])) for r in c.execute(
                    "SELECT f.path,"
                    " (SELECT COUNT(*) FROM folders g WHERE g.path LIKE f.path || '\\%%'),"
                    " (SELECT COUNT(*) FROM snapshots s WHERE s.path LIKE f.path || '\\%%')"
                    " FROM folders f WHERE f.path IN (%s)" % ",".join("?" * len(roots)), roots))
            except Exception:
                cnt = {}
            finally:
                c.close()
        for r in roots:
            sc, fc = cnt.get(r, (0, 0))
            _expl_node("", r, sc, fc)
        esum.config(text="корней: %d — раскрывай папки (дети читаются при раскрытии)" % len(roots))

    def _expl_dbl(event=None):
        path = _EFILE.get(eview.focus())
        if path and os.path.isfile(path):
            history_window(root, tk, ttk, filedialog,
                           "История изменений — %s" % os.path.basename(path),
                           lambda: history_rows(path, hist_settings()),
                           settings=settings, save_settings=save_settings,
                           status=os.path.basename(path))

    eview.bind("<<TreeviewOpen>>", lambda ev: _expl_fill(eview.focus()))
    eview.bind("<Double-1>", _expl_dbl)
    fill_explorer()

    _deb = {"id": None}

    def debounce(fn, ms=450):
        """Простое решение от тормозов: запускать поиск через паузу после набора."""
        if _deb["id"]:
            try:
                root.after_cancel(_deb["id"])
            except Exception:
                pass
        _deb["id"] = root.after(ms, fn)

    TCOLS = ("Тип", "Файл", "Обозначение", "Наименование", "Материал", "Объём, мм³", "Ревизия", "Роль", "Путь")
    tflt = ttk.Frame(tab_tree, padding=(6, 4))
    tflt.pack(fill="x")
    ttk.Label(tflt, text="Фильтр по всей базе:").pack(side="left")
    e_tfilter = ttk.Entry(tflt, width=38)
    e_tfilter.pack(side="left", padx=4)
    e_tfilter.bind("<KeyRelease>", lambda ev: debounce(fill_tree_view))
    ttk.Button(tflt, text="Сбросить",
               command=lambda: (e_tfilter.delete(0, "end"), fill_tree_view())).pack(side="left", padx=6)

    tmode = tk.StringVar(value="plm")
    ttk.Radiobutton(tflt, text="Входимость (ПЛМ)", variable=tmode, value="plm",
                    command=lambda: fill_tree_view()).pack(side="left", padx=(10, 0))
    ttk.Radiobutton(tflt, text="Папки", variable=tmode, value="folders",
                    command=lambda: fill_tree_view()).pack(side="left", padx=(8, 0))

    tbar = ttk.Frame(tab_tree, padding=(6, 0))
    tbar.pack(fill="x")
    ttk.Button(tbar, text="СОСТАВ (вниз)", command=lambda: tree_down()).pack(side="left", padx=4)
    ttk.Button(tbar, text="ГДЕ ИСПОЛЬЗУЕТСЯ (вверх)",
               command=lambda: tree_up()).pack(side="left", padx=4)
    ttk.Button(tbar, text="ИЗМЕНЕНИЯ по изделию",
               command=lambda: changes_selected()).pack(side="left", padx=4)
    ttk.Button(tbar, text="РАЗВЕРНУТЬ ВСЁ", command=lambda: expand_all()).pack(side="left", padx=4)
    tsum = ttk.Label(tbar, text="")
    tsum.pack(side="left", padx=10)

    tbody = ttk.Frame(tab_tree)
    tbody.pack(fill="both", expand=True, padx=6, pady=(0, 6))
    tbody.rowconfigure(0, weight=1)
    tbody.columnconfigure(0, weight=1)
    tview = ttk.Treeview(tbody, columns=TCOLS, show="tree headings", height=16)
    tview.heading("#0", text="папка / узел")
    tview.column("#0", width=280, anchor="w")
    for c in TCOLS:
        tview.heading(c, text=c)
        tview.column(c, width=COLS_WIDTH.get(c, 130), anchor="w")
    tvs = ttk.Scrollbar(tbody, orient="vertical", command=tview.yview)
    ths = ttk.Scrollbar(tbody, orient="horizontal", command=tview.xview)
    tview.configure(yscrollcommand=tvs.set, xscrollcommand=ths.set)
    tview.grid(row=0, column=0, sticky="nsew")
    tvs.grid(row=0, column=1, sticky="ns")
    ths.grid(row=1, column=0, sticky="ew")
    _FOLDERS, _MODELS = {}, {}

    def _short(p):
        return p if len(p) <= 90 else "…" + p[-88:]

    def _file_row(parent, p, desig, name, material, volume, rev, role):
        return tview.insert(parent, "end", values=(
            "файл", os.path.basename(p), desig or "", name or "", material or "",
            ("%.0f" % volume) if volume else "", rev or "", role or "", _short(p)))

    def node_add(node, folder):
        subs, files = eng.folder_children(folder)
        for p, desig, name, material, volume, rev, role in files:
            _file_row(node, p, desig, name, material, volume, rev, role)
        for s in subs:
            a, b = eng.folder_files_count(s)
            n = tview.insert(node, "end", text="%s  [%d папок, %d файлов]"
                             % (os.path.basename(s) or s, a, b),
                             values=("папка", "", "", "", "", "", "", "", _short(s)))
            _FOLDERS[n] = s
            tview.insert(n, "end", text="загрузка…")      # «плюсик» для раскрытия

    def _vals9(m, i, qty=""):
        """Строка для дерева вкладки «Дерево» (9 колонок)."""
        role = (i[5] or "") if len(i) > 5 else ""
        kind = "оснастка" if role == "MFG" else ("изделие" if (i[6] or i[7]) else "деталь")
        return (kind, m, i[0] or "", i[1] or "", i[2] or "",
                ("%.0f" % i[3]) if (len(i) > 3 and i[3]) else "", i[4] or "", role, qty)

    def _fill_node(tree_widget, node, model, with_up=True):
        """ЕДИНЫЙ строитель ветки для обеих площадок.

        состав (вниз) · ◄ отливка/заготовка · модельная оснастка (MFG) · [входит в (все сборки)].
        Возвращает (заготовок, узлов вверх, детей состава).
        """
        reg = _MODELS if tree_widget is tview else _LTREE
        vals = _vals9 if tree_widget is tview else _live_vals
        down = eng.plm_down_data(model, 1)
        der = eng.derived_bases(model)
        mfg = eng.mfg_models(model)
        up = eng.plm_up_data(model, 8) if with_up else {}
        nodes = {model} | set(down) | set(up)
        for v in list(down.values()) + list(up.values()):
            nodes |= {x[0] for x in v}
        info = eng.models_info(list(nodes))

        def row(m, qty=""):
            return vals(m, info.get(m, ("", "", "", 0, "", "", 0, 0)), qty)

        for b, k in der:
            dn0 = tree_widget.insert(
                node, "end",
                text=("◄ %s: имя не найдено (в файле только внутренний код)" % _kind(k))
                     if not b else "◄ %s: %s" % (_kind(k), b),
                values=("заготовка/отливка", b or "—", "", "", "", "", "", "", ""))
            if b:
                reg[dn0] = b                          # V81: узел «заготовка/отливка» кликабелен
                for name, how in eng.mfg_models(b, 30):
                    on = tree_widget.insert(dn0, "end", text="оснастка: %s  (%s)" % (name, how),
                                            values=("оснастка", name, "", "", "", "", "", "", ""))
                    reg[on] = name                    # V81: оснастка под заготовкой кликабельна
        if mfg:
            mn = tree_widget.insert(node, "end", open=True, text="модельная оснастка (MFG):")
            for name, how in mfg[:60]:
                on = tree_widget.insert(mn, "end", text="%s  (%s)" % (name, how),
                                        values=("оснастка", name, "", "", "", "", "", "", ""))
                reg[on] = name                        # V81: MFG-узел кликабелен
        if with_up:
            un = tree_widget.insert(node, "end", open=True, text="входит в (все сборки):")
            if not up:
                tree_widget.insert(un, "end",
                                   text="— ни в одну сборку не входит (верхнее изделие или связей нет в базе)",
                                   values=("—", "", "", "", "", "", "", "", ""))
            else:
                stack = [(un, model, 1)]
                while stack:
                    pn, m, depth = stack.pop()
                    for p2, q in up.get(m, []):
                        nn = tree_widget.insert(pn, "end", text="%s  ↑ x%d" % (p2, q), values=row(p2, "x%d" % q))
                        reg[nn] = p2                  # V81: узел «входит в (все сборки)» кликабелен
                        if depth < 8:
                            stack.append((nn, p2, depth + 1))
        cn = tree_widget.insert(node, "end", open=True, text="состав:")
        kids = down.get(model) or eng.plm_children(model)
        if not kids:
            tree_widget.insert(cn, "end", text="— в базе нет состава для этого изделия",
                               values=("—", "", "", "", "", "", "", "", ""))
        else:
            for c, q in kids:
                n = tree_widget.insert(cn, "end", text="%s  x%d" % (c, q), values=row(c, "x%d" % q))
                reg[n] = c
                tree_widget.insert(n, "end", text="загрузка…")
        made = eng.derived_children(model)          # 07.10.2026: что СДЕЛАНО из неё (копии/производные)
        if made:
            md = tree_widget.insert(node, "end", open=bool(made),
                                    text="сделано из неё (копии/производные): %d" % len(made))
            for c, k in made[:60]:
                nn = tree_widget.insert(md, "end", text="%s  (%s)" % (c, _kind(k)), values=row(c))
                reg[nn] = c
                tree_widget.insert(nn, "end", text="загрузка…")
            if len(made) > 60:
                tree_widget.insert(md, "end", text="… ещё %d" % (len(made) - 60))
        return len(der), sum(len(v) for v in up.values()), len(kids)

    def _model_values(m):
        i = eng.models_info([m]).get(m, ("", "", "", 0, "", "", 0, 0))
        return _vals9(m, i)

    def _kind(k):
        return {"наследование": "заготовка", "производная": "отливка",
                "копия": "модель скопирована от",
                "hash": "заготовка/отливка"}.get(k, "заготовка/отливка")

    def _resolve(base, models):
        for cand in (base, base + ".prt", base + ".asm"):
            if cand in models:
                return cand
        return ""

    def node_add_model(node, model):
        """Вкладка «Дерево»: тот же строитель ветки, что и в нижнем окне (состав/отливки/оснастка/входит в)."""
        return _fill_node(tview, node, model, with_up=True)

    def on_open(event=None):
        node = tview.focus()
        folder = _FOLDERS.get(node)
        model = _MODELS.get(node)
        if not (folder or model):
            return
        kids = tview.get_children(node)
        if kids and tview.item(kids[0], "text") == "загрузка…":
            tview.delete(*kids)
            if folder:
                node_add(node, folder)
            else:
                node_add_model(node, model)

    tview.bind("<<TreeviewOpen>>", on_open)
    def _dbl_click():
        """Двойной щелчок по строке: изделие есть → вкладка «История файла»; нет (папка) → карточка."""
        m = _sel_model()
        if m:
            _last["model"] = m
            _last.pop("lroot", None)
            try:
                lnb.select(lhist)
            except Exception:
                pass
            _hist_show(m)
        else:
            open_detail()

    tview.bind("<Double-1>", lambda ev: _dbl_click())      # двойной щёлчок — история файлов изделия

    def fill_tree_view():
        text = e_tfilter.get().strip()
        tview.delete(*tview.get_children())
        _FOLDERS.clear()
        _MODELS.clear()
        if tmode.get() == "plm":                  # ДЕРЕВО ВХОДИМОСТИ (ПЛМ): состав вниз, входимость вверх
            if text:
                rows = eng.find_plm_models(text)
                for m, files, pars in rows:
                    v = list(_model_values(m))
                    v[8] = "файлов %d · входит в %d" % (files, pars)
                    tview.insert("", "end", text=m, values=v)
                tsum.config(text="моделей по фильтру: %d" % len(rows))
            else:
                tops = eng.plm_tops(6000)
                info = eng.models_info(tops)
                rn = tview.insert("", "end", open=True,
                                  text="ВСЁ ПРОИЗВОДСТВО — верхних сборок %d из %d"
                                       % (len(tops), eng.count_tops()))
                for m in tops:
                    v = info.get(m, ("", "", "", 0, "", "", 0, 0))
                    n = tview.insert(rn, "end", text=m, values=_vals9(m, v))
                    _MODELS[n] = m
                    tview.insert(n, "end", text="загрузка…")
                tsum.config(text="верхних сборок %d · раскрывай узлы или жми РАЗВЕРНУТЬ ВСЁ" % len(tops))
            return
        if text:
            rows = eng.search_files(text)
            for p, folder, desig, name, material, volume, rev, role in rows:
                _file_row("", p, desig, name, material, volume, rev, role)
            tsum.config(text="показано %d (фильтр по всем словам)" % len(rows))
        else:
            for r in scan_roots(e_folder.get(), e_folder2.get(), settings.get("folders")):
                a, b = eng.folder_files_count(r)
                n = tview.insert("", "end", text="%s  [%d папок, %d файлов]" % (r, a, b),
                                 values=("корень", "", "", "", "", "", "", "", ""))
                _FOLDERS[n] = r
                tview.insert(n, "end", text="загрузка…")
            s = eng.summary()
            tsum.config(text="в базе изделий %d (файлов с копиями версий %d) · изменений %d"
                        % (s.get("models", 0), s.get("snapshots", 0), s.get("changes", 0)))

    def expand_all():
        """ПОЛНОЕ дерево: в режиме Входимость строится одним заходом из базы (быстро)."""
        if e_tfilter.get().strip():
            tsum.config(text="сначала сбрось фильтр — тогда разверну полное дерево")
            return
        t0 = time.time()
        if tmode.get() == "plm":
            tops, children, info, derived = eng.plm_tree_data()
            tview.delete(*tview.get_children())
            _MODELS.clear()
            _FOLDERS.clear()
            cap, n = 60000, 0
            rn = tview.insert("", "end", open=True,
                              text="ВСЁ ПРОИЗВОДСТВО — верхних сборок %d" % len(tops))
            stack = [(rn, m, 1, frozenset((m,)), "") for m in reversed(tops)]
            while stack and n < cap:
                parent, model, depth, path, label = stack.pop()
                v = _vals9(model, info.get(model, ("", "", "", 0, "", "", 0, 0)))
                node = tview.insert(parent, "end", text=label + model, values=v, open=True)
                _MODELS[node] = model
                n += 1
                if depth >= 12:                     # предел глубины
                    continue
                for c, q in reversed(children.get(model, [])):
                    if n < cap and c not in path:   # защита от циклов по ветке
                        stack.append((node, c, depth + 1, path | {c}, ""))
                for b, k in reversed(derived.get(model, [])):    # заготовка/отливка
                    base = _resolve(b, info)
                    lbl = "◄ %s: " % _kind(k)
                    if not base:
                        tview.insert(node, "end", text=lbl + b + "  (нет в базе)",
                                     values=("заготовка", b, "", "", "", "", "", "", ""))
                    elif base not in path and n < cap:
                        stack.append((node, base, depth + 1, path | {base}, lbl))
            tsum.config(text="построено узлов: %d за %.1f с%s"
                        % (n, time.time() - t0, " (достигнут предел)" if stack else ""))
            return
        limit_nodes = 6000
        queue = list(tview.get_children(""))
        cnt = 0
        while queue and cnt < limit_nodes:
            node = queue.pop(0)
            if node in _FOLDERS:
                kids = tview.get_children(node)
                if kids and tview.item(kids[0], "text") == "загрузка…":
                    tview.delete(*kids)
                    node_add(node, _FOLDERS[node])
            tview.item(node, open=True)
            queue.extend(tview.get_children(node))
            cnt += 1
            if cnt % 40 == 0:
                tsum.config(text="разворачиваю папки… узлов %d" % cnt)
                try:
                    root.update_idletasks()
                except Exception:
                    pass
        tsum.config(text="развёрнуто узлов: %d за %.1f с%s"
                    % (cnt, time.time() - t0, " (предел)" if queue else ""))

    def purge_folder():
        f = norm_path(e_folder.get()) if e_folder.get().strip() else ""
        if not f:
            roots = eng.base_roots()
            f = roots[0] if roots else ""
        return f

    def _text_window(title, head, text, note=""):
        """Окно с текстом (план ПУРГЕ, итоги): видно с ЛЮБОЙ вкладки, можно скопировать целиком."""
        win = tk.Toplevel(root)
        win.title(title)
        win.geometry("920x520")
        ttk.Label(win, text=head, padding=(8, 6)).pack(anchor="w")
        box = ttk.Frame(win, padding=6)
        box.pack(fill="both", expand=True)
        t = tk.Text(box, wrap="none")
        sb = ttk.Scrollbar(box, orient="vertical", command=t.yview)
        t.configure(yscrollcommand=sb.set)
        t.pack(side="left", fill="both", expand=True)
        sb.pack(side="left", fill="y")
        t.insert("end", text)
        foot = ttk.Frame(win, padding=6)
        foot.pack(fill="x")
        ttk.Button(foot, text="Копировать всё",
                   command=lambda: (root.clipboard_clear(),
                                    root.clipboard_append(text))).pack(side="left")
        ttk.Button(foot, text="Закрыть", command=win.destroy).pack(side="left", padx=6)
        if note:
            ttk.Label(foot, text=note, foreground="#666").pack(side="left", padx=10)
        return win

    def purge_show():
        """ПЛАН чистки версий (файлы НЕ трогаются): отдельное окно + статус + отчёт в log\\reports."""
        folder = purge_folder()
        plan = eng.purge_plan(folder or None, int(e_keep.get() or 2))
        txt = eng.purge_plan_text(plan)
        head = ("Purge-план: лишних версий %d · освободится %.1f МБ · папка %s"
                % (plan["count"], plan["bytes"] / 1048576.0, folder or "вся база"))
        log_line("purge plan: %s — лишних %d, %.1f МБ"
                 % (folder or "вся база", plan["count"], plan["bytes"] / 1048576.0))
        rep = ""
        try:
            rep = os.path.join(REPORTS_DIR,
                               "PURGE_plan_%s.txt" % datetime.datetime.now().strftime("%Y-%m-%d_%H%M"))
            os.makedirs(REPORTS_DIR, exist_ok=True)
            with open(rep, "w", encoding="utf-8") as f:
                f.write(txt)
        except Exception:
            pass
        lbl.config(text=head + (" · отчёт: %s" % os.path.basename(rep) if rep else ""))
        _text_window("Purge: ПЛАН (файлы не трогаются)", head, txt,
                     "отчёт: %s" % (os.path.basename(rep) if rep else "не сохранён"))

    def purge_run():
        """Перенос лишних версий в БЭКАП — встроенным движком ПЛМ (внешний purge_versions не нужен)."""
        from tkinter import messagebox as mb
        folder = purge_folder()
        plan = eng.purge_plan(folder or None, int(e_keep.get() or 2))
        if not plan["count"]:
            lbl.config(text="Purge: чистить нечего — лишних версий нет")
            return
        if not folder or not os.path.isdir(folder):
            lbl.config(text="Purge: выбери существующую папку (кнопка «Пути и исключения…»)")
            return
        keep = int(e_keep.get() or 2)
        bdir = os.path.join(folder, "_purge_backup")
        if not mb.askyesno("Purge",
                           "Перенести в БЭКАП %d лишних версий (%.1f МБ)?\n%s\n\n"
                           "Удаления нет: файлы уедут в %s"
                           % (plan["count"], plan["bytes"] / 1048576.0, folder, bdir)):
            lbl.config(text="Purge: отменено")
            return

        def work():
            try:
                rep = eng.purge_execute(folder, keep, None, items=plan["candidates"])
                out = ("перенесено %d версий, освобождено %.1f МБ, за %.1f с\nбэкап: %s"
                       % (len(rep["перенесено"]), rep["освобождено_байт"] / 1048576.0,
                          rep["seconds"], bdir))
                if rep["пропущено_с_причиной"]:
                    out += "\nпропущено: " + "; ".join(rep["пропущено_с_причиной"][:20])
            except Exception as e:
                out = "ОШИБКА: %s" % e
            log_line("purge execute: %s -> %s" % (folder, out.split("\n")[0]))

            def done():
                head = "Purge: %s" % out.split("\n")[0]
                lbl.config(text=head)
                _text_window("Purge: перенос в бэкап — результат", head, out, bdir)

            try:
                root.after(0, done)
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()
        lbl.config(text="Purge: переношу лишние версии в бэкап…")

    def _lout(text):
        """Окно вывода кнопок вкладки «Дерево» — перенесено в «Дерево связей» (среднее окно убрано)."""
        try:
            lout.delete("1.0", "end")
            lout.insert("end", text)
            lnb.select(llinks)
        except Exception:
            pass

    def say(fn, *a):
        import contextlib
        import io
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                fn(*a)
        except Exception as e:
            buf.write("ОШИБКА: %s" % e)
        _lout(buf.getvalue().rstrip())

    def cap(fn, *a):
        """Захватить вывод CLI-функции движка в строку (для текстового дерева)."""
        import contextlib
        import io
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                fn(*a)
        except Exception as e:
            buf.write("ОШИБКА: %s: %s" % (type(e).__name__, e))
        return buf.getvalue().rstrip()

    def _sel_model():
        sel = tview.selection()
        if not sel:
            return ""
        vals = tview.item(sel[0], "values")
        return eng.stem(vals[1]) if len(vals) > 1 and vals[1] else ""

    def where_selected():
        m = _sel_model()
        say(eng.do_where, m) if m else _lout("выбери строку-файл в дереве")

    def tree_down():
        m = _sel_model()
        say(eng.do_tree, m, 4) if m else _lout("выбери изделие в дереве")

    def tree_up():
        m = _sel_model()
        say(eng.do_tree_up, m, 4) if m else _lout("выбери изделие в дереве")

    def changes_selected():
        m = _sel_model()
        say(eng.do_changes_model, m, 200) if m else _lout("выбери строку-файл в дереве")

    def open_detail(model=None):
        """Карточка изделия (двойной щёлчок): паспорт + файлы; сбоку — история/входимость/состав/заготовка."""
        model = (model or _sel_model()).strip()
        if not model:
            return
        title = "Изделие %s" % model
        w = _WINS.get(title)
        if w is not None and w.winfo_exists():
            w.deiconify()
            w.lift()
            w.focus_force()
            return
        win = tk.Toplevel(root)
        _WINS[title] = win
        win.title(title)
        win.geometry("1000x580")
        left = ttk.Frame(win, padding=8)
        left.pack(side="left", fill="y")
        (desig, name, mat, vol, rev, role), files, pars = eng.model_info(model)
        ttk.Label(left, text=model, font=("Segoe UI", 11, "bold")).pack(anchor="w")
        for k, v in (("Обозначение", desig), ("Наименование", name), ("Материал", mat),
                     ("Объём, мм³", ("%.0f" % vol) if vol else ""), ("Ревизия", rev),
                     ("Роль", role), ("Файлов", files), ("Входит в сборок", pars)):
            ttk.Label(left, text="%s: %s" % (k, v if v not in ("", 0, None) else "—")).pack(anchor="w")
        ttk.Separator(left).pack(fill="x", pady=4)
        out = tk.Text(win, font=("Consolas", 9), bg="#fbfbfb")
        btns = ttk.Frame(left)
        btns.pack(fill="x", pady=2)

        def put(text):
            out.delete("1.0", "end")
            out.insert("end", text)

        def show(fn, *a):
            import contextlib
            import io
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    fn(*a)
            except Exception as e:
                buf.write("ОШИБКА: %s" % e)
            put(buf.getvalue().rstrip())

        def show_files():
            con = eng.connect()
            rows = con.execute("SELECT path,size,rev,revdate,author FROM snapshots WHERE model=? "
                               "ORDER BY path", (model,)).fetchall()
            con.close()
            lines = ["ФАЙЛЫ ИЗДЕЛИЯ: %d" % len(rows)]
            for p, sz, r, rd, au in rows:
                lines.append("%s | рев.%s | %s | %s | %.0f КБ"
                             % (p, r or "-", rd or "-", au or "-", (sz or 0) / 1024.0))
            put("\n".join(lines))

        def show_hist():
            """История файла — ОТДЕЛЬНЫМ полноценным окном (столбцы, даты, сортировка, CSV)."""
            con = eng.connect()
            r = con.execute("SELECT path FROM snapshots WHERE model=? ORDER BY path LIMIT 1",
                            (model,)).fetchone()
            con.close()
            if not r:
                put("файл не найден")
                return
            history_window(root, tk, ttk, filedialog,
                           "История файла — %s" % os.path.basename(r[0]),
                           lambda: history_rows_copy_aware(r[0], {"max_size_mb": float(e_max.get() or 0)}),
                           settings=settings, save_settings=save_settings,
                           status=os.path.basename(r[0]))

        def show_derived():
            lines = ["ЗАГОТОВКА / ОТЛИВКА (из чего сделано это изделие):"]
            d = eng.derived_bases(model)
            for b, k in d:
                lines.append("   ◄ %s: %s" % (_kind(k), b))
            if not d:
                lines.append("   —")
            con = eng.connect()
            rows = con.execute("SELECT child, kind FROM derived WHERE base=? OR base=?",
                               (model, eng.stem(model))).fetchall()
            con.close()
            lines.append("")
            lines.append("ИЗ ЭТОГО СДЕЛАНО (производные):")
            for c, k in rows:
                lines.append("   ► %s (%s)" % (c, _kind(k or "")))
            if not rows:
                lines.append("   —")
            put("\n".join(lines))

        ttk.Button(btns, text="История файла (окно)", command=show_hist).pack(fill="x", pady=2)
        ttk.Button(btns, text="Сборки, куда входит",
                   command=lambda: show(eng.do_tree_up, model, 5)).pack(fill="x", pady=2)
        ttk.Button(btns, text="Состав (вниз)",
                   command=lambda: show(eng.do_tree, model, 5)).pack(fill="x", pady=2)
        ttk.Button(btns, text="Заготовка / отливка", command=show_derived).pack(fill="x", pady=2)
        ttk.Button(btns, text="Файлы изделия", command=show_files).pack(fill="x", pady=2)
        out.pack(side="left", fill="both", expand=True, padx=(8, 8), pady=8)
        show_files()

    _plm_extra = {"nb": nb, "tab_tree": tab_tree, "tview": tview, "tfilter_entry": e_tfilter,
                  "tmode": tmode, "fill_tree_view": fill_tree_view, "expand_all": expand_all,
                  "open_detail": open_detail, "engine": eng}   # для самопроверки
    fill_tree_view()                       # сразу показать верхние папки базы

    # нижнее дерево производства живёт ВНЕ вкладок (полоса lpane прижата к низу окна)
    flt = ttk.Frame(tab_table, padding=(6, 4))
    flt.pack(fill="x")
    ttk.Label(flt, text="Фильтр:").pack(side="left")
    e_filter = ttk.Entry(flt, width=44)
    e_filter.pack(side="left", padx=4)
    ttk.Label(flt, text="часть текста; пусто — показать всё").pack(side="left")
    ttk.Button(flt, text="Сбросить", command=lambda: (e_filter.delete(0, "end"), redraw())).pack(side="left", padx=8)
    e_filter.bind("<KeyRelease>", lambda e: debounce(redraw))

    cols = list(settings.get("columns", DEFAULT_SETTINGS["columns"]))
    if "Версий" not in cols:
        cols.append("Версий")
    if "Файл" in cols:
        cols = ["Файл"] + [c for c in cols if c != "Файл"]
    sort_state = {"col": "Файл", "desc": False}
    rows_all, shown = [], []
    _ROWS = {}                                # uid -> строка: стабильная связь «строка таблицы ↔ данные»
    _SEQ = {"n": 0}

    def row_uid(r):
        """Постоянный id строки: не зависит от сортировки и фильтра (лечит «внизу показано другое»)."""
        u = r.get("_uid")
        if not u:
            _SEQ["n"] += 1
            u = r["_uid"] = "r%d" % _SEQ["n"]
        _ROWS[u] = r
        return u

    body = ttk.Frame(tab_table)
    body.pack(fill="both", expand=True, padx=6, pady=(0, 6))
    body.rowconfigure(0, weight=1)
    body.columnconfigure(0, weight=1)

    def make_tree():
        tv = ttk.Treeview(body, columns=cols, show="headings", height=12)
        for c in cols:
            tv.heading(c, text=c, command=lambda c=c: set_sort(c))
            tv.column(c, width=COLS_WIDTH.get(c, 108), anchor="w")
        return tv

    tree = make_tree()
    vsb = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(body, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    tree.bind("<Double-1>", lambda e: show_history())

    # --- ОНЛАЙН: внизу сразу строится дерево производства по выбранной строке ---
    # 08.10.2026: общая кнопка НАД нижним окном — вернуть предмет к строке, выбранной в ВЕРХНЕМ окне
    ltopbar = ttk.Frame(lpane)
    ltopbar.pack(fill="x")
    ttk.Button(ltopbar, text="Вернуться к выбранному (строка сверху)",
               command=lambda: _return_to_pick()).pack(side="left")
    lsubj = ttk.Label(ltopbar, text="", foreground="#555")
    lsubj.pack(side="left", padx=8)
    lnb = ttk.Notebook(lpane)                  # НИЖНЕЕ окно — ноутбук со своими режимами-вкладками
    lnb.pack(fill="both", expand=True)
    liv = ttk.Frame(lnb, padding=4)
    lnb.add(liv, text=" Родословная ")
    lsum = ttk.Label(liv, text="выбери изделие в ЛЮБОЙ вкладке сверху — покажу родословную: "
                               "откуда пришло · это изделие · что сделано из него · куда входит")
    lsum.pack(anchor="w")
    LTCOLS = ("Тип", "Изделие/файл", "Обозначение", "Наименование", "Кол-во")
    ltv = ttk.Treeview(liv, columns=LTCOLS, show="tree headings", height=8)
    ltv.heading("#0", text="дерево")
    ltv.column("#0", width=320, anchor="w")
    for c in LTCOLS:
        ltv.heading(c, text=c)
        ltv.column(c, width=150 if c != "Кол-во" else 70, anchor="w")
    lvs = ttk.Scrollbar(liv, orient="vertical", command=ltv.yview)
    ltv.configure(yscrollcommand=lvs.set)
    ltv.pack(side="left", fill="both", expand=True)
    lvs.pack(side="left", fill="y")
    ltv.bind("<<TreeviewOpen>>", lambda ev: ltv_open())

    llinks = ttk.Frame(lnb, padding=4)         # вторая вкладка нижнего окна — «Дерево связей»
    lnb.add(llinks, text=" Дерево связей ")
    lsum2 = ttk.Label(llinks, text="выбери что-либо в ЛЮБОЙ вкладке сверху — связи построятся сами")
    lsum2.pack(anchor="w")
    lbox = ttk.Frame(llinks)
    lbox.pack(fill="both", expand=True)
    ltv2 = ttk.Treeview(lbox, columns=LTCOLS, show="tree headings", height=8)
    ltv2.heading("#0", text="связи   ▲ вверх / ▼ вниз")
    ltv2.column("#0", width=320, anchor="w")
    for c in LTCOLS:
        ltv2.heading(c, text=c)
        ltv2.column(c, width=150 if c != "Кол-во" else 70, anchor="w")
    lvs2 = ttk.Scrollbar(lbox, orient="vertical", command=ltv2.yview)
    ltv2.configure(yscrollcommand=lvs2.set)
    ltv2.pack(side="left", fill="both", expand=True)
    lvs2.pack(side="left", fill="y")
    ltv2.bind("<<TreeviewOpen>>", lambda ev: ltv2_open())
    # 08.10.2026: ДВОЙНОЙ клик по узлу нижнего дерева = нижнее окно перестраивается на эту деталь
    ltv.bind("<Double-1>", lambda ev: _goto_node(ltv, _LTREE, ev))
    ltv2.bind("<Double-1>", lambda ev: _goto_node(ltv2, _LLINKS, ev))
    lout = tk.Text(llinks, height=4, font=("Consolas", 9), bg="#fbfbfb")   # вывод кнопок (перенесено из «Дерева»)
    lout.pack(fill="x")

    # ==== 07.10.2026: вкладка «Дерево текстом (вверх+вниз)» — ПОЛНОЕ ASCII-дерево производства ====
    ltext = ttk.Frame(lnb, padding=4)
    ltext_sum = ttk.Label(ltext, text="выбери изделие — покажу ПОЛНОЕ дерево: состав вниз и входимость вверх")
    ltext_sum.pack(anchor="w")
    ltctl = ttk.Frame(ltext)                       # 07.10.2026: раскрытие дерева
    ltctl.pack(anchor="w", pady=2)
    ttk.Label(ltctl, text="Глубина:").pack(side="left")
    lt_depth = ttk.Spinbox(ltctl, from_=1, to=25, width=4)
    lt_depth.set(6)
    lt_depth.pack(side="left", padx=(2, 8))
    lt_int = ttk.Checkbutton(ltctl, text="внутренние коды Creo")
    lt_int.pack(side="left", padx=(0, 8))

    def lt_apply():
        _last["lt_depth"] = int(lt_depth.get() or 6)
        _last["lt_int"] = bool(lt_int.instate(["selected"]))
        _text_tree_show()

    ttk.Button(ltctl, text="Обновить", command=lt_apply).pack(side="left")
    ttk.Label(ltctl, text="← ДВОЙНОЙ клик по изделию = нижнее окно переходит на него; по «… ещё N» — весь список",
              foreground="#666").pack(side="left", padx=6)
    ltbox = ttk.Frame(ltext)
    ltbox.pack(fill="both", expand=True)
    ltree = tk.Text(ltbox, font=("Consolas", 9), wrap="none", bg="#fbfbfb")
    ltv_s = ttk.Scrollbar(ltbox, orient="vertical", command=ltree.yview)
    lth_s = ttk.Scrollbar(ltbox, orient="horizontal", command=ltree.xview)
    ltree.configure(yscrollcommand=ltv_s.set, xscrollcommand=lth_s.set)
    ltv_s.pack(side="right", fill="y")
    lth_s.pack(side="bottom", fill="x")
    ltree.pack(side="left", fill="both", expand=True)

    # ==== 07.10.2026: вкладка «История файла» — ВСЯ история правок по ВСЕМ файлам изделия ====
    lhist = ttk.Frame(lnb, padding=4)
    lhist_sum = ttk.Label(lhist, text="выбери изделие — покажу ВСЮ историю его файлов: "
                                      "ревизия, дата, кто, компьютер, версия Creo, что изменено")
    lhist_sum.pack(anchor="w")
    var_hide = tk.BooleanVar(value=False)      # 07.10.2026: скрыть унаследованные (перенесённые из исходной)
    ttk.Checkbutton(lhist, text="скрыть унаследованные (перенесённые при копировании)",
                    variable=var_hide, command=lambda: _hist_show()).pack(anchor="w")
    HCOLS = ("Файл", "Ревизия", "Дата", "Пользователь", "Компьютер", "Версия Creo", "Что изменено")
    hbox = ttk.Frame(lhist)
    hbox.pack(fill="both", expand=True)
    ltv_h = ttk.Treeview(hbox, columns=HCOLS, show="headings", height=8)
    ltv_h.tag_configure("inh", foreground="#8a8a8a")   # унаследованные записи — серым
    for _c in HCOLS:
        ltv_h.heading(_c, text=_c)
        ltv_h.column(_c, width=320 if _c == "Что изменено" else 118, anchor="w")
    hvs = ttk.Scrollbar(hbox, orient="vertical", command=ltv_h.yview)
    hhs = ttk.Scrollbar(hbox, orient="horizontal", command=ltv_h.xview)
    ltv_h.configure(yscrollcommand=hvs.set, xscrollcommand=hhs.set)
    hbox.rowconfigure(0, weight=1)
    hbox.columnconfigure(0, weight=1)
    ltv_h.grid(row=0, column=0, sticky="nsew")
    hvs.grid(row=0, column=1, sticky="ns")
    hhs.grid(row=1, column=0, sticky="ew")

    # ==== 04.10.2026: вкладка «Свойства детали» — площадь, ТТ, параметры, РАЗМЕРЫ, чертежи ====
    lprop = ttk.Frame(lnb, padding=4)
    lnb.add(lprop, text=" Свойства детали ")
    lnb.add(ltext, text=" Дерево текстом (вверх+вниз) ")   # 4-я вкладка: полное дерево текстом (вверх+вниз)
    lnb.add(lhist, text=" История файла ")                 # 5-я: история правок всех файлов изделия
    lpsum = ttk.Label(lprop, text="выбери изделие — покажу площадь, техтребования, "
                                   "числовые параметры, РАЗМЕРЫ и связанные чертежи")
    lpsum.pack(anchor="w")
    pbox = ttk.Frame(lprop)
    pbox.pack(fill="both", expand=True)
    PROPCOLS = ("Показатель", "Значение")
    ptv = ttk.Treeview(pbox, columns=PROPCOLS, show="headings", height=8)
    ptv.heading("Показатель", text="Показатель")
    ptv.heading("Значение", text="Значение")
    ptv.column("Показатель", width=250, anchor="w")
    ptv.column("Значение", width=620, anchor="w")
    pvs = ttk.Scrollbar(pbox, orient="vertical", command=ptv.yview)
    ptv.configure(yscrollcommand=pvs.set)
    ptv.pack(side="left", fill="both", expand=True)
    pvs.pack(side="left", fill="y")

    def _fmt(x):
        """Число — без хвостовых нулей; строка — как есть."""
        if isinstance(x, float):
            return ("%.2f" % x).rstrip("0").rstrip(".")
        return x

    def _prop_show(model):
        """Показать сводные свойства изделия из файла модели (без базы PLM)."""
        ptv.delete(*ptv.get_children())
        model = eng.stem(model or "")
        if not model:
            lpsum.config(text="выбери изделие — покажу площадь, техтребования, "
                               "числовые параметры, РАЗМЕРЫ и связанные чертежи")
            return
        # путь берём из базы (активной), последняя версия изделия
        path = latest_path(model)
        if not path:
            lpsum.config(text="в базе нет ни одного файла изделия: %s" % model)
            return
        if not os.path.isfile(path):
            lpsum.config(text="файл указан в базе, но отсутствует на диске: %s" % path)
            return
        try:
            raw = read_bytes(path, 0)          # 0 = без ограничения размера: свойства нужны всегда
        except Exception as e:
            lpsum.config(text="не прочитать файл: %s (%s)" % (os.path.basename(path), e))
            return
        if not raw:
            lpsum.config(text="пустой/битый файл: %s" % os.path.basename(path))
            return

        sec = sections(raw)
        area = real_value(raw, "surfarea")
        notes = tech_notes(raw)               # 04.10.2026: с отсевом служебных подписей
        nums = sorted(numeric_params(raw).items(), key=lambda kv: kv[0])

        def add(k, v, bold=False):
            ptv.insert("", "end", values=(k, v),
                       tags=("hdr",) if bold else ())

        add("Файл", os.path.basename(path), True)
        add("Полный путь", path)
        v = real_value(raw, "volume")
        add("Объём, мм³", _fmt(v) if v else "— нет в файле")
        add("Площадь поверхности, мм²", _fmt(area) if area else "— нет в файле")
        # ⚠️ штатный outline_mm на живых файлах даёт не габарит (одно число 31.59 у детали
        # с резьбой М12), поэтому показываем его честно — как «неподтверждённый разбор»
        ol = outline_mm(raw, sec)
        add("Габарит, мм", ("%s  ← штатный разбор, НЕ подтверждён" % ", ".join(
            "%.2f" % x for x in ol)) if ol else "— формат не подтверждён")
        add("Технические требования", "  |  ".join(notes) if notes else "— нет")
        add("Числовых параметров", str(len(nums)))
        for k, val in nums[:60]:
            add("   " + k, _fmt(val))
        # 06.10.2026: РАЗМЕРЫ детали и история изменений (d_dims / dim_history)
        dims = read_dims_all(raw)
        add("Размеров в файле", str(len(dims)) if dims else "— нет (формат или их нет)")
        for dk in sorted(dims, key=lambda s: int(re.sub(r"\D", "", s) or 0)):
            add("   %s, мм" % dk, _fmt(dims[dk]))
        hist = read_history(raw)
        if hist:
            h0 = hist[0]
            add("Последнее изменение (файл)", "%s: %s → %s" % (
                h0["name"],
                _fmt(h0["old"]) if h0["old"] is not None else "—",
                _fmt(h0["new"])))
        else:
            add("Последнее изменение (файл)", "— нет блока diff_vals")
        dims_db, hist_db = archive_dims(model)
        if dims_db:
            add("Размеров в архиве (база)", str(len(dims_db)))
        if hist_db:
            add("История размеров (база)", "%d записей" % len(hist_db))
            for (dt, dm, ov, nv, kd) in hist_db[:40]:
                add("   %s %s" % (dt, dm),
                    "%s → %s  (%s)" % (ov or "—", nv or "", kd or ""))
        # 06.10.2026 (V43): ИСТОРИЯ по АРХИВНЫМ СРЕЗАМ — «боевая информация» из собранных баз
        snaps_db, chg_db = archive_history(model)
        if snaps_db:
            add("АРХИВ: срезов изделия", "%d (от %s до %s)"
                % (len(snaps_db), snaps_db[0][0], snaps_db[-1][0]))
            for (dt, k, mv, rev, au, cr) in snaps_db[:40]:
                add("   срез %s" % dt,
                    "файлов %s · объём %s · рев. %s · автор %s · Creo %s"
                    % (k, _vol_str(mv) if mv else "—", rev or "—", au or "—", cr or "—"))
        else:
            add("АРХИВ: срезы изделия", "— нет (архив не слит в базу)")
        if chg_db:
            add("АРХИВ: правок изделия", str(len(chg_db)))
            for (ts, d) in chg_db[:40]:
                add("   %s" % (ts or "?"), (d or "")[:120])
        dwg = dwg_models(raw)
        add("Показывает модели (если это чертёж)", ", ".join(dwg) if dwg else "— не чертёж")
        lpsum.config(text="%s — свойства из ФАЙЛА модели (площадь, ТТ, параметры, "
                          "размеры, чертежи)" % model)

    def _live_vals(m, i, qty=""):
        role = (i[5] or "") if len(i) > 5 else ""
        kind = "оснастка" if role == "MFG" else ("изделие" if (i[6] or i[7]) else "деталь")
        return (kind, m, i[0] or "", i[1] or "", qty)

    _LTREE = {}
    _LLINKS = {}                               # узел нижнего «дерева связей» -> (модель, режим down/up)

    def _branch_updown(node, model):
        """Ветка изделия в нижнем окне — тот же строитель, что и во вкладке «Дерево»."""
        return _fill_node(ltv, node, model, with_up=True)

    def _ltv_model(node):
        """Модель узла нижнего дерева (если узел — изделие)."""
        return _LTREE.get(node, "")

    def ltv_open(event=None):
        node = ltv.focus()
        model = _ltv_model(node)
        if not model:
            return
        kids = ltv.get_children(node)
        if kids and ltv.item(kids[0], "text") == "загрузка…":
            ltv.delete(*kids)
            _fill_node(ltv, node, model, with_up=True)      # тот же строитель, что и во вкладке «Дерево»

    _PLM = {"data": None}

    def _plm_data_ref():
        if _PLM["data"] is None:
            _PLM["data"] = eng.plm_tree_data()
        return _PLM["data"]

    def live_auto():
        """ОНЛАЙН: нижнее дерево ПЛМ строится САМО — при открытии, после фильтра и после скана."""
        ltv.delete(*ltv.get_children())
        _LTREE.clear()
        pat = e_filter.get().strip()
        if pat:                                   # фильтр — деревья по найденным во ВСЕЙ базе
            rows = list(shown) if shown else db_search_rows(pat.split(), 25)[0]
            shown = 0
            for r in rows[:25]:
                m = eng.stem(os.path.basename(r.get("_path") or ""))
                if not m:
                    continue
                rn = ltv.insert("", "end", open=False, text=m, values=_live_vals(
                    m, eng.models_info([m]).get(m, ("", "", "", 0, "", "", 0, 0))))
                _LTREE[rn] = m
                _branch_updown(rn, m)
                shown += 1
            lsum.config(text="онлайн по фильтру: совпадений %d → деревьев %d" % (len(rows), shown))
            return
        tops, children, info, derived = _plm_data_ref()
        rn = ltv.insert("", "end", open=True,
                        text="ВСЁ ПРОИЗВОДСТВО (ПЛМ) — верхних сборок %d" % len(tops),
                        values=("корень", "", "", "", ""))
        for m in tops:
            n = ltv.insert(rn, "end", text=m,
                           values=_live_vals(m, info.get(m, ("", "", "", 0, "", "", 0, 0))))
            _LTREE[n] = m
            ltv.insert(n, "end", text="загрузка…")
        lsum.config(text="дерево ПЛМ: верхних сборок %d · раскрывай узлы (состав / заготовка-отливка) — строится само"
                    % len(tops))

    _last = {"model": ""}                      # выбранная модель — общая для обеих вкладок низа

    def _prod_show(model):
        """Вкладка «Дерево производства»: состав вниз + заготовка/отливка + входимость вверх."""
        ltv.delete(*ltv.get_children())
        _LTREE.clear()
        info = eng.models_info([model]).get(model, ("", "", "", 0, "", "", 0, 0))
        rn = ltv.insert("", "end", open=True, text=model, values=_live_vals(model, info))
        _LTREE[rn] = model                           # V81: корень «Родословной» тоже кликабелен
        der, ups, dn = _branch_updown(rn, model)
        try:
            ltv.yview_moveto(0)                 # показать начало дерева
            ltv.see(rn)
        except Exception:
            pass
        lsum.config(text="родословная «%s»: состав %d · входит в сборок %d (все уровни) · заготовок/отливок %d"
                    % (model, dn, ups, der))

    def _links_show(model):
        """Вкладка «Дерево связей»: ▲ вверх — где используется; ▼ вниз — состав + отражения + наследование."""
        ltv2.delete(*ltv2.get_children())
        _LLINKS.clear()
        kids = eng.plm_children(model)
        refl = eng.derived_children(model)
        bases = eng.derived_bases(model)
        up = eng.plm_up_data(model, 8)
        rel = {model} | {c for c, _ in kids} | {c for c, _ in refl} | {b for b, _ in bases if b}
        for v in up.values():
            rel |= {x[0] for x in v}
        info = eng.models_info(list(rel))

        def iv(m, q=""):
            return _live_vals(m, info.get(m, ("", "", "", 0, "", "", 0, 0)), q)

        rn = ltv2.insert("", "end", open=True, text=model, values=iv(model))
        _LLINKS[rn] = (model, "down")                # V81: корень «Дерева связей» тоже кликабелен

        # ▼ вниз — СОСТАВ (ленивая загрузка уровней)
        dn = ltv2.insert(rn, "end", open=False, text="▼ состав (вниз)")
        if not kids:
            ltv2.insert(dn, "end", text="— в базе нет состава")
        for c, q in kids:
            nn = ltv2.insert(dn, "end", text="%s  x%d" % (c, q), values=iv(c, "x%d" % q))
            _LLINKS[nn] = (c, "down")
            ltv2.insert(nn, "end", text="загрузка…")

        # ▼ вниз — ОТРАЖЕНИЯ (кто сделан ИЗ этой модели) — она для них «пересохранён источник»
        ref = ltv2.insert(rn, "end", open=bool(refl), text="▼ из неё пересохранено (отражения): %d" % len(refl))
        if not refl:
            ltv2.insert(ref, "end", text="— обратных связей нет")
        for c, k in refl:
            kd = {"наследование": "заготовка", "производная": "отливка"}.get(k, "заготовка/отливка")
            ltv2.insert(ref, "end", text="%s: %s" % (kd, c), values=("отражение", c, "", "", ""))

        # ▼ вниз — НАСЛЕДОВАННАЯ ГЕОМЕТРИЯ (заготовки/отливки этой модели) — она ПЕРЕСОХРАНЕНА ИЗ них
        inh = ltv2.insert(rn, "end", open=bool(bases),
                          text="▼ она пересохранена из (заготовка/отливка): %d" % len(bases))
        if not bases:
            ltv2.insert(inh, "end", text="— наследования нет")
        for b, k in bases:
            kd = {"наследование": "заготовка", "производная": "отливка",
                  "hash": "заготовка/отливка"}.get(k, "заготовка/отливка")
            ltv2.insert(inh, "end", text="◄ %s: %s" % (kd, b or "имя не найдено (в файле только код)"),
                        values=(kd, b or "—", "", "", ""))

        # ▲ вверх — ГДЕ ИСПОЛЬЗУЕТСЯ (все сборки, все уровни)
        n_up = len(up)
        un = ltv2.insert(rn, "end", open=True, text="▲ где используется (вверх): сборок в цепочке %d" % n_up)
        if not up:
            ltv2.insert(un, "end", text="— ни в одну сборку не входит (верхнее изделие)")
        else:
            _fill_up(un, model, up, info, 1, frozenset((model,)))

        try:
            ltv2.yview_moveto(0)
            ltv2.see(rn)
        except Exception:
            pass
        lsum2.config(text="связи: %s — состав %d · из неё пересохранено %d · пересохранена из %d · сборок вверх %d"
                     % (model, len(kids), len(refl), len(bases), n_up))

    def _fill_up(parent_node, model, up, info, depth, seen):
        """Ветка «где используется»: рекурсивно по карте plm_up_data (все сборки, все уровни)."""
        for p, q in up.get(model, []):
            if p in seen:
                continue
            nn = ltv2.insert(parent_node, "end", text="%s  ↑ x%d" % (p, q),
                             values=_live_vals(p, info.get(p, ("", "", "", 0, "", "", 0, 0)), "x%d" % q))
            _LLINKS[nn] = (p, "up")
            if depth < 8:
                _fill_up(nn, p, up, info, depth + 1, seen | {p})

    def ltv2_open(event=None):
        """Раскрытие узла «Дерева связей»: ленивая достройка состава/входимости по базе."""
        node = ltv2.focus()
        rec = _LLINKS.get(node)
        if not rec:
            return
        c_model, mode = rec
        kids = ltv2.get_children(node)
        if not (kids and ltv2.item(kids[0], "text") == "загрузка…"):
            return
        ltv2.delete(*kids)
        info = eng.models_info([c_model]).get(c_model, ("", "", "", 0, "", "", 0, 0))
        if mode == "down":
            pairs = [(c, q, "%s  x%d" % (c, q), "x%d" % q) for c, q in eng.plm_children(c_model)]
        else:
            pairs = [(p, q, "%s  ↑ x%d" % (p, q), "↑ x%d" % q) for p, q in eng.plm_parents(c_model)]
        for nm, q, label, qv in pairs:
            nn = ltv2.insert(node, "end", text=label,
                             values=_live_vals(nm, info.get(nm, ("", "", "", 0, "", "", 0, 0)), qv))
            _LLINKS[nn] = (nm, mode)
            ltv2.insert(nn, "end", text="загрузка…")

    def _made_window(mdl):
        """Окно: ВЕСЬ список «кто сделан ИЗ модели» (строка «… ещё N» в дереве)."""
        try:
            rows = eng.made_of_list(mdl, 0)
        except Exception as e:
            _text_window("Сделано из «%s»" % mdl, "ошибка", "не удалось получить список: %s" % e)
            return
        txt = "сделано из «%s» — всего %d\n\n" % (mdl, len(rows))
        for nm, kind, name, vol, rev in rows:
            txt += "%-46s %-13s %s%s%s\n" % (nm, kind,
                                             ("«%s» " % name) if name else "",
                                             ("%.0f мм³ " % vol) if vol else "",
                                             ("rev%s" % rev) if rev else "")
        _text_window("Сделано из «%s»" % mdl, "сделано из «%s» — всего %d" % (mdl, len(rows)), txt)

    _TMAP = {}                              # V82: номер строки Text -> (kind, payload) для кликов

    def _text_line_at(ev):
        """Строка «Дерева текстом» под курсором: (номер, kind, payload) либо None."""
        try:
            ln = int(ltree.index("@%d,%d" % (ev.x, ev.y)).split(".")[0])
        except Exception:
            return None
        rec = _TMAP.get(ln)
        return (ln, rec[0], rec[1]) if rec else None

    def _text_dbl(ev):
        """V82: ОДИН обработчик двойного клика — переход по строке под курсором.

        Раньше tag_bind звался в цикле ПО СТРОКЕ и ЗАМЕНЯЛ сам себя (Tk: без «+» —
        replace), выживала последняя лямбда — клик вёл не туда («не работает»)."""
        rec = _text_line_at(ev)
        if rec:
            if rec[1] == "nd" and rec[2]:
                _goto_model(rec[2])
            return "break"
        return None

    def _text_more(ev):
        """V82: клик по «… ещё N» — окно со ВСЕМ списком (тоже по строке под курсором)."""
        rec = _text_line_at(ev)
        if rec and rec[1] == "more" and rec[2]:
            _made_window(rec[2])
            return "break"
        return None

    def _text_tree_show(model=None):
        """Вкладка «Дерево текстом»: ПОЛНОЕ дерево связей.

        ДВОЙНОЙ клик по ИЗДЕЛИЮ — нижнее окно перестраивается на него (как выбор в верхнем окне).
        Клик по «… ещё сделано из неё: N» — окно со ВСЕМ списком."""
        if model:
            _last["lroot"] = model
        m = _last.get("lroot") or _last.get("model")
        try:
            ltree.configure(state="normal")
            ltree.delete("1.0", "end")
            _TMAP.clear()
            for tg in ("nd", "mr", "hd"):
                ltree.tag_delete(tg)
            # V82: один обработчик на виджет (replace тем же хэндлером безвреден)
            ltree.bind("<Double-1>", _text_dbl)
            ltree.bind("<Button-1>", _text_more)
        except Exception:
            pass
        ltree.tag_configure("nd", foreground="#0a4a8a", underline=True)
        ltree.tag_configure("mr", foreground="#8a4a00", underline=True)
        ltree.tag_configure("hd", foreground="#123", background="#eef3f8")
        try:
            if not m:
                ltree.insert("end", "выбери изделие в ЛЮБОЙ вкладке сверху — покажу полное дерево\n")
                ltext_sum.config(text="выбери изделие — полное дерево: состав + входимость + наследование")
                ltree.configure(state="disabled")
                return
            depth = int(_last.get("lt_depth") or 6)
            internal = bool(_last.get("lt_int"))
            lines = eng.full_tree_lines(m, depth, internal)
            for text, kind, payload in lines:
                start = ltree.index("end-1c")
                ltree.insert("end", text + "\n")
                end = ltree.index("end-1c")
                if kind == "node" and payload:
                    ltree.tag_add("nd", start, end)
                    # V82: вместо tag_bind в цикле (replace) — карта строка->payload
                    _TMAP[int(end.split(".")[0])] = ("nd", payload)
                elif kind == "more" and payload:
                    ltree.tag_add("mr", start, end)
                    _TMAP[int(end.split(".")[0])] = ("more", payload)
                elif kind == "head":
                    ltree.tag_add("hd", start, end)
            ltext_sum.config(text="полное дерево: %s (глубина %d) · ДВОЙНОЙ клик по изделию = перейти на него, "
                                  "по «… ещё N» = весь список" % (m, depth))
            ltree.configure(state="disabled")
        except Exception as e:
            try:
                ltree.configure(state="disabled")
            except Exception:
                pass
            ltext_sum.config(text="не удалось построить дерево: %s" % e)

    def _hist_show(model=None):
        """Вкладка «История файла»: ПОЛНАЯ история правок по ВСЕМ файлам изделия.

        История берётся ИЗ САМИХ ФАЙЛОВ (trail Creo). Если изделие — КОПИЯ, Creo перенёс в файл
        историю ИСХОДНОЙ модели: такие записи показываем с именем ИСХОДНОГО файла (серым), а галка
        «скрыть унаследованные» убирает их совсем. Источник берём из файла (`from_mdl_name`).
        """
        m = model or _last.get("model") or ""
        try:
            ltv_h.delete(*ltv_h.get_children())
        except Exception:
            return
        if not m:
            lhist_sum.config(text="выбери изделие в ЛЮБОЙ вкладке сверху — покажу историю его файлов")
            return
        try:
            con = eng.connect()
            paths = [r[0] for r in con.execute("SELECT path FROM snapshots WHERE model=? ORDER BY path",
                                               (eng.stem(m),))]
            con.close()
        except Exception:
            paths = []
        if not paths:
            lhist_sum.config(text="изделие %s: файлов в базе нет" % m)
            return
        hide_inh = bool(var_hide.get())
        src, _sp, src_keys, src_found = copy_source_of(paths, settings)
        total, inh, own_iso = 0, 0, []
        for p in paths:
            try:
                rows = history_rows(p, settings)
            except Exception as ex:
                ltv_h.insert("", "end", values=(os.path.basename(p), "ошибка", str(ex), "", "", "", ""))
                continue
            pbase = os.path.basename(p)
            pstem = eng.stem(pbase)
            own_suffix = pbase[len(pstem):] if pbase.upper().startswith(pstem) else ""
            src_name = (src + own_suffix) if (src and own_suffix) else pbase
            for row in rows:
                total += 1
                own = True
                if src_found:
                    own = ((row.get("Ревизия", ""), row.get("Дата", ""), row.get("Пользователь", ""))
                           not in src_keys)
                if not own:
                    inh += 1
                    if hide_inh:
                        continue
                fname = row.get("Файл", "") if own else src_name
                item = ltv_h.insert("", "end", values=(fname, row.get("Ревизия", ""),
                                                       row.get("Дата", ""), row.get("Пользователь", ""),
                                                       row.get("Компьютер", ""), row.get("Версия Creo", ""),
                                                       row.get("Что изменено", "")))
                if not own:
                    ltv_h.item(item, tags=("inh",))
                elif row.get("_dt"):
                    own_iso.append(row["_dt"])
        shown = total - inh if hide_inh else total
        if src_found:
            cdate = ""
            try:
                if own_iso:
                    cdate = min(datetime.datetime.fromisoformat(x) for x in own_iso).strftime("%d.%m.%Y")
            except Exception:
                cdate = ""
            lhist_sum.config(text="⚠ модель скопирована из %s%s; записи РАНЬШЕ копии относятся к "
                                  "ИСХОДНОЙ модели · файлов %d, записей %d (унаследованных %d%s)"
                             % (src, (" (копия ~%s)" % cdate) if cdate else "",
                                len(paths), shown, inh, ", скрыты галкой" if hide_inh else ""))
        else:
            lhist_sum.config(text="история «%s»: файлов %d, записей %d" % (m, len(paths), shown))

    def _bottom_render():
        """Наполнить АКТИВНУЮ вкладку нижнего окна выбранной моделью (или автосводкой)."""
        model = _last["model"]
        try:
            sel = lnb.select()
        except Exception:
            sel = ""
        # сравниваем по САМОМУ виджету (а не по номеру вкладки) — порядок вкладок может меняться
        if sel == str(lprop):
            # 04.10.2026: «Свойства детали» — площадь, ТТ, параметры, чертежи
            try:
                _prop_show(model)
            except Exception as e:      # вкладка не должна ронять всё окно
                ptv.delete(*ptv.get_children())
                ptv.insert("", "end", values=("Ошибка разбора",
                                               "%s: %s" % (type(e).__name__, e)))
                lpsum.config(text="не удалось показать свойства: %s" % e)
            return
        if sel == str(ltext):           # 07.10.2026: полное дерево связей (узлы кликабельны)
            _text_tree_show()
            return
        if sel == str(lhist):           # 07.10.2026: история правок всех файлов изделия
            _hist_show(model)
            return
        if not model:
            if sel == str(llinks):
                ltv2.delete(*ltv2.get_children())
                _LLINKS.clear()
                lsum2.config(text="выбери что-либо в ЛЮБОЙ вкладке сверху — связи построятся сами")
            else:
                live_auto()
            return
        if sel == str(llinks):
            try:
                _prod_show(model)        # «Дерево производства» держим готовым — при переходе на вкладку не будет пусто
            except Exception:
                pass
            _links_show(model)
        else:
            _prod_show(model)

    def _bottom_show(model, pick=False):
        """Показать в НИЖНЕМ окне связи модели. Зовут вкладки СВЕРХУ (pick=True) и переходы внизу."""
        model = eng.stem(model or "")
        _last["model"] = model
        if pick:
            _last["pick"] = model     # 08.10.2026: строка, выбранная ВВЕРХУ, — к ней возвращает кнопка
        _last.pop("lroot", None)
        try:                          # 08.10.2026: строка над нижним окном — что именно показывает низ
            _txt = ("низ показывает: %s" % model) if model else ""
            if model and not pick and _last.get("pick") and _last.get("pick") != model:
                _txt += "   (переход; кнопка вернёт к верхнему выбору)"
            lsubj.config(text=_txt)
        except Exception:
            pass
        _bottom_render()

    def _goto_model(m):
        """08.10.2026: ДВОЙНОЙ клик по детали в нижнем окне = перестроить низ на неё (как выбор сверху)."""
        if m:
            _bottom_show(m)

    def _return_to_pick():
        """08.10.2026: «Вернуться к выбранному» — предмет низа = строка, выбранная в ВЕРХНЕМ окне."""
        m = _last.get("pick") or _last.get("model")
        if m:
            _bottom_show(m)

    def _goto_node(tree_widget, registry, event=None):
        """07.10.2026/08.10.2026: переход по узлу нижнего дерева на ДВОЙНОЙ клик (узел берём под курсором)."""
        try:
            node = tree_widget.identify_row(event.y) if event is not None else tree_widget.focus()
        except Exception:
            node = tree_widget.focus()
        rec = registry.get(node)
        m = rec[0] if isinstance(rec, tuple) else rec
        if not m:
            # V81 (08.10.2026): узла может НЕТЬ в реестре (входит-в / MFG / заготовка / корень) —
            # модель берём из 1-й колонки values строки; заглушки («—», пусто) никуда не ведут.
            try:
                vals = tree_widget.item(node, "values")
            except Exception:
                vals = ()
            cand = ((vals[1] if len(vals) > 1 else "") or "").strip()
            m = "" if cand in ("", "—", "-") else cand
        if m:
            _bottom_show(m)

    lnb.bind("<<NotebookTabChanged>>", lambda ev: _bottom_render())

    def live_tree(event=None):
        """ОНЛАЙН по выбранной строке ТАБЛИЦЫ: состав ВНИЗ и ВСЕ сборки ВВЕРХ."""
        sel = tree.selection()
        row = _ROWS.get(sel[0]) if sel else None
        if not row:
            live_auto()
            return
        p = row.get("_path") or ""
        _bottom_show(eng.stem(os.path.basename(p)) if p else "", pick=True)

    tree.bind("<<TreeviewSelect>>", live_tree)

    def expl_live(event=None):
        """Выбор в ПРОВОДНИКЕ → нижнее окно (выбран файл → связи его модели)."""
        p = _EFILE.get(eview.focus())
        if p:
            _bottom_show(eng.stem(os.path.basename(p)), pick=True)

    eview.bind("<<TreeviewSelect>>", expl_live)

    def tree_live(event=None):
        """Выбор в ДЕРЕВЕ → нижнее окно (узел → связи его модели)."""
        sel = tview.focus()
        if not sel:
            return
        txt = (tview.item(sel, "text") or "").strip()
        m = eng.stem(txt.split()[0]) if txt else ""
        if m:
            _bottom_show(m, pick=True)

    tview.bind("<<TreeviewSelect>>", tree_live)
    _plm_extra.update({"ltv": ltv, "ltv2": ltv2, "lnb": lnb, "live_tree": live_tree,
                       "live_auto": live_auto, "bottom_show": _bottom_show})   # для самопроверки

    _auto = {"done": False}

    def on_tab(ev=None):
        """При входе на вкладку — только список верхних сборок (без «развернуть всё»)."""
        try:
            if nb.index(nb.select()) == 1 and not _auto["done"]:
                _auto["done"] = True
                fill_tree_view()              # свёрнутый вид: корень + верхние сборки
        except Exception:
            pass

    nb.bind("<<NotebookTabChanged>>", on_tab)

    def sort_key(r, col):
        v = r.get(col, "")
        if col in ("Записей", "Ревизия"):
            try:
                return (0, int(v))
            except (TypeError, ValueError):
                return (1, 0)
        if col == "Объём, мм³":
            try:
                return (0, float(v))
            except (TypeError, ValueError):
                return (1, 0.0)
        if col == "Дата":
            d = parse_dt(v)
            return (0, d.timestamp()) if d else (1, 0)
        if col == "Создан":
            return (0, float(r.get("_created_ts") or 0))
        if col == "Изменён":
            return (0, float(r.get("_mtime_ts") or 0))
        return (0, str(v).lower())

    def set_sort(col):
        if sort_state["col"] == col:
            sort_state["desc"] = not sort_state["desc"]
        else:
            sort_state["col"], sort_state["desc"] = col, False
        redraw()

    def redraw():
        pat = e_filter.get().strip()
        prev = tree.selection()
        keep = prev[0] if prev else ""
        if pat:                       # ФИЛЬТР — по ВСЕЙ БАЗЕ, а не по загруженной странице
            rows, hits, mode = db_search_rows(pat.split(), int(settings.get("show_limit") or 50000))
            rts = [r for r in roots_of(e_folder.get(), e_folder2.get()) if os.path.isdir(r)]
            in_r = sum(1 for r in rows if path_under(r["_path"], rts)) if rts else len(rows)
            tail = (" · по фильтру %d в базе %d (слова: %s) · в папках окна %d, вне папок %d%s"
                    % (hits, db_total(None), mode, in_r, len(rows) - in_r,
                       (" · показаны первые %d — уточните слова" % len(rows)) if hits > len(rows) else ""))
        else:
            rows = list(rows_all)
            tail = " из %d загруженных" % len(rows_all)
        rows.sort(key=lambda r: sort_key(r, sort_state["col"]), reverse=sort_state["desc"])
        shown[:] = rows
        tree.delete(*tree.get_children())
        for r in rows:
            tree.insert("", "end", iid=row_uid(r), values=[r.get(c, "") for c in cols])
        for c in cols:
            mark = "  ▼" if (sort_state["col"] == c and sort_state["desc"]) else \
                   ("  ▲" if sort_state["col"] == c else "")
            tree.heading(c, text=c + mark)
        lbl.config(text="показано %d%s" % (len(rows), tail))
        if keep and keep in tree.get_children():
            tree.selection_set(keep)          # выбор сохраняется при сортировке/фильтре
        try:
            live_tree()                       # низ всегда следует за выбором (иначе — общее дерево)
        except Exception:
            pass

    def rebuild_tree():
        nonlocal tree
        tree.destroy()
        tree = make_tree()
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.configure(command=tree.yview)
        hsb.configure(command=tree.xview)
        tree.grid(row=0, column=0, sticky="nsew")
        tree.bind("<Double-1>", lambda e: show_history())
        redraw()

    root._plm = {"redraw": redraw, "rebuild": rebuild_tree, "tree": lambda: tree,
                 "set_sort": set_sort, "rows_map": lambda: _ROWS, **_plm_extra}

    def show_readme():
        w = getattr(root, "_readme_win", None)
        if w is not None and w.winfo_exists():
            w.deiconify()
            w.lift()
            w.focus_force()
            return
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
                      "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            lbl.config(text="README не прочитан: %s" % e)
            return
        win = tk.Toplevel(root)
        root._readme_win = win
        win.title("README — PLM Reader")
        win.geometry("900x680")
        t = tk.Text(win, wrap="word", font=("Consolas", 9))
        t.pack(fill="both", expand=True)
        t.insert("1.0", text)

    def check_base():
        """Быстро: актуальна база или нужен скан (обход+stat, БЕЗ чтения файлов)."""
        lbl.config(text="проверяю актуальность базы…")

        def work():
            try:
                import engine as eng
                r = eng.do_check(exclude=exclude_list(settings.get("exclude")))
            except Exception as e:
                try:
                    root.after(0, lambda: lbl.config(text="проверка не удалась: %s" % e))
                except Exception:
                    pass
                return
            try:
                root.after(0, lambda: show_check(r))
            except Exception:
                pass                    # окно уже закрыто — молча


        threading.Thread(target=work, daemon=True).start()

    def show_check(r):
        _p = r.get("purged", 0)
        _tail = ("  ·  старые версии после Purge: %d — норма" % _p) if _p else ""
        if r.get("need"):
            lbl.config(text="НУЖЕН СКАН: новых %d · изменённых %d · пропало %d (%.1f с)%s"
                       % (r["new"], r["mod"], r["gone"], r["secs"], _tail))
        else:
            lbl.config(text="БАЗА АКТУАЛЬНА: изделий %d (файлов на диске %d, с копиями версий), изменений нет (%.1f с)%s"
                       % (r.get("models", r["total"]), r["total"], r["secs"], _tail))
        log_line("check: %s" % r.get("verdict", ""))

    def load_base(limit=None):
        """Показать базу БЕЗ чтения файлов: строки паспортов из plm_reader.db."""
        if not limit:
            limit = int(settings.get("show_limit") or 50000)   # лимит показа — из настройки «ПОКАЗ строк»
        roots = [r for r in roots_of(e_folder.get(), e_folder2.get()) if os.path.isdir(r)]
        rows_all.clear()
        tree.delete(*tree.get_children())
        rows_all.extend(db_rows(roots or None, limit))
        redraw()
        tot = db_total(roots or None)
        where = " + ".join(roots) if roots else "вся база"
        lbl.config(text="из базы: показано %d из %d (%s)" % (len(rows_all), tot, where))
        log_line("base: показано %d из %d (%s)" % (len(rows_all), tot, where))

    def _active_stamp():
        """Отпечаток активной базы (имя+время) — по нему замечаем публикацию другого ПК."""
        try:
            p = _active_db_file()
            return "%s|%d" % (os.path.basename(p), int(os.path.getmtime(p)))
        except Exception:
            return ""

    def refresh_from_db(reason=None, stamp=None):
        """Перечитать таблицу из СВЕЖАЙШЕЙ базы (фильтр и выделение сохраняются)."""
        if getattr(root, "_plm_scan_active", False) or getattr(root, "_plm_refreshing", False):
            return
        root._plm_refreshing = True
        try:
            sel = tree.selection()
            keep = sel[0] if sel else ""
            load_base()
            if keep and keep in tree.get_children():
                try:
                    tree.selection_set(keep)
                except Exception:
                    pass
            root._plm_db_stamp = stamp if stamp is not None else _active_stamp()
            if reason:
                lbl.config(text=reason)
        finally:
            root._plm_refreshing = False

    def watch_db():
        """Раз в 15 с: не появилась ли на складе более свежая база (её опубликовал другой ПК)."""
        try:
            enabled = bool(var_auto.get())
        except Exception:
            enabled = True
        if enabled and not getattr(root, "_plm_scan_active", False):
            def work():
                st = _active_stamp()
                if st and st != getattr(root, "_plm_db_stamp", None):
                    try:
                        root.after(0, lambda: refresh_from_db(
                            "база обновлена на другой машине — таблица перечитана", st))
                    except Exception:
                        pass
            try:
                threading.Thread(target=work, daemon=True).start()
            except Exception:
                pass
        root.after(15000, watch_db)

    ALL_FIELDS = ["Файл", "Обозначение", "Наименование", "Материал", "Объём, мм³", "Тип",
                  "Роль", "Родитель", "Записей", "Версий", "Ревизия", "Дата",
                  "Создан", "Изменён", "Пользователь", "Версия Creo", "Габарит, мм"]

    def save_settings():
        save_settings_file(settings)                    # атомарная запись; ошибка — в лог

    def save_ui():
        """Собрать в настройки то, что на экране, и сохранить (зовётся при закрытии окна)."""
        try:
            settings.update({"max_size_mb": float(e_max.get() or 0),
                             "recurse": var_rec.get(), "latest_only": var_lat.get(),
                             "depth": int(e_depth.get() or 0), "purge_keep": int(e_keep.get() or 2),
                             "auto_refresh": var_auto.get(), "full": var_full.get()})
        except Exception:
            pass
        save_settings_file(settings)

    def on_close():
        save_ui()
        try:
            root.destroy()
        except Exception:
            pass

    root.protocol("WM_DELETE_WINDOW", on_close)

    if os.environ.get("PLM_SELFCHECK"):        # самопроверка вида: ключевые кнопки видны и внутри окна
        def _selfcheck():
            try:
                root.update_idletasks()
                w, h = root.winfo_width(), root.winfo_height()
                bad = []
                for name, wdg in (("Пути…", btn_paths), ("Показывать", sp_limit), ("Сканировать", btn),
                                  ("Стоп", b_stop), ("Актуально?", b_check),
                                  ("Purge-ПЛАН", b_purge_plan), ("Purge-бэкап", b_purge_run)):
                    vis = wdg.winfo_ismapped()
                    x = wdg.winfo_rootx() - root.winfo_rootx()
                    y = wdg.winfo_rooty() - root.winfo_rooty()
                    if not vis or not (0 <= x < w and 0 <= y < h):
                        bad.append("%s(vis=%s,%d,%d)" % (name, vis, x, y))
                log_line("selfcheck: окно %dx%d, проверено виджетов 7, скрыто/вне окна: %s"
                         % (w, h, ", ".join(bad) if bad else "нет"))
                log_line("selfcheck: лимит=%s | %s | %s"
                         % (sp_limit.get(), lbl_p.cget("text").replace("\n", " | ")[:80],
                            lbl_e.cget("text").replace("\n", " | ")[:80]))
                tabs = nb.tabs()
                bad_tabs = []
                for t in tabs:
                    nb.select(t)
                    root.update_idletasks()
                    if not ltv.winfo_ismapped():
                        bad_tabs.append(nb.tab(t, "text").strip())
                log_line("selfcheck: нижнее дерево производства видно на вкладках: %s"
                         % (("НЕТ на: " + ", ".join(bad_tabs)) if bad_tabs
                            else "все %d" % len(tabs)))
                log_line("selfcheck: полоса низа — lpane(%s,h=%d) liv(%s,h=%d) ltv(%s,h=%d)"
                         % (lpane.winfo_ismapped(), lpane.winfo_height(),
                            liv.winfo_ismapped(), liv.winfo_height(),
                            ltv.winfo_ismapped(), ltv.winfo_height()))
                log_line("selfcheck: нижний ноутбук — вкладок %d, активна «%s», ltv2(h=%d)"
                         % (len(lnb.tabs()), lnb.tab(lnb.select(), "text").strip(),
                            ltv2.winfo_height()))
                if os.environ.get("PLM_SELFCHECK") == "2":     # проверка кнопки ПУРГЕ: ПЛАН целиком
                    try:
                        purge_show()
                        log_line("selfcheck: ПУРГЕ ПЛАН выполнен — окно плана открыто")
                    except Exception as e:
                        log_line("selfcheck: ПУРГЕ ПЛАН упал: %s" % e)
                nb.select(tabs[0])
            except Exception as e:
                log_line("selfcheck: ошибка %s" % e)
        root.after(1500, _selfcheck)

    def split_list(s):
        return [x.strip() for x in (s or "").replace(";", ",").split(",") if x.strip()]

    def choose_columns():
        win = tk.Toplevel(root)
        win.title("Столбцы и параметры — сохраняются в настройках")
        win.geometry("780x600")
        ttk.Label(win, text="Какие столбцы показывать («Файл» — всегда первый):").pack(anchor="w", padx=8, pady=(8, 0))
        box = ttk.Frame(win, padding=8)
        box.pack(fill="x")
        vars_ = {}
        for i, f in enumerate(ALL_FIELDS):
            vars_[f] = tk.BooleanVar(value=f in cols)
            cb = ttk.Checkbutton(box, text=f, variable=vars_[f])
            cb.grid(row=i // 3, column=i % 3, sticky="w", padx=6, pady=2)
            if f == "Файл":
                cb.state(["disabled"])
        pf = ttk.Frame(win, padding=8)
        pf.pack(fill="x")
        ttk.Label(pf, text="Имена параметров для «Обозначение» (через запятую, по порядку поиска):").pack(anchor="w")
        e_des = ttk.Entry(pf, width=92)
        e_des.insert(0, ", ".join(settings.get("param_designation", DEFAULT_SETTINGS["param_designation"])))
        e_des.pack(fill="x", pady=(0, 6))
        ttk.Label(pf, text="Имена параметров для «Наименование»:").pack(anchor="w")
        e_nam = ttk.Entry(pf, width=92)
        e_nam.insert(0, ", ".join(settings.get("param_name", DEFAULT_SETTINGS["param_name"])))
        e_nam.pack(fill="x", pady=(0, 6))
        ttk.Label(pf, text="Имена параметров для «Материал»:").pack(anchor="w")
        e_mat = ttk.Entry(pf, width=92)
        e_mat.insert(0, ", ".join(settings.get("param_material", DEFAULT_SETTINGS["param_material"])))
        e_mat.pack(fill="x")
        ttk.Label(win, text="Список проверяется по порядку — берётся первое НЕПУСТОЕ.\n"
                            "Разделитель правил — ЗАПЯТАЯ. Правило = имя параметра ИЛИ шаблон:\n"
                            "  {NAME_1} {NAME_2}      → склеит в одну строку: M5x20 ГОСТ 11738-72\n"
                            "  {ИМЯ} — значение; \"текст\" — вставить текст (кавычки НЕ выводятся);\n"
                            "  + — склейка без пробела; обычный пробел = пробел; пустые части отбрасываются.\n"
                            "Пример:  NAME_1, NAME_2, НАИМЕНОВАНИЕ    или    {NAME_1} {NAME_2}, НАИМЕНОВАНИЕ",
                  justify="left").pack(anchor="w", padx=8, pady=(0, 8))

        def apply():
            cols[:] = ["Файл"] + [f for f in ALL_FIELDS if f != "Файл" and vars_[f].get()]
            settings["columns"] = list(cols)
            settings["param_designation"] = split_list(e_des.get())
            settings["param_name"] = split_list(e_nam.get())
            settings["param_material"] = split_list(e_mat.get())
            save_settings()
            rebuild_tree()
            lbl.config(text="столбцы сохранены")
            win.destroy()

        ttk.Button(win, text="Применить и сохранить", command=apply).pack(anchor="w", padx=8, pady=(0, 10))

    def hist_settings():
        return {"max_size_mb": float(e_max.get() or 0), "recurse": var_rec.get()}

    def show_history():
        items = tree.selection()
        if not items:
            messagebox.showinfo(APP_TITLE, "Выберите строку в таблице.")
            return
        row = _ROWS.get(items[0]) or {}
        path = row.get("_path")
        if not path:
            return
        history_window(root, tk, ttk, filedialog,
                       "История изменений — %s" % os.path.basename(path),
                       lambda: history_rows_copy_aware(path, hist_settings()),
                       settings=settings, save_settings=save_settings,
                       status=os.path.basename(path))

    def show_folder_history():
        folder = e_folder.get().strip()
        if not os.path.isdir(folder):
            messagebox.showwarning(APP_TITLE, "Сначала выберите папку.")
            return
        history_window(root, tk, ttk, filedialog,
                       "История изменений — %s" % folder,
                       lambda: history_folder(folder, hist_settings()),
                       settings=settings, save_settings=save_settings,
                       status=folder)

    q = queue.Queue()

    def poll_scan():
        try:
            while True:
                msg = q.get_nowait()
                if msg[0] == "row":
                    r = msg[1]
                    rows_all.append(r)
                    pat = e_filter.get().strip()
                    if match_filter(r, cols, pat):
                        tree.insert("", "end", iid=row_uid(r), values=[r.get(c, "") for c in cols])
                elif msg[0] == "walk":
                    _secs = time.time() - getattr(root, "_plm_t0", time.time())
                    lbl.config(text="ищу файлы: найдено %d%s (%.0f с)"
                               % (msg[1], " — обход готов, читаю изменённое…" if msg[2] else "", _secs))
                elif msg[0] == "prog":
                    _secs = time.time() - getattr(root, "_plm_t0", time.time())
                    lbl.config(text="%d / %d · прочитано %d, пропущено (уже в базе) %d · %.0f с · %s"
                               % (msg[1], msg[2], msg[4], msg[5], _secs, msg[3][:40]))
                else:
                    st = msg[2] if len(msg) > 2 else {}
                    _secs = time.time() - getattr(root, "_plm_t0", time.time())
                    if st.get("busy"):
                        lbl.config(text="Занято: %s" % st["error"])
                    elif st.get("error"):
                        lbl.config(text="скан не удался: %s" % st["error"])
                    else:
                        roots_now = [r for r in roots_of(e_folder.get(), e_folder2.get())
                                     if os.path.isdir(r)]
                        rows = db_rows(roots_now or None, int(settings.get("show_limit") or 50000))
                        total = db_total(roots_now or None)
                        rows_all.clear()
                        tree.delete(*tree.get_children())
                        rows_all.extend(rows)
                        redraw()
                        lbl.config(text="скан базы за %.1f с: новых %d · изменённых %d · "
                                        "пропущено (уже в базе) %d · в базе %d, показано %d · исключено папок %d · "
                                        "убрано строк %d%s"
                                   % (_secs, st.get("new", 0), st.get("mod", 0), st.get("skipped", 0),
                                      total, len(rows), len(exclude_list(settings.get("exclude"))),
                                      st.get("excluded", 0),
                                      "; ОСТАНОВЛЕНО" if st.get("stopped") else ""))
                        log_line("scan: %s -> новых %d, изменённых %d, пропущено %d за %.1f с"
                                 % (" + ".join(roots_now) or "вся база", st.get("new", 0),
                                    st.get("mod", 0), st.get("skipped", 0), _secs))
                    root._plm_scan_active = False
                    try:
                        root._plm_db_stamp = _active_stamp()
                    except Exception:
                        pass
                    btn.config(state="normal")
                    b_stop.config(state="disabled")
                    return
        except queue.Empty:
            pass
        root.after(120, poll_scan)

    def worker(roots, opts):
        import engine as eng
        res = {}

        def pc(n, total):
            q.put(("prog", n, total, "", 0, 0))

        try:
            res = eng.scan_to_base(roots, float(opts.get("max_size_mb") or 8), 3600.0,
                                   (int(e_depth.get() or 0) or None),
                                   progress_cb=pc,
                                   stop_cb=lambda: getattr(root, "_plm_stop", False),
                                   full=bool(opts.get("full")),
                                   recurse=bool(opts.get("recurse", True)),
                                   latest_only=bool(opts.get("latest_only", True)),
                                   param_cfg={"pdes": settings.get("param_designation"),
                                              "pname": settings.get("param_name"),
                                              "pmat": settings.get("param_material")},
                                   exclude=exclude_list(settings.get("exclude"))) or {}
        except Exception as e:
            res = {"error": str(e)}
        q.put(("done", 0, res))

    def go():
        folder = norm_path(e_folder.get())
        if not os.path.isdir(folder):
            messagebox.showwarning(APP_TITLE, "Выберите папку.")
            return
        folder2 = norm_path(e_folder2.get()) if e_folder2.get().strip() else ""
        roots = [r for r in scan_roots(folder, folder2, settings.get("folders")) if os.path.isdir(r)]
        if folder2 and not os.path.isdir(folder2):
            messagebox.showwarning(APP_TITLE, "Папка2 не найдена — скан её пропустит,\n"
                                              "но путь я сохраню:\n%s" % folder2)
        # список путей держим согласным с полями: первые две — Папка1 и Папка2, дальше — из «Путей…»
        rest = [x for x in (settings.get("folders") or [])
                if norm_path(x) not in (folder, folder2)]
        settings["folders"] = ([folder] if folder else []) + ([folder2] if folder2 else []) + rest
        try:
            show_paths()
        except Exception:
            pass
        e_folder.delete(0, "end")
        e_folder.insert(0, folder)
        tree.delete(*tree.get_children())
        rows_all.clear()
        opts = {"max_size_mb": float(e_max.get() or 0), "recurse": var_rec.get(),
                "latest_only": var_lat.get(), "full": var_full.get()}
        btn.config(state="disabled")
        b_stop.config(state="normal")
        root._plm_stop = False
        root._plm_scan_active = True          # пока скан идёт — автообновление не мешает
        root._plm_t0 = time.time()
        _hint = ""
        try:
            import engine as _e
            _roots = json.loads(_e.meta_get("roots") or "null") or []
            if _roots and not any(folder.lower().startswith(r.rstrip("\\").lower()) for r in _roots):
                _hint = "  (папка ВНЕ базы: %s — будет прочитано заново)" % "; ".join(_roots)
        except Exception:
            pass
        lbl.config(text="ищу файлы…" + _hint)
        settings.update({"max_size_mb": opts["max_size_mb"],
                         "recurse": opts["recurse"], "latest_only": opts["latest_only"],
                         "depth": int(e_depth.get() or 0), "purge_keep": int(e_keep.get() or 2),
                         "auto_refresh": var_auto.get(), "full": var_full.get(),
                         "show_limit": max(1000, min(1000000, int(sp_limit.get() or 50000)))})
        save_settings()
        threading.Thread(target=worker, args=(roots, opts), daemon=True).start()
        root.after(120, poll_scan)

    def export():
        if not rows_all:
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="plm_items.csv",
                                         filetypes=[("CSV", "*.csv")])
        if p:
            save_csv(shown or rows_all, p)
            lbl.config(text="выгружено: %s" % os.path.basename(p))

    # --- КОПИРОВАТЬ / ВСТАВИТЬ: Ctrl+C/V/X/A и ПКМ во всех полях и таблицах ---
    # ГРАБЛЯ (V35): НЕЛЬЗЯ вешать bind_all на Ctrl+V и тут же делать event_generate("<<Paste>>") —
    # у полей (Entry/TEntry/Text/Spinbox/Combobox) СВОЙ class-binding на <<Paste>>, а он срабатывает
    # РАНЬШЕ тега "all" (порядок bindtags: виджет → класс → родитель → all). Итог: нативная вставка
    # + наша = ДВЕ вставки подряд (жалоба владельца 02.10.2026, окно «Столбцы и параметры»).
    # Поэтому: если класс виджета умеет событие сам — молча возвращаем "break" и НЕ генерируем.
    _NATIVE = {}

    def _has_native(w, seq):
        """Есть ли у класса виджета собственная обработка виртуального события."""
        try:
            cls = w.winfo_class()
        except Exception:
            return False
        key = (cls, seq)
        if key in _NATIVE:
            return _NATIVE[key]
        ok = False
        try:
            ok = bool(w.tk.call("bind", cls, seq))
        except Exception:
            ok = False
        _NATIVE[key] = ok
        return ok

    def _foc():
        try:
            return root.focus_get()
        except Exception:
            return None

    def _clip_ev(seq, ev=None):
        w = _foc()
        try:
            if w is not None and not _has_native(w, seq):
                w.event_generate(seq)
        except Exception:
            pass
        return "break"

    def _on_copy(ev=None):
        """Копировать ПРЯМО (родной <<Copy>> в русской раскладке не срабатывает)."""
        w = _foc()
        try:
            if isinstance(w, ttk.Treeview):
                txt = "\n".join("\t".join(str(x) for x in w.item(i, "values")) for i in w.selection())
            elif isinstance(w, tk.Text):
                txt = w.get("sel.first", "sel.last")
            elif isinstance(w, (tk.Entry, ttk.Entry)):
                txt = w.selection_get()
            else:
                txt = ""
            if txt:
                root.clipboard_clear()
                root.clipboard_append(txt)
        except Exception:
            pass
        return "break"

    def _on_paste(ev=None):
        """Вставить ПРЯМО из буфера (родной <<Paste>> в русской раскладке не срабатывает)."""
        w = _foc()
        try:
            txt = root.clipboard_get()
        except Exception:
            return "break"
        try:
            if isinstance(w, tk.Text):
                w.insert("insert", txt)
            elif isinstance(w, (tk.Entry, ttk.Entry)):
                w.insert(w.index("insert"), txt)
        except Exception:
            pass
        return "break"

    def _on_cut(ev=None):
        w = _foc()
        _on_copy()
        try:
            if isinstance(w, tk.Text):
                w.delete("sel.first", "sel.last")
            elif isinstance(w, (tk.Entry, ttk.Entry)):
                w.delete("sel.first", "sel.last")
        except Exception:
            pass
        return "break"

    def _sel_all(ev=None):
        w = _foc()
        try:
            if isinstance(w, tk.Text):
                w.tag_add("sel", "1.0", "end-1c")
            elif isinstance(w, (tk.Entry, ttk.Entry)):
                w.selection_range(0, "end")
                w.icursor("end")
            elif isinstance(w, ttk.Treeview):
                w.selection_set(w.get_children())
        except Exception:
            pass
        return "break"

    def _menu_pop(ev):
        w = ev.widget
        try:
            w.focus_set()                      # действия — по ЭТОМУ виджету
        except Exception:
            pass
        m = tk.Menu(root, tearoff=0)
        try:
            m.add_command(label="Копировать", command=_on_copy)
            if not isinstance(w, ttk.Treeview):
                m.add_command(label="Вырезать", command=_on_cut)
                m.add_command(label="Вставить", command=_on_paste)
            m.add_separator()
            m.add_command(label="Выделить всё", command=_sel_all)
            m.tk_popup(ev.x_root, ev.y_root)
        finally:
            m.grab_release()

    def _bind_clip(w):
        try:
            w.bind("<Button-3>", _menu_pop, add="+")
        except Exception:
            pass

    def _bind_clip_all():
        def walk(w):
            for ch in w.winfo_children():
                try:
                    if isinstance(ch, (tk.Entry, ttk.Entry, tk.Text, ttk.Treeview)):
                        _bind_clip(ch)
                except Exception:
                    pass
                walk(ch)
        try:
            walk(root)
        except Exception:
            pass

    # Ctrl+C/V/X/A в ЛЮБОЙ раскладке. В кириллице keysym другой, поэтому <Control-c>
    # не срабатывает; ориентируемся на ФИЗИЧЕСКУЮ клавишу (keycode=VK: C=67, V=86, X=88, A=65)
    # плюс запасной вариант по keysym (латиница и кириллица).
    def _clip_ctrl(ev):
        # ЛАТИНСКАЯ раскладка: у полей (Entry/TEntry/Text/Spinbox/Combobox) ЕСТЬ нативный
        # `<<Copy/Paste/Cut/SelectAll>>` (проверено `bind <класс> <<Paste>>`), и он срабатывает
        # РАНЬШЕ тега "all" (порядок виджет→класс→родитель→all). Поэтому НЕ дублируем: отдаём полю.
        # Нет нативного (Treeview) — делаем сами. КИРИЛЛИЦА/прочая раскладка: нативного нет вовсе →
        # делаем сами по ФИЗИЧЕСКОЙ клавише (keycode: C=67, V=86, X=88, A=65 — не зависит от раскладки).
        w = _foc()
        kc = getattr(ev, "keycode", None)
        ks = (getattr(ev, "keysym", "") or "").lower()
        latin = {"c": ("<<Copy>>", _on_copy), "v": ("<<Paste>>", _on_paste),
                 "x": ("<<Cut>>", _on_cut), "a": ("<<SelectAll>>", _sel_all)}
        if ks in latin:
            seq, fn = latin[ks]
            if w is not None and _has_native(w, seq):
                return "break"            # поле обработает само — ДВОЙНОЙ вставки не будет
            return fn(ev)
        if kc == 67:
            return _on_copy(ev)
        if kc == 86:
            return _on_paste(ev)
        if kc == 88:
            return _on_cut(ev)
        if kc == 65:
            return _sel_all(ev)

    # 07.10.2026: буквенные Ctrl-привязки УБРАНЫ — их дублировал общий `_clip_ctrl` (плюс нативный
    # класс-бантинг полей) → ДВОЙНАЯ вставка Ctrl+V. Остаются только Insert-варианты (их `_clip_ctrl`
    # не трогает — другой keycode) + единый разбор `_clip_ctrl` ниже.
    for _seq, _fn in (
        ("<Control-Insert>", _on_copy), ("<Shift-Insert>", _on_paste),
    ):
        try:
            root.bind_all(_seq, _fn)
        except Exception:
            pass
    root.bind_all("<Control-KeyPress>", _clip_ctrl, add="+")
    root.after(700, _bind_clip_all)                 # ПКМ-меню в существующих полях

    def _offer_archive_cleanup():
        """САМОПЕРЕСТРОЙКА: если в базе остался тяжёлый архивный сырой импорт — предложить убрать.
        Размеры/история (arch_dims/arch_dim_ch) и текущее состояние НЕ трогаем."""
        try:
            info = eng.cleanup_archive_tables(do=False)
        except Exception:
            return
        n = info.get("rows") or 0
        if not n:
            return

        def ask():
            rus = lambda x: "{:,}".format(int(x)).replace(",", " ")
            if messagebox.askyesno(
                    "Уборка архива",
                    "В базе %s лишних архивных строк (сырой импорт срезов).\n\n"
                    "Убрать? База уменьшится в разы. Размеры/история и ТЕКУЩЕЕ состояние "
                    "изделий останутся." % rus(n)):
                def work():
                    res = eng.cleanup_archive_tables(do=True)
                    tail = ("\n(сжатие файла не прошло: %s)" % res.get("vacuum_error")
                            ) if res.get("vacuum_error") else ""
                    root.after(0, lambda: messagebox.showinfo(
                        "Уборка архива",
                        "Убрано таблиц: %d, строк: %s.%s"
                        % (len(res.get("dropped", [])), rus(res.get("rows", 0)), tail)))
                threading.Thread(target=work, daemon=True).start()

        try:
            root.after(0, ask)
        except Exception:
            pass

    root.after(1200, _offer_archive_cleanup)

    btn.config(command=go)
    _bs = db_summary()
    log_line("base: изделий %d, файлов с копиями версий %d, связей %d, папок %d, изменений %d"
             % (_bs.get("models", 0), _bs.get("files", 0), _bs.get("links", 0),
                _bs.get("folders", 0), _bs.get("changes", 0)))
    if _bs.get("files"):
        # V35: цифры по-человечески — главная = ИЗДЕЛИЯ (без дублей .1/.2), рядом файлы с копиями версий
        # 07.10.2026: если правила разбора новее базы — ПРЯМО ГОВОРИМ, что нужен полный скан
        _tag_note = "   ⚠ ПРАВИЛА РАЗБОРА ИЗМЕНИЛИСЬ — нужен СКАН (перечитает все файлы)"
        try:
            _tag_note = _tag_note if eng.parser_tag_changed() else ""
        except Exception:
            _tag_note = ""
        lbl.config(text="база: изделий %d (файлов с копиями версий %d) · изменений %d — читаю из базы…%s"
                   % (_bs.get("models", 0), _bs.get("files", 0), _bs.get("changes", 0), _tag_note))
        load_base()
        root._plm_db_stamp = _active_stamp()
        check_base()
        root.after(500, live_auto)         # нижнее дерево ПЛМ строится само при открытии

    root.after(15000, watch_db)            # автообновление: если базу обновил другой ПК

    # 07.10.2026 (V54): НАСТРОЙКИ — СЛЕВА (узкая прокручиваемая колонка), статус — ВНИЗУ,
    # основное поле — ПОПОЛАМ справа (верх: список изделий, низ: детали)
    try:
        for _w in (top, data, vpan, lhost):
            _w.pack_forget()
        data.pack(side="bottom", fill="x", padx=6, pady=(0, 6))    # самый низ — строка состояния
        lhost.pack(side="left", fill="y", padx=(6, 0), pady=6)     # слева — настройки и кнопки
        vpan.pack(side="left", fill="both", expand=True, padx=6, pady=(0, 6))   # справа — два окна
    except Exception:
        pass

    try:                                   # окно не «прыгает» при переключении вкладок
        root.update_idletasks()
        root.geometry("1520x900")          # слева панель настроек, справа два окна пополам
        _half_try()                        # разделитель — в половину (с повторами, пока не разложится)
    except Exception:
        pass
    try:                                   # тихая проверка обновлений при старте (есть — предложит)
        root.after(2500, lambda: check_updates_ui(False))
    except Exception:
        pass
    root.mainloop()
