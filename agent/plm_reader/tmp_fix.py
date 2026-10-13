# -*- coding: utf-8 -*-
"""РћРєРЅРѕ PLM Reader (РІС‹РЅРµСЃРµРЅРѕ РёР· plm_reader.py СЂР°СЃРїРёР»РѕРј; СЃРј. РЎРџР•РљРђ_Р РђРЎРџРР›Рђ_PLM_READER.md).

Р’РµСЃСЊ РёРЅС‚РµСЂС„РµР№СЃ: РїР°РЅРµР»Рё, РІРєР»Р°РґРєРё, РґРµСЂРµРІСЊСЏ, РјРµРЅСЋ, Р±СѓС„РµСЂ, СЃР°РјРѕРїСЂРѕРІРµСЂРєР°, РѕР±РЅРѕРІР»РµРЅРёРµ.
Р’С‹Р·РѕРІ: plm_reader.main() -> from plm_toolwin import run_gui (Р»РµРЅРёРІС‹Р№ РёРјРїРѕСЂС‚, Р±РµР· С†РёРєР»Р°).

Р’РќРРњРђРќРР•: СЌС‚Рѕ РћР”РќРђ Р±РѕР»СЊС€Р°СЏ С„СѓРЅРєС†РёСЏ run_gui() СЃРѕ ~110 Р’Р›РћР–Р•РќРќР«РњР С„СѓРЅРєС†РёСЏРјРё, Р¶РёРІСѓС‰РёРјРё РІ РѕР±С‰РёС…
Р»РѕРєР°Р»СЊРЅС‹С… (root, tk, ttk, settings, РІРёРґР¶РµС‚С‹, _ROWS, _last, cols, shownвЂ¦). РџСЂР°РІРєРё вЂ” РїРѕ СЏРєРѕСЂСЋ
`def <РёРјСЏ>`; СЂРµС„Р°РєС‚РѕСЂРёС‚СЊ РІ РєР»Р°СЃСЃ/РјРёРєСЃРёРЅС‹ вЂ” РѕС‚РґРµР»СЊРЅР°СЏ Р·Р°РґР°С‡Р° (СЃРїРµРєР° В§8).

РљРђР РўРђ Р’Р›РћР–Р•РќРќР«РҐ Р¤РЈРќРљР¦РР™ (РїРѕСЂСЏРґРѕРє = РїРѕСЂСЏРґРѕРє РІ С„Р°Р№Р»Рµ; РёС‰Рё РїРѕ `    def <РёРјСЏ>`):
* РѕРєРЅРѕ/РїР°РЅРµР»СЊ/СЃС‚Р°С‚СѓСЃ: _lwheel, _paths_text, show_paths, pull_paths, open_paths, limit_changed, _row,
  _auto_changed, stop_scan, _vgrid, _upd_status, _apply_update, check_updates_ui, show_facts,
  _copy_status, _status_menu, _wrap_data, _half_sash, _half_try
* РџСЂРѕРІРѕРґРЅРёРє (РІРµСЂС…): _e_short, _expl_root_paths, _expl_data, _expl_node, _expl_file_row, _expl_more,
  _expl_fill, fill_explorer, _expl_dbl
* Р”РµСЂРµРІРѕ/С‚Р°Р±Р»РёС†Р° (РІРµСЂС…): debounce, _short, _file_row, node_add, _vals9, _fill_node, _model_values,
  _kind, _resolve, node_add_model, on_open, _dbl_click, fill_tree_view, expand_all, row_uid, make_tree
* РёРЅСЃС‚СЂСѓРјРµРЅС‚С‹ СЂСЏРґР°: purge_folder, _text_window, purge_show, purge_run, _lout, say, cap, _sel_model,
  where_selected, tree_down, tree_up, changes_selected, open_detail, lt_apply, _fmt, export_bom (СЃРѕСЃС‚Р°РІв†’CSV)
* РќРР–РќР•Р• РѕРєРЅРѕ (РІРєР»Р°РґРєРё): _prop_show, _live_vals, _branch_updown, _ltv_model, ltv_open, _plm_data_ref,
  live_auto, _prod_show (Р РѕРґРѕСЃР»РѕРІРЅР°СЏ), _links_show + _fill_up + ltv2_open (РЎРІСЏР·Рё), _made_window,
  _text_tree_show (РўРµРєСЃС‚), _hist_show (РСЃС‚РѕСЂРёСЏ), _overview_text + _overview_show (РћР±Р·РѕСЂ вЂ” СЃРІРѕРґРєР° Р±Р°Р·С‹),
  _graph_data + _graph_layout + _graph_show (Р“СЂР°С„ вЂ” РєР°СЂС‚Р° РЅР° canvas), _bottom_render, _bottom_show (pick=),
  _goto_model + _goto_node (РґРІРѕР№РЅРѕР№ РєР»РёРє = РїРµСЂРµР№С‚Рё РЅР° РґРµС‚Р°Р»СЊ), _return_to_pick (РєРЅРѕРїРєР° В«РІРµСЂРЅСѓС‚СЊСЃСЏВ»),
  _nav_record/_nav_state/_nav_back/_nav_fwd (в†ђ в†’ РёСЃС‚РѕСЂРёСЏ), _goto_entry (РїРѕР»Рµ В«РїРµСЂРµР№С‚Рё Рє РјРѕРґРµР»РёВ»),
  live_tree, expl_live, tree_live, on_tab
* С‚Р°Р±Р»РёС†Р°/СЃРѕСЂС‚/Р±Р°Р·Р°: sort_key, set_sort, redraw, rebuild_tree, show_readme, check_base, show_check,
  load_base, _active_stamp, refresh_from_db, watch_db, save_settings, save_ui, on_close
* РѕРєРЅР° РёСЃС‚РѕСЂРёРё/СЃРєР°РЅ: split_list, choose_columns, hist_settings, show_history, show_folder_history,
  poll_scan, worker, go, export + _bom_rows/export_bom (СЃРѕСЃС‚Р°РІв†’CSV), _offer_archive_cleanup
* РљРћРџРР РћР’РђРўР¬/РџРљРњ (РІ РєРѕРЅС†Рµ С„Р°Р№Р»Р°): _has_native, _foc, _clip_ev, _on_copy, _on_paste, _on_cut, _sel_all,
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

    settings = load_settings_file()                     # Р±РёС‚С‹Р№/С‡СѓР¶РѕР№ С„Р°Р№Р» РЅРµ СЂРѕРЅСЏРµС‚ РѕРєРЅРѕ
    import engine as _eng_start                      # РґРІРёР¶РѕРє РЅСѓР¶РµРЅ Р”Рћ РїРµСЂРІРѕРіРѕ С‡С‚РµРЅРёСЏ Р±Р°Р·С‹
    _db_dir, _db_mirrors = apply_db_paths(settings, _eng_start)   # Р±Р°Р·Р° РјРѕР¶РµС‚ Р¶РёС‚СЊ РЅР° РґСЂСѓРіРѕРј РґРёСЃРєРµ
    if settings.get("db_dir") or settings.get("db_mirror"):
        log_line("Р±Р°Р·Р°: РїР°РїРєР° %s В· Р·РµСЂРєР°Р»: %s"
                 % (_db_dir, ", ".join(_db_mirrors) if _db_mirrors else "РЅРµС‚"))
    _cols = settings.get("columns")                     # РЅРѕРІС‹Рµ РєРѕР»РѕРЅРєРё РґР°С‚ вЂ” Рё РґР»СЏ СЃС‚Р°СЂС‹С… РЅР°СЃС‚СЂРѕРµРє
    if isinstance(_cols, list):
        _off = 0
        for _c in ("РЎРѕР·РґР°РЅ", "РР·РјРµРЅС‘РЅ"):
            if _c not in _cols:
                _i = (_cols.index("Р”Р°С‚Р°") + 1 + _off) if "Р”Р°С‚Р°" in _cols else len(_cols)
                _cols.insert(_i, _c)
                _off += 1

    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("1520x900")         # 07.10.2026: РЅР°СЃС‚СЂРѕР№РєРё РЎР›Р•Р’Рђ + РѕСЃРЅРѕРІРЅРѕРµ РїРѕР»Рµ РїРѕРїРѕР»Р°Рј
    root.minsize(980, 620)            # РїР°РЅРµР»СЊ СЃР»РµРІР° + РґРІР° РѕРєРЅР° РІРёРґРЅРѕ Рё РІ РЅРµР±РѕР»СЊС€РѕРј РѕРєРЅРµ

    # 07.10.2026: РќРђРЎРўР РћР™РљР Р РљРќРћРџРљР вЂ” Р’ Р›Р•Р’РћР™ РљРћР›РћРќРљР• (СѓР·РєР°СЏ РєРѕР»РѕРЅРєР° РџР РћРљР РЈР§РР’РђР•РўРЎРЇ,
    # РїРѕСЌС‚РѕРјСѓ РЅР°СЃС‚СЂРѕР№РєРё РЅРµ В«СЃСЂС‹РІР°СЋС‚СЃСЏВ» Р·Р° РєСЂР°Р№ РїСЂРё РєРѕСЂРѕС‚РєРѕРј РѕРєРЅРµ)
    lhost = ttk.Frame(root, width=330)
    lhost.pack_propagate(False)            # РєРѕР»РѕРЅРєР° РґРµСЂР¶РёС‚ СЃРІРѕСЋ С€РёСЂРёРЅСѓ
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

    top = ttk.Frame(lcanv, padding=2)      # РїР°РЅРµР»СЊ РЅР°СЃС‚СЂРѕРµРє Р¶РёРІС‘С‚ Р’ РљРђРќР’Р• (РїСЂРѕРєСЂСѓС‚РєР° РєРѕР»РµСЃРѕРј)
    lcanv.create_window((0, 0), window=top, anchor="nw")
    top.bind("<Configure>", lambda e: lcanv.configure(scrollregion=lcanv.bbox("all")))
    for _lw in (lcanv, top):
        _lw.bind("<MouseWheel>", _lwheel)
    row1 = ttk.Frame(top)                  # РіСЂСѓРїРїС‹ 1 (РЎР’Р•Р РҐРЈ Р’РќРР—): РџРђРџРљР В· РЎРљРђРќ В· РџРћРљРђР—
    row1.pack(fill="x")
    row2 = ttk.Frame(top)                  # РіСЂСѓРїРїС‹ 2: Purge В· РЎРљРђРќРР РћР’РђРќРР• В· РРќРЎРўР РЈРњР•РќРўР«
    row2.pack(fill="x")
    grp_paths = ttk.LabelFrame(row1, text=" РџРђРџРљР ", padding=8)
    grp_paths.pack(fill="x", pady=(0, 6))
    grp_scan = ttk.LabelFrame(row1, text=" РЎРљРђРќ ", padding=8)
    grp_scan.pack(fill="x", pady=(0, 6))
    grp_show = ttk.LabelFrame(row1, text=" РџРћРљРђР— ", padding=8)
    grp_show.pack(fill="x", pady=(0, 6))
    grp_purge = ttk.LabelFrame(row2, text=" Purge вЂ” СЃС‚Р°СЂС‹Рµ РІРµСЂСЃРёРё РІ Р±СЌРєР°Рї, СѓРґР°Р»РµРЅРёСЏ РЅРµС‚ ", padding=8)
    grp_purge.pack(fill="x", pady=(0, 6))
    grp_do = ttk.LabelFrame(row2, text=" РЎРљРђРќРР РћР’РђРќРР• ", padding=8)
    grp_do.pack(fill="x", pady=(0, 6))
    grp_tools = ttk.LabelFrame(row2, text=" РРќРЎРўР РЈРњР•РќРўР« ", padding=8)
    grp_tools.pack(fill="x", pady=(0, 6))
    spath = grp_paths                      # РїР°РЅРµР»СЊ РїСѓС‚РµР№ Р¶РёРІС‘С‚ РІ РіСЂСѓРїРїРµ В«РџРђРџРљРВ»
    _hidden = ttk.Frame(top)               # РЅРµРІРёРґРёРјС‹Р№ РґРµСЂР¶Р°С‚РµР»СЊ (СЃРѕРІРјРµСЃС‚РёРјРѕСЃС‚СЊ СЂР°Р·РјРµС‚РєРё)
    class _Field:
        """РџРѕР»Рµ-РїСѓС‚СЊ Р‘Р•Р— РІРёРґР¶РµС‚Р°: РІРІРѕРґ РїСѓС‚РµР№ Р¶РёРІС‘С‚ РІ РѕРєРЅРµ В«РџСѓС‚Рё Рё РёСЃРєР»СЋС‡РµРЅРёСЏвЂ¦В», С‚СѓС‚ С‚РѕР»СЊРєРѕ Р·РЅР°С‡РµРЅРёРµ."""

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
        """Р’СЃРµ РїСѓС‚Рё РЎР›РРўРќРћ С‡РµСЂРµР· Р·Р°РїСЏС‚СѓСЋ; РµСЃР»Рё РґР»РёРЅРЅРѕ вЂ” РѕР±СЂРµР·РєР° СЃ В«вЂ¦В» (РЅРµ Р±РѕР»СЊС€Рµ 2 СЃС‚СЂРѕРє)."""
        if not items:
            return "вЂ”"
        joined = ", ".join(items)
        if len(joined) > max_chars:
            return joined[:max_chars - 1] + "вЂ¦"
        return joined

    def show_paths():
        """Р§С‚Рѕ РЅР°СЃС‚СЂРѕРµРЅРѕ: РїР°РїРєРё СЃРєР°РЅР° Рё РёСЃРєР»СЋС‡РµРЅРёСЏ вЂ” СЃР»РёС‚РЅРѕ С‡РµСЂРµР· Р·Р°РїСЏС‚СѓСЋ, РјР°РєСЃРёРјСѓРј РІ 2 СЃС‚СЂРѕРєРё."""
        flds = scan_roots(e_folder.get(), e_folder2.get(), settings.get("folders"))
        exc = exclude_list(settings.get("exclude"))
        lbl_p.config(text="РџР°РїРѕРє СЃРєР°РЅР°: %d. %s" % (len(flds), _paths_text(flds)))
        lbl_e.config(text="РСЃРєР»СЋС‡РµРЅРѕ: %d. %s" % (len(exc), _paths_text(exc)))

    def pull_paths():
        """РџРѕСЃР»Рµ РѕРєРЅР° В«РџСѓС‚Рё Рё РёСЃРєР»СЋС‡РµРЅРёСЏвЂ¦В»: Р·РЅР°С‡РµРЅРёСЏ вЂ” РІ РїРѕР»СЏ-РґРµСЂР¶Р°С‚РµР»Рё, РїРѕРґРїРёСЃРё вЂ” РЅР° РїР°РЅРµР»СЊ."""
        flds = settings.get("folders") or []
        e_folder.v = flds[0] if flds else ""
        e_folder2.v = flds[1] if len(flds) > 1 else ""
        show_paths()

    def open_paths():
        PathsWindow(root, settings, tk, ttk, filedialog, on_save=pull_paths)

    btn_paths = ttk.Button(spath, text="РџСѓС‚Рё Рё РёСЃРєР»СЋС‡РµРЅРёСЏвЂ¦", command=open_paths, width=26)
    btn_paths.grid(row=0, column=0, sticky="w")
    lim = ttk.Frame(grp_show)
    lim.pack(fill="x")
    ttk.Label(lim, text="СЃС‚СЂРѕРє РІ С‚Р°Р±Р»РёС†Рµ Рё РІ С„РёР»СЊС‚СЂРµ:").pack(side="left")
    sp_limit = ttk.Spinbox(lim, from_=1000, to=1000000, increment=5000, width=9)
    sp_limit.set(int(settings.get("show_limit") or 50000))
    sp_limit.pack(side="left", padx=4)
    ttk.Label(grp_show, text="(СЃС‚РѕР»СЊРєРѕ Р¶Рµ СЃС‚СЂРѕРє РѕС‚РґР°С‘С‚ РїРѕРёСЃРє РїРѕ С„РёР»СЊС‚СЂСѓ)", foreground="#666").pack(anchor="w")

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
        """РЎС‚СЂРѕРєР° В«РїРѕРґРїРёСЃСЊ + РїРѕР»РµВ» РІРЅСѓС‚СЂРё РіСЂСѓРїРїС‹."""
        f = ttk.Frame(parent)
        f.pack(fill="x", pady=1)
        ttk.Label(f, text=label).pack(side="left")
        e = ttk.Entry(f, width=width)
        e.pack(side="left", padx=4)
        return e

    e_depth = _row(grp_scan, "Р“Р»СѓР±РёРЅР° РїР°РїРѕРє (0 = РІСЃРµ):", 5)
    e_depth.delete(0, "end")
    e_depth.insert(0, str(settings.get("depth", 0)))
    e_max = _row(grp_scan, "РџСЂРѕРїСѓСЃРєР°С‚СЊ С„Р°Р№Р»С‹ > РњР‘:", 5)
    e_max.delete(0, "end")
    e_max.insert(0, str(settings.get("max_size_mb", 24)))
    var_rec = tk.BooleanVar(value=settings.get("recurse", True))
    ttk.Checkbutton(grp_scan, text="СЃ РїРѕРґРїР°РїРєР°РјРё", variable=var_rec).pack(anchor="w")
    var_lat = tk.BooleanVar(value=settings.get("latest_only", True))
    ttk.Checkbutton(grp_scan, text="С‚РѕР»СЊРєРѕ РїРѕСЃР»РµРґРЅРёРµ РІРµСЂСЃРёРё", variable=var_lat).pack(anchor="w")

    e_keep = _row(grp_purge, "РѕСЃС‚Р°РІРёС‚СЊ РІРµСЂСЃРёР№:", 4)
    e_keep.delete(0, "end")
    e_keep.insert(0, str(settings.get("purge_keep", 2)))
    ttk.Label(grp_purge, text="РџР›РђРќ вЂ” С‡С‚Рѕ СѓР№РґС‘С‚; В«РІ Р±СЌРєР°РїВ» вЂ” РїРµСЂРµРЅРµСЃС‚Рё",
              foreground="#666").pack(anchor="w", pady=(2, 3))
    b_purge_plan = ttk.Button(grp_purge, text="Purge: РџР›РђРќ", width=20,
                              command=lambda: purge_show())
    b_purge_plan.pack(anchor="w", pady=1)
    b_purge_run = ttk.Button(grp_purge, text="Purge: РІ Р±СЌРєР°РївЂ¦", width=20,
                             command=lambda: purge_run())
    b_purge_run.pack(anchor="w", pady=1)

    def _auto_changed():
        try:
            settings["auto_refresh"] = bool(var_auto.get())
            save_settings()
        except Exception:
            pass

    var_auto = tk.BooleanVar(value=settings.get("auto_refresh", True))
    ttk.Checkbutton(grp_show, text="Р°РІС‚РѕРѕР±РЅРѕРІР»РµРЅРёРµ", variable=var_auto,
                    command=_auto_changed).pack(anchor="w", pady=(4, 0))
    var_full = tk.BooleanVar(value=settings.get("full", False))
    ttk.Checkbutton(grp_show, text="РїРµСЂРµС‡РёС‚Р°С‚СЊ РІСЃС‘", variable=var_full).pack(anchor="w")

    btn = ttk.Button(grp_do, text="РЎРєР°РЅРёСЂРѕРІР°С‚СЊ", width=18)
    btn.pack(anchor="w", pady=1)

    def stop_scan():
        root._plm_stop = True
        lbl.config(text="РѕСЃС‚Р°РЅР°РІР»РёРІР°СЋвЂ¦")

    b_stop = ttk.Button(grp_do, text="РЎС‚РѕРї", command=stop_scan, state="disabled", width=18)
    b_stop.pack(anchor="w", pady=1)
    b_check = ttk.Button(grp_do, text="РђРєС‚СѓР°Р»СЊРЅРѕ?", width=18, command=lambda: check_base())
    b_check.pack(anchor="w", pady=1)

    def _vgrid(parent, items, per_col=4, width=18):
        """РљРЅРѕРїРєРё Р’Р•Р РўРРљРђР›Р¬РќРћ: РЅРµ Р±РѕР»СЊС€Рµ per_col РІ СЃС‚РѕР»Р±РёРє, РґР°Р»СЊС€Рµ вЂ” СЃР»РµРґСѓСЋС‰РёР№ СЃС‚РѕР»Р±РµС† РїСЂР°РІРµРµ.
        per_col=4 РїСЂРё 7 РєРЅРѕРїРєР°С… РґР°С‘С‚ Р РћР’РќРћ 2 СЃС‚РѕР»Р±С†Р° = 2 РёРЅСЃС‚СЂСѓРјРµРЅС‚Р° Р’ РЎРўР РћРљРЈ вЂ” РІР»РµР·Р°РµС‚ РІ СѓР·РєСѓСЋ РїР°РЅРµР»СЊ."""
        for i, (text, cmd) in enumerate(items):
            col, row = divmod(i, per_col)
            ttk.Button(parent, text=text, width=width, command=cmd).grid(
                row=row, column=col, sticky="ew", padx=(0 if col == 0 else 8, 0), pady=1)

    _vgrid(grp_tools, [
        ("РСЃС‚РѕСЂРёСЏ РІС‹Р±СЂР°РЅРЅРѕРіРѕ", lambda: show_history()),
        ("РСЃС‚РѕСЂРёСЏ РїРѕ РїР°РїРєРµ", lambda: show_folder_history()),
        ("РЎС‚РѕР»Р±С†С‹ Рё РїР°СЂР°РјРµС‚СЂС‹вЂ¦", lambda: choose_columns()),
        ("Р’С‹РіСЂСѓР·РёС‚СЊ РІ CSV", lambda: export()),
        ("README", lambda: show_readme()),
        ("РџСЂРѕРІРµСЂРёС‚СЊ РѕР±РЅРѕРІР»РµРЅРёРµ", lambda: check_updates_ui(True)),
        ("Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅРѕ", lambda: show_facts()),
        ("РЎРѕСЃС‚Р°РІ РІ CSV", lambda: export_bom()),   # V83: BOM С‚РµРєСѓС‰РµРіРѕ РёР·РґРµР»РёСЏ РЅРёР¶РЅРµРіРѕ РѕРєРЅР°
    ], per_col=4)
    def _upd_status(text):
        try:
            root.after(0, lambda: lbl.config(text=text))
        except Exception:
            pass

    def _apply_update(files, remote):
        def work():
            _upd_status("РѕР±РЅРѕРІР»РµРЅРёРµ: РєР°С‡Р°СЋ С„Р°Р№Р»С‹вЂ¦")
            res = eng.sync_by_manifest(files)
            if res.get("ok"):
                warns = res.get("warnings") or []
                note = ("\n\nРџСЂРёРјРµС‡Р°РЅРёРµ: Сѓ С‡Р°СЃС‚Рё С„Р°Р№Р»РѕРІ SHA РЅРµ СЃРѕРІРїР°Р» СЃ РјР°РЅРёС„РµСЃС‚РѕРј (РјР°РЅРёС„РµСЃС‚ "
                        "РѕС‚СЃС‚Р°Р» РѕС‚ РєРѕРґР°) вЂ” РѕРЅРё РІСЃС‘ СЂР°РІРЅРѕ СѓСЃС‚Р°РЅРѕРІР»РµРЅС‹: %s. Р­С‚Рѕ РЅРµ РѕС€РёР±РєР°."
                        % ", ".join(warns)) if warns else ""
                _upd_status("РѕР±РЅРѕРІР»РµРЅРѕ РґРѕ %s вЂ” РїРµСЂРµР·Р°РїСѓСЃС‚РёС‚Рµ РїСЂРѕРіСЂР°РјРјСѓ" % remote)
                root.after(0, lambda: messagebox.showinfo(
                    "РћР±РЅРѕРІР»РµРЅРёРµ",
                    "РћР±РЅРѕРІР»РµРЅРѕ РґРѕ %s.\nР¤Р°Р№Р»РѕРІ: %d, СѓСЃС‚Р°СЂРµРІС€РёС… СѓР±СЂР°РЅРѕ: %d.%s\n\n"
                    "РџРµСЂРµР·Р°РїСѓСЃС‚РёС‚Рµ РїСЂРѕРіСЂР°РјРјСѓ." % (remote, len(res.get("updated", [])),
                                                  len(res.get("obsolete", [])), note)))
            else:
                _upd_status("РѕР±РЅРѕРІР»РµРЅРёРµ РЅРµ СѓРґР°Р»РѕСЃСЊ: %s" % res.get("error"))
                root.after(0, lambda: messagebox.showwarning(
                    "РћР±РЅРѕРІР»РµРЅРёРµ", "РќРµ СѓРґР°Р»РѕСЃСЊ: %s" % res.get("error")))
        threading.Thread(target=work, daemon=True).start()

    def check_updates_ui(manual=False):
        def work():
            _upd_status("РїСЂРѕРІРµСЂСЏСЋ РѕР±РЅРѕРІР»РµРЅРёСЏвЂ¦")
            r = eng.check_updates()
            if not r.get("ok"):
                _upd_status("РїСЂРѕРІРµСЂРєР° РѕР±РЅРѕРІР»РµРЅРёР№: %s" % r.get("error"))
                if manual:
                    root.after(0, lambda: messagebox.showwarning(
                        "РћР±РЅРѕРІР»РµРЅРёРµ", "РќРµ СѓРґР°Р»РѕСЃСЊ РїСЂРѕРІРµСЂРёС‚СЊ: %s" % r.get("error")))
                return
            if r.get("available"):
                _upd_status("РµСЃС‚СЊ РѕР±РЅРѕРІР»РµРЅРёРµ: %s" % r.get("remote"))
                msg = ("Р”РѕСЃС‚СѓРїРЅР° РІРµСЂСЃРёСЏ %s (Сѓ РІР°СЃ %s).\n\n%s\n\nРћР±РЅРѕРІРёС‚СЊ СЃРµР№С‡Р°СЃ?"
                       % (r.get("remote"), r.get("local"), r.get("notes") or ""))
                def ask():
                    if messagebox.askyesno("Р•СЃС‚СЊ РѕР±РЅРѕРІР»РµРЅРёРµ", msg):
                        _apply_update(r.get("files") or {}, r.get("remote"))
                root.after(0, ask)
            else:
                _upd_status("РѕР±РЅРѕРІР»РµРЅРёР№ РЅРµС‚ (РІРµСЂСЃРёСЏ %s)" % r.get("local"))
                if manual:
                    root.after(0, lambda: messagebox.showinfo(
                        "РћР±РЅРѕРІР»РµРЅРёРµ", "РЈ РІР°СЃ РїРѕСЃР»РµРґРЅСЏСЏ РІРµСЂСЃРёСЏ: %s" % r.get("local")))
        threading.Thread(target=work, daemon=True).start()

    def show_facts():
        """РћРєРЅРѕ В«Р”РѕРїРѕР»РЅРёС‚РµР»СЊРЅРѕВ»: РёРЅС‚РµСЂРµСЃРЅС‹Рµ С„Р°РєС‚С‹ РїРѕ Р°РєС‚РёРІРЅРѕР№ Р±Р°Р·Рµ (СЂР°СЃС‡С‘С‚ РІ С„РѕРЅРµ)."""
        win = tk.Toplevel(root)
        win.title("PLM Reader вЂ” РґРѕРїРѕР»РЅРёС‚РµР»СЊРЅРѕ (РёРЅС‚РµСЂРµСЃРЅС‹Рµ С„Р°РєС‚С‹ РїРѕ Р±Р°Р·Рµ)")
        win.geometry("660x470")
        win.transient(root)
        head = ttk.Label(win, text="СЃС‡РёС‚Р°СЋвЂ¦", padding=8)
        head.pack(anchor="w")
        tv = ttk.Treeview(win, columns=("k", "v"), show="headings", height=16)
        tv.heading("k", text="РџРѕРєР°Р·Р°С‚РµР»СЊ")
        tv.heading("v", text="Р—РЅР°С‡РµРЅРёРµ")
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
                    head.config(text="РРЅС‚РµСЂРµСЃРЅС‹Рµ С„Р°РєС‚С‹ РїРѕ Р°РєС‚РёРІРЅРѕР№ Р±Р°Р·Рµ")
                    warn.config(text=wrn)
                except Exception:
                    pass
            root.after(0, done)

        threading.Thread(target=work, daemon=True).start()
        ttk.Button(win, text="РџРµСЂРµСЃС‡РёС‚Р°С‚СЊ",
                   command=lambda: threading.Thread(target=work, daemon=True).start()).pack(pady=6)
        ttk.Button(win, text="Р—Р°РєСЂС‹С‚СЊ", command=win.destroy).pack(pady=(0, 8))



    data = ttk.Frame(root, padding=6)
    data.pack(side="bottom", fill="x", padx=6, pady=(0, 4))    # РїРѕР»РѕСЃР° СЃС‚Р°С‚СѓСЃР° вЂ” Р’РќРР—РЈ РѕРєРЅР°

    vpan = ttk.PanedWindow(root, orient="vertical")   # Р’Р•Р РҐ (РѕРєРЅРѕ) / РќРР— (РґРµСЂРµРІСЊСЏ) вЂ” СЂР°Р·РґРµР»РёС‚РµР»СЊ С‚СЏРЅРµС‚СЃСЏ

    def _copy_status():
        """РЎРєРѕРїРёСЂРѕРІР°С‚СЊ РЅРёР¶РЅСЋСЋ СЃС‚СЂРѕРєСѓ РІ Р±СѓС„РµСЂ (СѓРґРѕР±РЅРѕ РїРµСЂРµСЃР»Р°С‚СЊ РѕС€РёР±РєСѓ С†РµР»РёРєРѕРј)."""
        try:
            txt = lbl.cget("text")
            root.clipboard_clear()
            root.clipboard_append(str(txt))
            lbl.config(text="вњ“ СЃС‚СЂРѕРєСѓ СЃРєРѕРїРёСЂРѕРІР°РЅРѕ вЂ” РІСЃС‚Р°РІСЊ РІ С‡Р°С‚/РїРёСЃСЊРјРѕ (Ctrl+V)")
            root.after(1500, lambda: lbl.config(text=txt))
        except Exception:
            pass

    btn_copy = ttk.Button(data, text="РљРѕРїРёСЂРѕРІР°С‚СЊ", width=12, command=_copy_status)
    btn_copy.pack(side="right", padx=(6, 0))
    lbl = ttk.Label(data, text="РіРѕС‚РѕРІ", anchor="w", justify="left")
    lbl.pack(side="left", fill="x", expand=True)

    # РќРР–РќРЇРЇ РџРћР›РћРЎРђ (РґРµСЂРµРІРѕ РїСЂРѕРёР·РІРѕРґСЃС‚РІР°) вЂ” РїСЂРёР¶Р°С‚Р° Рє РЅРёР·Сѓ РѕРєРЅР°, РІРёРґРЅР° РЅР° Р›Р®Р‘РћР™ РІРєР»Р°РґРєРµ
    lpane = ttk.Frame(vpan)
    # lpane РґРѕР±Р°РІР»СЏРµРј РІ СЂР°Р·РґРµР»РёС‚РµР»СЊ РџРћРЎР›Р• nb (РЅРёР¶Рµ) вЂ” РёРЅР°С‡Рµ РІРµСЂС…/РЅРёР· РїРѕРјРµРЅСЏСЋС‚СЃСЏ РјРµСЃС‚Р°РјРё

    def _status_menu(event):
        m = tk.Menu(root, tearoff=0)
        m.add_command(label="РљРѕРїРёСЂРѕРІР°С‚СЊ СЃС‚СЂРѕРєСѓ", command=_copy_status)
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()

    lbl.bind("<Button-3>", _status_menu)          # РџРљРњ РїРѕ СЃС‚СЂРѕРєРµ = РјРµРЅСЋ В«РљРѕРїРёСЂРѕРІР°С‚СЊВ»

    def _wrap_data(event=None):
        try:
            lbl.config(wraplength=max(240, root.winfo_width() - 80))   # С‚РµРєСЃС‚ РЅРµ РїСЂРѕРїР°РґР°РµС‚ РІ СѓР·РєРѕРј РѕРєРЅРµ
        except Exception:
            pass

    root.bind("<Configure>", _wrap_data)

    nb = ttk.Notebook(vpan)
    vpan.add(nb, weight=1)                    # Р’Р•Р РҐ: СЃРїРёСЃРѕРє РёР·РґРµР»РёР№ (РџСЂРѕРІРѕРґРЅРёРє/Р”РµСЂРµРІРѕ/РўР°Р±Р»РёС†Р°)
    vpan.add(lpane, weight=1)                 # РќРР—: РґРµС‚Р°Р»Рё (4 РІРєР»Р°РґРєРё) вЂ” РїРѕР»Рµ РґРµР»РёС‚СЃСЏ РџРћРџРћР›РђРњ
    lhost.pack(side="left", fill="y", padx=(6, 0), pady=6)     # 07.10.2026: РЅР°СЃС‚СЂРѕР№РєРё вЂ” РЎР›Р•Р’Рђ
    vpan.pack(side="left", fill="both", expand=True, padx=6, pady=(0, 6))

    def _half_sash():
        """Р Р°Р·РґРµР»РёС‚РµР»СЊ вЂ” СЂРѕРІРЅРѕ РІ РїРѕР»РѕРІРёРЅСѓ. Р›РѕР¶СЊ, РїРѕРєР° РѕРєРЅРѕ РµС‰С‘ РЅРµ СЂР°Р·Р»РѕР¶РµРЅРѕ (РёРЅР°С‡Рµ sash
        РІСЃС‚Р°С‘С‚ РЅР° РјРёРЅРёРјСѓРј Рё РїРѕР»СѓС‡Р°РµС‚СЃСЏ В«РІРµСЂС… СЃРІС‘СЂРЅСѓС‚, РЅРёР· РЅР° РІСЃС‘ РѕРєРЅРѕВ»)."""
        try:
            h = vpan.winfo_height()
            if h < 200:
                return False
            vpan.sashpos(0, max(150, h // 2))
            return True
        except Exception:
            return False

    def _half_try(n=0):
        """07.10.2026: РїРѕРІС‚РѕСЂСЏРµРј, РїРѕРєР° Сѓ СЂР°Р·РґРµР»РёС‚РµР»СЏ РЅРµ РїРѕСЏРІРёС‚СЃСЏ РЅР°СЃС‚РѕСЏС‰Р°СЏ РІС‹СЃРѕС‚Р°."""
        if getattr(root, "_plm_sash_user", False):
            return
        if not _half_sash() and n < 15:
            root.after(150, lambda: _half_try(n + 1))

    vpan.bind("<ButtonRelease-1>", lambda e: setattr(root, "_plm_sash_user", True))
    root.after(200, _half_try)
    tab_table = ttk.Frame(nb)                 # РўР°Р±Р»РёС†Р° вЂ” РїР»РѕСЃРєРёР№ РІРёРґ РґР°РЅРЅС‹С… Р±Р°Р·С‹ (С‚СЂРµС‚СЊСЏ РІРєР»Р°РґРєР°)
    tab_tree = ttk.Frame(nb)                  # Р”РµСЂРµРІРѕ вЂ” РёРµСЂР°СЂС…РёСЏ РўР•РҐ Р–Р• РґР°РЅРЅС‹С… (РїР°РїРєРё в†’ С„Р°Р№Р»С‹) (РІС‚РѕСЂР°СЏ)
    nb.add(tab_tree, text=" Р”РµСЂРµРІРѕ ")
    nb.add(tab_table, text=" РўР°Р±Р»РёС†Р° ")

    # --- Р”Р•Р Р•Р’Рћ: С„РёР»СЊС‚СЂ РїРѕ Р’РЎР•Р™ Р±Р°Р·Рµ + РёРµСЂР°СЂС…РёСЏ РїР°РїРѕРє (Р»РµРЅРёРІР°СЏ, РёР· Р±Р°Р·С‹) ---
    import engine as eng

    # --- РџР РћР’РћР”РќРРљ: РїР°РїРєРё СЃРєР»Р°РґР° РёРµСЂР°СЂС…РёРµР№ (Р»РµРЅРёРІР°СЏ, РёР· Р±Р°Р·С‹) вЂ” РєР°Рє РІ РџСЂРѕРІРѕРґРЅРёРєРµ Windows ---
    tab_expl = ttk.Frame(nb)
    nb.insert(0, tab_expl, text=" РџСЂРѕРІРѕРґРЅРёРє ")     # РџСЂРѕРІРѕРґРЅРёРє вЂ” РџР•Р Р’РђРЇ РІРєР»Р°РґРєР°
    ebar = ttk.Frame(tab_expl, padding=(6, 4))
    ebar.pack(fill="x")
    ttk.Button(ebar, text="РћР±РЅРѕРІРёС‚СЊ", command=lambda: fill_explorer()).pack(side="left", padx=4)
    esum = ttk.Label(ebar, text="")
    esum.pack(side="left", padx=10)
    ebody = ttk.Frame(tab_expl)
    ebody.pack(fill="both", expand=True, padx=6, pady=(0, 6))
    ebody.rowconfigure(0, weight=1)
    ebody.columnconfigure(0, weight=1)
    ECOLS = ("РўРёРї", "Р¤Р°Р№Р»", "РћР±РѕР·РЅР°С‡РµРЅРёРµ", "РќР°РёРјРµРЅРѕРІР°РЅРёРµ", "РњР°С‚РµСЂРёР°Р»", "РћР±СЉС‘Рј, РјРјВі",
             "Р РµРІРёР·РёСЏ", "Р РѕР»СЊ", "РџСѓС‚СЊ")
    eview = ttk.Treeview(ebody, columns=ECOLS, show="tree headings", height=18)
    eview.heading("#0", text="РїР°РїРєР° / С„Р°Р№Р»")
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
        return p if len(p) <= 90 else "вЂ¦" + p[-88:]

    def _expl_root_paths():
        """РљРѕСЂРЅРё РџР РћР’РћР”РќРРљРђ: СЃРЅР°С‡Р°Р»Р° РїР°РїРєРё РѕРєРЅР° (РѕСЃРЅРѕРІРЅР°СЏ + РџР°РїРєР°2), Р·Р°С‚РµРј РєРѕСЂРЅРё Р±Р°Р·С‹."""
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
        """РџРѕРґРїР°РїРєРё (СЃ С‡РёСЃР»Р°РјРё) Рё С„Р°Р№Р»С‹ РїР°РїРєРё вЂ” РћР”РќРРњ СЃРѕРµРґРёРЅРµРЅРёРµРј (Р±РµР· COUNT РЅР° РєР°Р¶РґСѓСЋ РїРѕРґРїР°РїРєСѓ)."""
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
                         text="%s  [%d РїР°РїРѕРє, %d С„Р°Р№Р»РѕРІ]" % (os.path.basename(folder) or folder,
                                                              subs_n, files_n),
                         values=("РїР°РїРєР°", "", "", "", "", "", "", "", _e_short(folder)))
        _EFOLD[n] = folder
        eview.insert(n, "end", text="вЂ¦")          # В«РїР»СЋСЃРёРєВ»: РґРµС‚Рё С‡РёС‚Р°СЋС‚СЃСЏ РїСЂРё СЂР°СЃРєСЂС‹С‚РёРё
        return n

    def _expl_file_row(node, p, desig, name):
        n = eview.insert(node, "end", text=os.path.basename(p), values=(
            "С„Р°Р№Р»", os.path.basename(p), desig or "", name or "", "", "", "", "", _e_short(p)))
        _EFILE[n] = p
        return n

    def _expl_more(node, rest, subs):
        """РџРѕСЂС†РёСЏРјРё РїРѕ 150 вЂ” РѕРєРЅРѕ РЅРµ Р·Р°РјРёСЂР°РµС‚, СЃС‚СЂРѕРєРё РїРѕСЏРІР»СЏСЋС‚СЃСЏ РїРѕ РјРµСЂРµ С‡С‚РµРЅРёСЏ."""
        for p, desig, name in rest[:150]:
            _expl_file_row(node, p, desig, name)
        if len(rest) > 150:
            root.after(1, lambda: _expl_more(node, rest[150:], subs))
        else:
            for s, sc, fc in subs:
                _expl_node(node, s, sc, fc)
            _EDONE.add(node)

    def _expl_fill(node, res=None):
        """Р›Р•РќРР’Рћ: РїРѕРєР°Р·Р°Р»Рё В«С‡РёС‚Р°СЋвЂ¦В» в†’ С„РѕРЅРѕРј С‡РёС‚Р°РµРј в†’ СЂРёСЃСѓРµРј РїРѕСЂС†РёСЏРјРё. РџРѕРІС‚РѕСЂ РЅРµ РїРµСЂРµС‡РёС‚С‹РІР°РµС‚."""
        folder = _EFOLD.get(node)
        if folder is None:
            return
        if res is None:
            if node in _EDONE:
                return
            for ch in eview.get_children(node):
                eview.delete(ch)
            eview.insert(node, "end", text="вЂ¦ С‡РёС‚Р°СЋ")

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
                if eview.item(ch, "text") == "вЂ¦ С‡РёС‚Р°СЋ":
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
        esum.config(text="РєРѕСЂРЅРµР№: %d вЂ” СЂР°СЃРєСЂС‹РІР°Р№ РїР°РїРєРё (РґРµС‚Рё С‡РёС‚Р°СЋС‚СЃСЏ РїСЂРё СЂР°СЃРєСЂС‹С‚РёРё)" % len(roots))

    def _expl_dbl(event=None):
        path = _EFILE.get(eview.focus())
        if path and os.path.isfile(path):
            history_window(root, tk, ttk, filedialog,
                           "РСЃС‚РѕСЂРёСЏ РёР·РјРµРЅРµРЅРёР№ вЂ” %s" % os.path.basename(path),
                           lambda: history_rows(path, hist_settings()),
                           settings=settings, save_settings=save_settings,
                           status=os.path.basename(path))

    eview.bind("<<TreeviewOpen>>", lambda ev: _expl_fill(eview.focus()))
    eview.bind("<Double-1>", _expl_dbl)
    fill_explorer()

    _deb = {"id": None}

    def debounce(fn, ms=450):
        """РџСЂРѕСЃС‚РѕРµ СЂРµС€РµРЅРёРµ РѕС‚ С‚РѕСЂРјРѕР·РѕРІ: Р·Р°РїСѓСЃРєР°С‚СЊ РїРѕРёСЃРє С‡РµСЂРµР· РїР°СѓР·Сѓ РїРѕСЃР»Рµ РЅР°Р±РѕСЂР°."""
        if _deb["id"]:
            try:
                root.after_cancel(_deb["id"])
            except Exception:
                pass
        _deb["id"] = root.after(ms, fn)

    TCOLS = ("РўРёРї", "Р¤Р°Р№Р»", "РћР±РѕР·РЅР°С‡РµРЅРёРµ", "РќР°РёРјРµРЅРѕРІР°РЅРёРµ", "РњР°С‚РµСЂРёР°Р»", "РћР±СЉС‘Рј, РјРјВі", "Р РµРІРёР·РёСЏ", "Р РѕР»СЊ", "РџСѓС‚СЊ")
    tflt = ttk.Frame(tab_tree, padding=(6, 4))
    tflt.pack(fill="x")
    ttk.Label(tflt, text="Р¤РёР»СЊС‚СЂ РїРѕ РІСЃРµР№ Р±Р°Р·Рµ:").pack(side="left")
    e_tfilter = ttk.Entry(tflt, width=38)
    e_tfilter.pack(side="left", padx=4)
    e_tfilter.bind("<KeyRelease>", lambda ev: debounce(fill_tree_view))
    ttk.Button(tflt, text="РЎР±СЂРѕСЃРёС‚СЊ",
               command=lambda: (e_tfilter.delete(0, "end"), fill_tree_view())).pack(side="left", padx=6)

    tmode = tk.StringVar(value="plm")
    ttk.Radiobutton(tflt, text="Р’С…РѕРґРёРјРѕСЃС‚СЊ (РџР›Рњ)", variable=tmode, value="plm",
                    command=lambda: fill_tree_view()).pack(side="left", padx=(10, 0))
    ttk.Radiobutton(tflt, text="РџР°РїРєРё", variable=tmode, value="folders",
                    command=lambda: fill_tree_view()).pack(side="left", padx=(8, 0))

    tbar = ttk.Frame(tab_tree, padding=(6, 0))
    tbar.pack(fill="x")
    ttk.Button(tbar, text="РЎРћРЎРўРђР’ (РІРЅРёР·)", command=lambda: tree_down()).pack(side="left", padx=4)
    ttk.Button(tbar, text="Р“Р”Р• РРЎРџРћР›Р¬Р—РЈР•РўРЎРЇ (РІРІРµСЂС…)",
               command=lambda: tree_up()).pack(side="left", padx=4)
    ttk.Button(tbar, text="РР—РњР•РќР•РќРРЇ РїРѕ РёР·РґРµР»РёСЋ",
               command=lambda: changes_selected()).pack(side="left", padx=4)
    ttk.Button(tbar, text="Р РђР—Р’Р•Р РќРЈРўР¬ Р’РЎРЃ", command=lambda: expand_all()).pack(side="left", padx=4)
    tsum = ttk.Label(tbar, text="")
    tsum.pack(side="left", padx=10)

    tbody = ttk.Frame(tab_tree)
    tbody.pack(fill="both", expand=True, padx=6, pady=(0, 6))
    tbody.rowconfigure(0, weight=1)
    tbody.columnconfigure(0, weight=1)
    tview = ttk.Treeview(tbody, columns=TCOLS, show="tree headings", height=16)
    tview.heading("#0", text="РїР°РїРєР° / СѓР·РµР»")
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
        return p if len(p) <= 90 else "вЂ¦" + p[-88:]

    def _file_row(parent, p, desig, name, material, volume, rev, role):
        return tview.insert(parent, "end", values=(
            "С„Р°Р№Р»", os.path.basename(p), desig or "", name or "", material or "",
            ("%.0f" % volume) if volume else "", rev or "", role or "", _short(p)))

    def node_add(node, folder):
        subs, files = eng.folder_children(folder)
        for p, desig, name, material, volume, rev, role in files:
            _file_row(node, p, desig, name, material, volume, rev, role)
        for s in subs:
            a, b = eng.folder_files_count(s)
            n = tview.insert(node, "end", text="%s  [%d РїР°РїРѕРє, %d С„Р°Р№Р»РѕРІ]"
                             % (os.path.basename(s) or s, a, b),
                             values=("РїР°РїРєР°", "", "", "", "", "", "", "", _short(s)))
            _FOLDERS[n] = s
            tview.insert(n, "end", text="Р·Р°РіСЂСѓР·РєР°вЂ¦")      # В«РїР»СЋСЃРёРєВ» РґР»СЏ СЂР°СЃРєСЂС‹С‚РёСЏ

    def _vals9(m, i, qty=""):
        """РЎС‚СЂРѕРєР° РґР»СЏ РґРµСЂРµРІР° РІРєР»Р°РґРєРё В«Р”РµСЂРµРІРѕВ» (9 РєРѕР»РѕРЅРѕРє)."""
        role = (i[5] or "") if len(i) > 5 else ""
        kind = "РѕСЃРЅР°СЃС‚РєР°" if role == "MFG" else ("РёР·РґРµР»РёРµ" if (i[6] or i[7]) else "РґРµС‚Р°Р»СЊ")
        return (kind, m, i[0] or "", i[1] or "", i[2] or "",
                ("%.0f" % i[3]) if (len(i) > 3 and i[3]) else "", i[4] or "", role, qty)

    def _fill_node(tree_widget, node, model, with_up=True):
        """Р•Р”РРќР«Р™ СЃС‚СЂРѕРёС‚РµР»СЊ РІРµС‚РєРё РґР»СЏ РѕР±РµРёС… РїР»РѕС‰Р°РґРѕРє.

        СЃРѕСЃС‚Р°РІ (РІРЅРёР·) В· в—„ РѕС‚Р»РёРІРєР°/Р·Р°РіРѕС‚РѕРІРєР° В· РјРѕРґРµР»СЊРЅР°СЏ РѕСЃРЅР°СЃС‚РєР° (MFG) В· [РІС…РѕРґРёС‚ РІ (РІСЃРµ СЃР±РѕСЂРєРё)].
        Р’РѕР·РІСЂР°С‰Р°РµС‚ (Р·Р°РіРѕС‚РѕРІРѕРє, СѓР·Р»РѕРІ РІРІРµСЂС…, РґРµС‚РµР№ СЃРѕСЃС‚Р°РІР°).
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
                text=("в—„ %s: РёРјСЏ РЅРµ РЅР°Р№РґРµРЅРѕ (РІ С„Р°Р№Р»Рµ С‚РѕР»СЊРєРѕ РІРЅСѓС‚СЂРµРЅРЅРёР№ РєРѕРґ)" % _kind(k))
                     if not b else "в—„ %s: %s" % (_kind(k), b),
                values=("Р·Р°РіРѕС‚РѕРІРєР°/РѕС‚Р»РёРІРєР°", b or "вЂ”", "", "", "", "", "", "", ""))
            if b:
                reg[dn0] = b                          # V81: СѓР·РµР» В«Р·Р°РіРѕС‚РѕРІРєР°/РѕС‚Р»РёРІРєР°В» РєР»РёРєР°Р±РµР»РµРЅ
                for name, how in eng.mfg_models(b, 30):
                    on = tree_widget.insert(dn0, "end", text="РѕСЃРЅР°СЃС‚РєР°: %s  (%s)" % (name, how),
                                            values=("РѕСЃРЅР°СЃС‚РєР°", name, "", "", "", "", "", "", ""))
                    reg[on] = name                    # V81: РѕСЃРЅР°СЃС‚РєР° РїРѕРґ Р·Р°РіРѕС‚РѕРІРєРѕР№ РєР»РёРєР°Р±РµР»СЊРЅР°
        if mfg:
            mn = tree_widget.insert(node, "end", open=True, text="РјРѕРґРµР»СЊРЅР°СЏ РѕСЃРЅР°СЃС‚РєР° (MFG):")
            for name, how in mfg[:60]:
                on = tree_widget.insert(mn, "end", text="%s  (%s)" % (name, how),
                                        values=("РѕСЃРЅР°СЃС‚РєР°", name, "", "", "", "", "", "", ""))
                reg[on] = name                        # V81: MFG-СѓР·РµР» РєР»РёРєР°Р±РµР»РµРЅ
        if with_up:
            un = tree_widget.insert(node, "end", open=True, text="РІС…РѕРґРёС‚ РІ (РІСЃРµ СЃР±РѕСЂРєРё):")
            if not up:
                tree_widget.insert(un, "end",
                                   text="вЂ” РЅРё РІ РѕРґРЅСѓ СЃР±РѕСЂРєСѓ РЅРµ РІС…РѕРґРёС‚ (РІРµСЂС…РЅРµРµ РёР·РґРµР»РёРµ РёР»Рё СЃРІСЏР·РµР№ РЅРµС‚ РІ Р±Р°Р·Рµ)",
                                   values=("вЂ”", "", "", "", "", "", "", "", ""))
            else:
                stack = [(un, model, 1)]
                while stack:
                    pn, m, depth = stack.pop()
                    for p2, q in up.get(m, []):
                        nn = tree_widget.insert(pn, "end", text="%s  в†‘ x%d" % (p2, q), values=row(p2, "x%d" % q))
                        reg[nn] = p2                  # V81: СѓР·РµР» В«РІС…РѕРґРёС‚ РІ (РІСЃРµ СЃР±РѕСЂРєРё)В» РєР»РёРєР°Р±РµР»РµРЅ
                        if depth < 8:
                            stack.append((nn, p2, depth + 1))
        cn = tree_widget.insert(node, "end", open=True, text="СЃРѕСЃС‚Р°РІ:")
        kids = down.get(model) or eng.plm_children(model)
        if not kids:
            tree_widget.insert(cn, "end", text="вЂ” РІ Р±Р°Р·Рµ РЅРµС‚ СЃРѕСЃС‚Р°РІР° РґР»СЏ СЌС‚РѕРіРѕ РёР·РґРµР»РёСЏ",
                               values=("вЂ”", "", "", "", "", "", "", "", ""))
        else:
            for c, q in kids:
                n = tree_widget.insert(cn, "end", text="%s  x%d" % (c, q), values=row(c, "x%d" % q))
                reg[n] = c
                tree_widget.insert(n, "end", text="Р·Р°РіСЂСѓР·РєР°вЂ¦")
        made = eng.derived_children(model)          # 07.10.2026: С‡С‚Рѕ РЎР”Р•Р›РђРќРћ РёР· РЅРµС‘ (РєРѕРїРёРё/РїСЂРѕРёР·РІРѕРґРЅС‹Рµ)
        if made:
            md = tree_widget.insert(node, "end", open=bool(made),
                                    text="СЃРґРµР»Р°РЅРѕ РёР· РЅРµС‘ (РєРѕРїРёРё/РїСЂРѕРёР·РІРѕРґРЅС‹Рµ): %d" % len(made))
            for c, k in made[:60]:
                nn = tree_widget.insert(md, "end", text="%s  (%s)" % (c, _kind(k)), values=row(c))
                reg[nn] = c
                tree_widget.insert(nn, "end", text="Р·Р°РіСЂСѓР·РєР°вЂ¦")
            if len(made) > 60:
                tree_widget.insert(md, "end", text="вЂ¦ РµС‰С‘ %d" % (len(made) - 60))
        return len(der), sum(len(v) for v in up.values()), len(kids)

    def _model_values(m):
        i = eng.models_info([m]).get(m, ("", "", "", 0, "", "", 0, 0))
        return _vals9(m, i)

    def _kind(k):
        return {"РЅР°СЃР»РµРґРѕРІР°РЅРёРµ": "Р·Р°РіРѕС‚РѕРІРєР°", "РїСЂРѕРёР·РІРѕРґРЅР°СЏ": "РѕС‚Р»РёРІРєР°",
                "РєРѕРїРёСЏ": "РјРѕРґРµР»СЊ СЃРєРѕРїРёСЂРѕРІР°РЅР° РѕС‚",
                "hash": "Р·Р°РіРѕС‚РѕРІРєР°/РѕС‚Р»РёРІРєР°"}.get(k, "Р·Р°РіРѕС‚РѕРІРєР°/РѕС‚Р»РёРІРєР°")

    def _resolve(base, models):
        for cand in (base, base + ".prt", base + ".asm"):
            if cand in models:
                return cand
        return ""

    def node_add_model(node, model):
        """Р’РєР»Р°РґРєР° В«Р”РµСЂРµРІРѕВ»: С‚РѕС‚ Р¶Рµ СЃС‚СЂРѕРёС‚РµР»СЊ РІРµС‚РєРё, С‡С‚Рѕ Рё РІ РЅРёР¶РЅРµРј РѕРєРЅРµ (СЃРѕСЃС‚Р°РІ/РѕС‚Р»РёРІРєРё/РѕСЃРЅР°СЃС‚РєР°/РІС…РѕРґРёС‚ РІ)."""
        return _fill_node(tview, node, model, with_up=True)

    def on_open(event=None):
        node = tview.focus()
        folder = _FOLDERS.get(node)
        model = _MODELS.get(node)
        if not (folder or model):
            return
        kids = tview.get_children(node)
        if kids and tview.item(kids[0], "text") == "Р·Р°РіСЂСѓР·РєР°вЂ¦":
            tview.delete(*kids)
            if folder:
                node_add(node, folder)
            else:
                node_add_model(node, model)

    tview.bind("<<TreeviewOpen>>", on_open)
    def _dbl_click():
        """Р”РІРѕР№РЅРѕР№ С‰РµР»С‡РѕРє РїРѕ СЃС‚СЂРѕРєРµ: РёР·РґРµР»РёРµ РµСЃС‚СЊ в†’ РІРєР»Р°РґРєР° В«РСЃС‚РѕСЂРёСЏ С„Р°Р№Р»Р°В»; РЅРµС‚ (РїР°РїРєР°) в†’ РєР°СЂС‚РѕС‡РєР°."""
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

    tview.bind("<Double-1>", lambda ev: _dbl_click())      # РґРІРѕР№РЅРѕР№ С‰С‘Р»С‡РѕРє вЂ” РёСЃС‚РѕСЂРёСЏ С„Р°Р№Р»РѕРІ РёР·РґРµР»РёСЏ

    def fill_tree_view():
        text = e_tfilter.get().strip()
        tview.delete(*tview.get_children())
        _FOLDERS.clear()
        _MODELS.clear()
        if tmode.get() == "plm":                  # Р”Р•Р Р•Р’Рћ Р’РҐРћР”РРњРћРЎРўР (РџР›Рњ): СЃРѕСЃС‚Р°РІ РІРЅРёР·, РІС…РѕРґРёРјРѕСЃС‚СЊ РІРІРµСЂС…
            if text:
                rows = eng.find_plm_models(text)
                for m, files, pars in rows:
                    v = list(_model_values(m))
                    v[8] = "С„Р°Р№Р»РѕРІ %d В· РІС…РѕРґРёС‚ РІ %d" % (files, pars)
                    tview.insert("", "end", text=m, values=v)
                tsum.config(text="РјРѕРґРµР»РµР№ РїРѕ С„РёР»СЊС‚СЂСѓ: %d" % len(rows))
            else:
                tops = eng.plm_tops(6000)
                info = eng.models_info(tops)
                rn = tview.insert("", "end", open=True,
                                  text="Р’РЎРЃ РџР РћРР—Р’РћР”РЎРўР’Рћ вЂ” РІРµСЂС…РЅРёС… СЃР±РѕСЂРѕРє %d РёР· %d"
                                       % (len(tops), eng.count_tops()))
                for m in tops:
                    v = info.get(m, ("", "", "", 0, "", "", 0, 0))
                    n = tview.insert(rn, "end", text=m, values=_vals9(m, v))
                    _MODELS[n] = m
                    tview.insert(n, "end", text="Р·Р°РіСЂСѓР·РєР°вЂ¦")
                tsum.config(text="РІРµСЂС…РЅРёС… СЃР±РѕСЂРѕРє %d В· СЂР°СЃРєСЂС‹РІР°Р№ СѓР·Р»С‹ РёР»Рё Р¶РјРё Р РђР—Р’Р•Р РќРЈРўР¬ Р’РЎРЃ" % len(tops))
            return
        if text:
            rows = eng.search_files(text)
            for p, folder, desig, name, material, volume, rev, role in rows:
                _file_row("", p, desig, name, material, volume, rev, role)
            tsum.config(text="РїРѕРєР°Р·Р°РЅРѕ %d (С„РёР»СЊС‚СЂ РїРѕ РІСЃРµРј СЃР»РѕРІР°Рј)" % len(rows))
        else:
            for r in scan_roots(e_folder.get(), e_folder2.get(), settings.get("folders")):
                a, b = eng.folder_files_count(r)
                n = tview.insert("", "end", text="%s  [%d РїР°РїРѕРє, %d С„Р°Р№Р»РѕРІ]" % (r, a, b),
                                 values=("РєРѕСЂРµРЅСЊ", "", "", "", "", "", "", "", ""))
                _FOLDERS[n] = r
                tview.insert(n, "end", text="Р·Р°РіСЂСѓР·РєР°вЂ¦")
            s = eng.summary()
            tsum.config(text="РІ Р±Р°Р·Рµ РёР·РґРµР»РёР№ %d (С„Р°Р№Р»РѕРІ СЃ РєРѕРїРёСЏРјРё РІРµСЂСЃРёР№ %d) В· РёР·РјРµРЅРµРЅРёР№ %d"
                        % (s.get("models", 0), s.get("snapshots", 0), s.get("changes", 0)))

    def expand_all():
        """РџРћР›РќРћР• РґРµСЂРµРІРѕ: РІ СЂРµР¶РёРјРµ Р’С…РѕРґРёРјРѕСЃС‚СЊ СЃС‚СЂРѕРёС‚СЃСЏ РѕРґРЅРёРј Р·Р°С…РѕРґРѕРј РёР· Р±Р°Р·С‹ (Р±С‹СЃС‚СЂРѕ)."""
        if e_tfilter.get().strip():
            tsum.config(text="СЃРЅР°С‡Р°Р»Р° СЃР±СЂРѕСЃСЊ С„РёР»СЊС‚СЂ вЂ” С‚РѕРіРґР° СЂР°Р·РІРµСЂРЅСѓ РїРѕР»РЅРѕРµ РґРµСЂРµРІРѕ")
            return
        t0 = time.time()
        if tmode.get() == "plm":
            tops, children, info, derived = eng.plm_tree_data()
            tview.delete(*tview.get_children())
            _MODELS.clear()
            _FOLDERS.clear()
            cap, n = 60000, 0
            rn = tview.insert("", "end", open=True,
                              text="Р’РЎРЃ РџР РћРР—Р’РћР”РЎРўР’Рћ вЂ” РІРµСЂС…РЅРёС… СЃР±РѕСЂРѕРє %d" % len(tops))
            stack = [(rn, m, 1, frozenset((m,)), "") for m in reversed(tops)]
            while stack and n < cap:
                parent, model, depth, path, label = stack.pop()
                v = _vals9(model, info.get(model, ("", "", "", 0, "", "", 0, 0)))
                node = tview.insert(parent, "end", text=label + model, values=v, open=True)
                _MODELS[node] = model
                n += 1
                if depth >= 12:                     # РїСЂРµРґРµР» РіР»СѓР±РёРЅС‹
                    continue
                for c, q in reversed(children.get(model, [])):
                    if n < cap and c not in path:   # Р·Р°С‰РёС‚Р° РѕС‚ С†РёРєР»РѕРІ РїРѕ РІРµС‚РєРµ
                        stack.append((node, c, depth + 1, path | {c}, ""))
                for b, k in reversed(derived.get(model, [])):    # Р·Р°РіРѕС‚РѕРІРєР°/РѕС‚Р»РёРІРєР°
                    base = _resolve(b, info)
                    lbl = "в—„ %s: " % _kind(k)
                    if not base:
                        tview.insert(node, "end", text=lbl + b + "  (РЅРµС‚ РІ Р±Р°Р·Рµ)",
                                     values=("Р·Р°РіРѕС‚РѕРІРєР°", b, "", "", "", "", "", "", ""))
                    elif base not in path and n < cap:
                        stack.append((node, base, depth + 1, path | {base}, lbl))
            tsum.config(text="РїРѕСЃС‚СЂРѕРµРЅРѕ СѓР·Р»РѕРІ: %d Р·Р° %.1f СЃ%s"
                        % (n, time.time() - t0, " (РґРѕСЃС‚РёРіРЅСѓС‚ РїСЂРµРґРµР»)" if stack else ""))
            return
        limit_nodes = 6000
        queue = list(tview.get_children(""))
        cnt = 0
        while queue and cnt < limit_nodes:
            node = queue.pop(0)
            if node in _FOLDERS:
                kids = tview.get_children(node)
                if kids and tview.item(kids[0], "text") == "Р·Р°РіСЂСѓР·РєР°вЂ¦":
                    tview.delete(*kids)
                    node_add(node, _FOLDERS[node])
            tview.item(node, open=True)
            queue.extend(tview.get_children(node))
            cnt += 1
            if cnt % 40 == 0:
                tsum.config(text="СЂР°Р·РІРѕСЂР°С‡РёРІР°СЋ РїР°РїРєРёвЂ¦ СѓР·Р»РѕРІ %d" % cnt)
                try:
                    root.update_idletasks()
                except Exception:
                    pass
        tsum.config(text="СЂР°Р·РІС‘СЂРЅСѓС‚Рѕ СѓР·Р»РѕРІ: %d Р·Р° %.1f СЃ%s"
                    % (cnt, time.time() - t0, " (РїСЂРµРґРµР»)" if queue else ""))

    def purge_folder():
        f = norm_path(e_folder.get()) if e_folder.get().strip() else ""
        if not f:
            roots = eng.base_roots()
            f = roots[0] if roots else ""
        return f

    def _text_window(title, head, text, note=""):
        """РћРєРЅРѕ СЃ С‚РµРєСЃС‚РѕРј (РїР»Р°РЅ РџРЈР Р“Р•, РёС‚РѕРіРё): РІРёРґРЅРѕ СЃ Р›Р®Р‘РћР™ РІРєР»Р°РґРєРё, РјРѕР¶РЅРѕ СЃРєРѕРїРёСЂРѕРІР°С‚СЊ С†РµР»РёРєРѕРј."""
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
        ttk.Button(foot, text="РљРѕРїРёСЂРѕРІР°С‚СЊ РІСЃС‘",
                   command=lambda: (root.clipboard_clear(),
                                    root.clipboard_append(text))).pack(side="left")
        ttk.Button(foot, text="Р—Р°РєСЂС‹С‚СЊ", command=win.destroy).pack(side="left", padx=6)
        if note:
            ttk.Label(foot, text=note, foreground="#666").pack(side="left", padx=10)
        return win

    def purge_show():
        """РџР›РђРќ С‡РёСЃС‚РєРё РІРµСЂСЃРёР№ (С„Р°Р№Р»С‹ РќР• С‚СЂРѕРіР°СЋС‚СЃСЏ): РѕС‚РґРµР»СЊРЅРѕРµ РѕРєРЅРѕ + СЃС‚Р°С‚СѓСЃ + РѕС‚С‡С‘С‚ РІ log\\reports."""
        folder = purge_folder()
        plan = eng.purge_plan(folder or None, int(e_keep.get() or 2))
        txt = eng.purge_plan_text(plan)
        head = ("Purge-РїР»Р°РЅ: Р»РёС€РЅРёС… РІРµСЂСЃРёР№ %d В· РѕСЃРІРѕР±РѕРґРёС‚СЃСЏ %.1f РњР‘ В· РїР°РїРєР° %s"
                % (plan["count"], plan["bytes"] / 1048576.0, folder or "РІСЃСЏ Р±Р°Р·Р°"))
        log_line("purge plan: %s вЂ” Р»РёС€РЅРёС… %d, %.1f РњР‘"
                 % (folder or "РІСЃСЏ Р±Р°Р·Р°", plan["count"], plan["bytes"] / 1048576.0))
        rep = ""
        try:
            rep = os.path.join(REPORTS_DIR,
                               "PURGE_plan_%s.txt" % datetime.datetime.now().strftime("%Y-%m-%d_%H%M"))
            os.makedirs(REPORTS_DIR, exist_ok=True)
            with open(rep, "w", encoding="utf-8") as f:
                f.write(txt)
        except Exception:
            pass
        lbl.config(text=head + (" В· РѕС‚С‡С‘С‚: %s" % os.path.basename(rep) if rep else ""))
        _text_window("Purge: РџР›РђРќ (С„Р°Р№Р»С‹ РЅРµ С‚СЂРѕРіР°СЋС‚СЃСЏ)", head, txt,
                     "РѕС‚С‡С‘С‚: %s" % (os.path.basename(rep) if rep else "РЅРµ СЃРѕС…СЂР°РЅС‘РЅ"))

    def purge_run():
        """РџРµСЂРµРЅРѕСЃ Р»РёС€РЅРёС… РІРµСЂСЃРёР№ РІ Р‘Р­РљРђРџ вЂ” РІСЃС‚СЂРѕРµРЅРЅС‹Рј РґРІРёР¶РєРѕРј РџР›Рњ (РІРЅРµС€РЅРёР№ purge_versions РЅРµ РЅСѓР¶РµРЅ)."""
        from tkinter import messagebox as mb
        folder = purge_folder()
        plan = eng.purge_plan(folder or None, int(e_keep.get() or 2))
        if not plan["count"]:
            lbl.config(text="Purge: С‡РёСЃС‚РёС‚СЊ РЅРµС‡РµРіРѕ вЂ” Р»РёС€РЅРёС… РІРµСЂСЃРёР№ РЅРµС‚")
            return
        if not folder or not os.path.isdir(folder):
            lbl.config(text="Purge: РІС‹Р±РµСЂРё СЃСѓС‰РµСЃС‚РІСѓСЋС‰СѓСЋ РїР°РїРєСѓ (РєРЅРѕРїРєР° В«РџСѓС‚Рё Рё РёСЃРєР»СЋС‡РµРЅРёСЏвЂ¦В»)")
            return
        keep = int(e_keep.get() or 2)
        bdir = os.path.join(folder, "_purge_backup")
        if not mb.askyesno("Purge",
                           "РџРµСЂРµРЅРµСЃС‚Рё РІ Р‘Р­РљРђРџ %d Р»РёС€РЅРёС… РІРµСЂСЃРёР№ (%.1f РњР‘)?\n%s\n\n"
                           "РЈРґР°Р»РµРЅРёСЏ РЅРµС‚: С„Р°Р№Р»С‹ СѓРµРґСѓС‚ РІ %s"
                           % (plan["count"], plan["bytes"] / 1048576.0, folder, bdir)):
            lbl.config(text="Purge: РѕС‚РјРµРЅРµРЅРѕ")
            return

        def work():
            try:
                rep = eng.purge_execute(folder, keep, None, items=plan["candidates"])
                out = ("РїРµСЂРµРЅРµСЃРµРЅРѕ %d РІРµСЂСЃРёР№, РѕСЃРІРѕР±РѕР¶РґРµРЅРѕ %.1f РњР‘, Р·Р° %.1f СЃ\nР±СЌРєР°Рї: %s"
                       % (len(rep["РїРµСЂРµРЅРµСЃРµРЅРѕ"]), rep["РѕСЃРІРѕР±РѕР¶РґРµРЅРѕ_Р±Р°Р№С‚"] / 1048576.0,
                          rep["seconds"], bdir))
                if rep["РїСЂРѕРїСѓС‰РµРЅРѕ_СЃ_РїСЂРёС‡РёРЅРѕР№"]:
                    out += "\nРїСЂРѕРїСѓС‰РµРЅРѕ: " + "; ".join(rep["РїСЂРѕРїСѓС‰РµРЅРѕ_СЃ_РїСЂРёС‡РёРЅРѕР№"][:20])
            except Exception as e:
                out = "РћРЁРР‘РљРђ: %s" % e
            log_line("purge execute: %s -> %s" % (folder, out.split("\n")[0]))

            def done():
                head = "Purge: %s" % out.split("\n")[0]
                lbl.config(text=head)
                _text_window("Purge: РїРµСЂРµРЅРѕСЃ РІ Р±СЌРєР°Рї вЂ” СЂРµР·СѓР»СЊС‚Р°С‚", head, out, bdir)

            try:
                root.after(0, done)
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()
        lbl.config(text="Purge: РїРµСЂРµРЅРѕС€Сѓ Р»РёС€РЅРёРµ РІРµСЂСЃРёРё РІ Р±СЌРєР°РївЂ¦")

    def _lout(text):
        """РћРєРЅРѕ РІС‹РІРѕРґР° РєРЅРѕРїРѕРє РІРєР»Р°РґРєРё В«Р”РµСЂРµРІРѕВ» вЂ” РїРµСЂРµРЅРµСЃРµРЅРѕ РІ В«Р”РµСЂРµРІРѕ СЃРІСЏР·РµР№В» (СЃСЂРµРґРЅРµРµ РѕРєРЅРѕ СѓР±СЂР°РЅРѕ)."""
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
            buf.write("РћРЁРР‘РљРђ: %s" % e)
        _lout(buf.getvalue().rstrip())

    def cap(fn, *a):
        """Р—Р°С…РІР°С‚РёС‚СЊ РІС‹РІРѕРґ CLI-С„СѓРЅРєС†РёРё РґРІРёР¶РєР° РІ СЃС‚СЂРѕРєСѓ (РґР»СЏ С‚РµРєСЃС‚РѕРІРѕРіРѕ РґРµСЂРµРІР°)."""
        import contextlib
        import io
        buf = io.StringIO()
        try:
            with contextlib.redirect_stdout(buf):
                fn(*a)
        except Exception as e:
            buf.write("РћРЁРР‘РљРђ: %s: %s" % (type(e).__name__, e))
        return buf.getvalue().rstrip()

    def _sel_model():
        sel = tview.selection()
        if not sel:
            return ""
        vals = tview.item(sel[0], "values")
        return eng.stem(vals[1]) if len(vals) > 1 and vals[1] else ""

    def where_selected():
        m = _sel_model()
        say(eng.do_where, m) if m else _lout("РІС‹Р±РµСЂРё СЃС‚СЂРѕРєСѓ-С„Р°Р№Р» РІ РґРµСЂРµРІРµ")

    def tree_down():
        m = _sel_model()
        say(eng.do_tree, m, 4) if m else _lout("РІС‹Р±РµСЂРё РёР·РґРµР»РёРµ РІ РґРµСЂРµРІРµ")

    def tree_up():
        m = _sel_model()
        say(eng.do_tree_up, m, 4) if m else _lout("РІС‹Р±РµСЂРё РёР·РґРµР»РёРµ РІ РґРµСЂРµРІРµ")

    def changes_selected():
        m = _sel_model()
        say(eng.do_changes_model, m, 200) if m else _lout("РІС‹Р±РµСЂРё СЃС‚СЂРѕРєСѓ-С„Р°Р№Р» РІ РґРµСЂРµРІРµ")

    def open_detail(model=None):
        """РљР°СЂС‚РѕС‡РєР° РёР·РґРµР»РёСЏ (РґРІРѕР№РЅРѕР№ С‰С‘Р»С‡РѕРє): РїР°СЃРїРѕСЂС‚ + С„Р°Р№Р»С‹; СЃР±РѕРєСѓ вЂ” РёСЃС‚РѕСЂРёСЏ/РІС…РѕРґРёРјРѕСЃС‚СЊ/СЃРѕСЃС‚Р°РІ/Р·Р°РіРѕС‚РѕРІРєР°."""
        model = (model or _sel_model()).strip()
        if not model:
            return
        title = "РР·РґРµР»РёРµ %s" % model
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
        for k, v in (("РћР±РѕР·РЅР°С‡РµРЅРёРµ", desig), ("РќР°РёРјРµРЅРѕРІР°РЅРёРµ", name), ("РњР°С‚РµСЂРёР°Р»", mat),
                     ("РћР±СЉС‘Рј, РјРјВі", ("%.0f" % vol) if vol else ""), ("Р РµРІРёР·РёСЏ", rev),
                     ("Р РѕР»СЊ", role), ("Р¤Р°Р№Р»РѕРІ", files), ("Р’С…РѕРґРёС‚ РІ СЃР±РѕСЂРѕРє", pars)):
            ttk.Label(left, text="%s: %s" % (k, v if v not in ("", 0, None) else "вЂ”")).pack(anchor="w")
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
                buf.write("РћРЁРР‘РљРђ: %s" % e)
            put(buf.getvalue().rstrip())

        def show_files():
            con = eng.connect()
            rows = con.execute("SELECT path,size,rev,revdate,author FROM snapshots WHERE model=? "
                               "ORDER BY path", (model,)).fetchall()
            con.close()
            lines = ["Р¤РђР™Р›Р« РР—Р”Р•Р›РРЇ: %d" % len(rows)]
            for p, sz, r, rd, au in rows:
                lines.append("%s | СЂРµРІ.%s | %s | %s | %.0f РљР‘"
                             % (p, r or "-", rd or "-", au or "-", (sz or 0) / 1024.0))
            put("\n".join(lines))

        def show_hist():
            """РСЃС‚РѕСЂРёСЏ С„Р°Р№Р»Р° вЂ” РћРўР”Р•Р›Р¬РќР«Рњ РїРѕР»РЅРѕС†РµРЅРЅС‹Рј РѕРєРЅРѕРј (СЃС‚РѕР»Р±С†С‹, РґР°С‚С‹, СЃРѕСЂС‚РёСЂРѕРІРєР°, CSV)."""
            con = eng.connect()
            r = con.execute("SELECT path FROM snapshots WHERE model=? ORDER BY path LIMIT 1",
                            (model,)).fetchone()
            con.close()
            if not r:
                put("С„Р°Р№Р» РЅРµ РЅР°Р№РґРµРЅ")
                return
            history_window(root, tk, ttk, filedialog,
                           "РСЃС‚РѕСЂРёСЏ С„Р°Р№Р»Р° вЂ” %s" % os.path.basename(r[0]),
                           lambda: history_rows_copy_aware(r[0], {"max_size_mb": float(e_max.get() or 0)}),
                           settings=settings, save_settings=save_settings,
                           status=os.path.basename(r[0]))

        def show_derived():
            lines = ["Р—РђР“РћРўРћР’РљРђ / РћРўР›РР’РљРђ (РёР· С‡РµРіРѕ СЃРґРµР»Р°РЅРѕ СЌС‚Рѕ РёР·РґРµР»РёРµ):"]
            d = eng.derived_bases(model)
            for b, k in d:
                lines.append("   в—„ %s: %s" % (_kind(k), b))
            if not d:
                lines.append("   вЂ”")
            con = eng.connect()
            rows = con.execute("SELECT child, kind FROM derived WHERE base=? OR base=?",
                               (model, eng.stem(model))).fetchall()
            con.close()
            lines.append("")
            lines.append("РР— Р­РўРћР“Рћ РЎР”Р•Р›РђРќРћ (РїСЂРѕРёР·РІРѕРґРЅС‹Рµ):")
            for c, k in rows:
                lines.append("   в–є %s (%s)" % (c, _kind(k or "")))
            if not rows:
                lines.append("   вЂ”")
            put("\n".join(lines))

        ttk.Button(btns, text="РСЃС‚РѕСЂРёСЏ С„Р°Р№Р»Р° (РѕРєРЅРѕ)", command=show_hist).pack(fill="x", pady=2)
        ttk.Button(btns, text="РЎР±РѕСЂРєРё, РєСѓРґР° РІС…РѕРґРёС‚",
                   command=lambda: show(eng.do_tree_up, model, 5)).pack(fill="x", pady=2)
        ttk.Button(btns, text="РЎРѕСЃС‚Р°РІ (РІРЅРёР·)",
                   command=lambda: show(eng.do_tree, model, 5)).pack(fill="x", pady=2)
        ttk.Button(btns, text="Р—Р°РіРѕС‚РѕРІРєР° / РѕС‚Р»РёРІРєР°", command=show_derived).pack(fill="x", pady=2)
        ttk.Button(btns, text="Р¤Р°Р№Р»С‹ РёР·РґРµР»РёСЏ", command=show_files).pack(fill="x", pady=2)
        out.pack(side="left", fill="both", expand=True, padx=(8, 8), pady=8)
        show_files()

    _plm_extra = {"nb": nb, "tab_tree": tab_tree, "tview": tview, "tfilter_entry": e_tfilter,
                  "tmode": tmode, "fill_tree_view": fill_tree_view, "expand_all": expand_all,
                  "open_detail": open_detail, "engine": eng}   # РґР»СЏ СЃР°РјРѕРїСЂРѕРІРµСЂРєРё
    fill_tree_view()                       # СЃСЂР°Р·Сѓ РїРѕРєР°Р·Р°С‚СЊ РІРµСЂС…РЅРёРµ РїР°РїРєРё Р±Р°Р·С‹

    # РЅРёР¶РЅРµРµ РґРµСЂРµРІРѕ РїСЂРѕРёР·РІРѕРґСЃС‚РІР° Р¶РёРІС‘С‚ Р’РќР• РІРєР»Р°РґРѕРє (РїРѕР»РѕСЃР° lpane РїСЂРёР¶Р°С‚Р° Рє РЅРёР·Сѓ РѕРєРЅР°)
    flt = ttk.Frame(tab_table, padding=(6, 4))
    flt.pack(fill="x")
    ttk.Label(flt, text="Р¤РёР»СЊС‚СЂ:").pack(side="left")
    e_filter = ttk.Entry(flt, width=44)
    e_filter.pack(side="left", padx=4)
    ttk.Label(flt, text="С‡Р°СЃС‚СЊ С‚РµРєСЃС‚Р°; РїСѓСЃС‚Рѕ вЂ” РїРѕРєР°Р·Р°С‚СЊ РІСЃС‘").pack(side="left")
    ttk.Button(flt, text="РЎР±СЂРѕСЃРёС‚СЊ", command=lambda: (e_filter.delete(0, "end"), redraw())).pack(side="left", padx=8)
    e_filter.bind("<KeyRelease>", lambda e: debounce(redraw))

    cols = list(settings.get("columns", DEFAULT_SETTINGS["columns"]))
    if "Р’РµСЂСЃРёР№" not in cols:
        cols.append("Р’РµСЂСЃРёР№")
    if "Р¤Р°Р№Р»" in cols:
        cols = ["Р¤Р°Р№Р»"] + [c for c in cols if c != "Р¤Р°Р№Р»"]
    sort_state = {"col": "Р¤Р°Р№Р»", "desc": False}
    rows_all, shown = [], []
    _ROWS = {}                                # uid -> СЃС‚СЂРѕРєР°: СЃС‚Р°Р±РёР»СЊРЅР°СЏ СЃРІСЏР·СЊ В«СЃС‚СЂРѕРєР° С‚Р°Р±Р»РёС†С‹ в†” РґР°РЅРЅС‹РµВ»
    _SEQ = {"n": 0}

    def row_uid(r):
        """РџРѕСЃС‚РѕСЏРЅРЅС‹Р№ id СЃС‚СЂРѕРєРё: РЅРµ Р·Р°РІРёСЃРёС‚ РѕС‚ СЃРѕСЂС‚РёСЂРѕРІРєРё Рё С„РёР»СЊС‚СЂР° (Р»РµС‡РёС‚ В«РІРЅРёР·Сѓ РїРѕРєР°Р·Р°РЅРѕ РґСЂСѓРіРѕРµВ»)."""
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

    # --- РћРќР›РђР™Рќ: РІРЅРёР·Сѓ СЃСЂР°Р·Сѓ СЃС‚СЂРѕРёС‚СЃСЏ РґРµСЂРµРІРѕ РїСЂРѕРёР·РІРѕРґСЃС‚РІР° РїРѕ РІС‹Р±СЂР°РЅРЅРѕР№ СЃС‚СЂРѕРєРµ ---
    # 08.10.2026: РѕР±С‰Р°СЏ РєРЅРѕРїРєР° РќРђР” РЅРёР¶РЅРёРј РѕРєРЅРѕРј вЂ” РІРµСЂРЅСѓС‚СЊ РїСЂРµРґРјРµС‚ Рє СЃС‚СЂРѕРєРµ, РІС‹Р±СЂР°РЅРЅРѕР№ РІ Р’Р•Р РҐРќР•Рњ РѕРєРЅРµ
    ltopbar = ttk.Frame(lpane)
    ltopbar.pack(fill="x")
    ttk.Button(ltopbar, text="Р’РµСЂРЅСѓС‚СЊСЃСЏ Рє РІС‹Р±СЂР°РЅРЅРѕРјСѓ (СЃС‚СЂРѕРєР° СЃРІРµСЂС…Сѓ)",
               command=lambda: _return_to_pick()).pack(side="left")
    # V83: РёСЃС‚РѕСЂРёСЏ РїРµСЂРµС…РѕРґРѕРІ в†ђ в†’ + РїРѕР»Рµ В«РїРµСЂРµР№С‚Рё Рє РјРѕРґРµР»РёВ» (Enter = РїРµСЂРµС…РѕРґ)
    btn_back = ttk.Button(ltopbar, text="в†ђ РќР°Р·Р°Рґ", width=9,
                          command=lambda: _nav_back())
    btn_back.pack(side="left", padx=(6, 0))
    btn_fwd = ttk.Button(ltopbar, text="Р’РїРµСЂС‘Рґ в†’", width=9,
                         command=lambda: _nav_fwd())
    btn_fwd.pack(side="left")
    ttk.Label(ltopbar, text="РџРµСЂРµР№С‚Рё Рє РјРѕРґРµР»Рё:").pack(side="left", padx=(12, 2))
    e_goto = ttk.Entry(ltopbar, width=22)
    e_goto.pack(side="left")
    ttk.Button(ltopbar, text="РџРµСЂРµР№С‚Рё",
               command=lambda: _goto_entry()).pack(side="left", padx=(4, 0))
    e_goto.bind("<Return>", lambda ev: _goto_entry())
    lsubj = ttk.Label(ltopbar, text="", foreground="#555")
    lsubj.pack(side="left", padx=8)
    lnb = ttk.Notebook(lpane)                  # РќРР–РќР•Р• РѕРєРЅРѕ вЂ” РЅРѕСѓС‚Р±СѓРє СЃРѕ СЃРІРѕРёРјРё СЂРµР¶РёРјР°РјРё-РІРєР»Р°РґРєР°РјРё
    lnb.pack(fill="both", expand=True)
    liv = ttk.Frame(lnb, padding=4)
    lnb.add(liv, text=" Р РѕРґРѕСЃР»РѕРІРЅР°СЏ ")
    lsum = ttk.Label(liv, text="РІС‹Р±РµСЂРё РёР·РґРµР»РёРµ РІ Р›Р®Р‘РћР™ РІРєР»Р°РґРєРµ СЃРІРµСЂС…Сѓ вЂ” РїРѕРєР°Р¶Сѓ СЂРѕРґРѕСЃР»РѕРІРЅСѓСЋ: "
                               "РѕС‚РєСѓРґР° РїСЂРёС€Р»Рѕ В· СЌС‚Рѕ РёР·РґРµР»РёРµ В· С‡С‚Рѕ СЃРґРµР»Р°РЅРѕ РёР· РЅРµРіРѕ В· РєСѓРґР° РІС…РѕРґРёС‚")
    lsum.pack(anchor="w")
    LTCOLS = ("РўРёРї", "РР·РґРµР»РёРµ/С„Р°Р№Р»", "РћР±РѕР·РЅР°С‡РµРЅРёРµ", "РќР°РёРјРµРЅРѕРІР°РЅРёРµ", "РљРѕР»-РІРѕ")
    ltv = ttk.Treeview(liv, columns=LTCOLS, show="tree headings", height=8)
    ltv.heading("#0", text="РґРµСЂРµРІРѕ")
    ltv.column("#0", width=320, anchor="w")
    for c in LTCOLS:
        ltv.heading(c, text=c)
        ltv.column(c, width=150 if c != "РљРѕР»-РІРѕ" else 70, anchor="w")
    lvs = ttk.Scrollbar(liv, orient="vertical", command=ltv.yview)
    ltv.configure(yscrollcommand=lvs.set)
    ltv.pack(side="left", fill="both", expand=True)
    lvs.pack(side="left", fill="y")
    ltv.bind("<<TreeviewOpen>>", lambda ev: ltv_open())

    llinks = ttk.Frame(lnb, padding=4)         # РІС‚РѕСЂР°СЏ РІРєР»Р°РґРєР° РЅРёР¶РЅРµРіРѕ РѕРєРЅР° вЂ” В«Р”РµСЂРµРІРѕ СЃРІСЏР·РµР№В»
    lnb.add(llinks, text=" Р”РµСЂРµРІРѕ СЃРІСЏР·РµР№ ")
    lsum2 = ttk.Label(llinks, text="РІС‹Р±РµСЂРё С‡С‚Рѕ-Р»РёР±Рѕ РІ Р›Р®Р‘РћР™ РІРєР»Р°РґРєРµ СЃРІРµСЂС…Сѓ вЂ” СЃРІСЏР·Рё РїРѕСЃС‚СЂРѕСЏС‚СЃСЏ СЃР°РјРё")
    lsum2.pack(anchor="w")
    lbox = ttk.Frame(llinks)
    lbox.pack(fill="both", expand=True)
    ltv2 = ttk.Treeview(lbox, columns=LTCOLS, show="tree headings", height=8)
    ltv2.heading("#0", text="СЃРІСЏР·Рё   в–І РІРІРµСЂС… / в–ј РІРЅРёР·")
    ltv2.column("#0", width=320, anchor="w")
    for c in LTCOLS:
        ltv2.heading(c, text=c)
        ltv2.column(c, width=150 if c != "РљРѕР»-РІРѕ" else 70, anchor="w")
    lvs2 = ttk.Scrollbar(lbox, orient="vertical", command=ltv2.yview)
    ltv2.configure(yscrollcommand=lvs2.set)
    ltv2.pack(side="left", fill="both", expand=True)
    lvs2.pack(side="left", fill="y")
    ltv2.bind("<<TreeviewOpen>>", lambda ev: ltv2_open())
    # 08.10.2026: Р”Р’РћР™РќРћР™ РєР»РёРє РїРѕ СѓР·Р»Сѓ РЅРёР¶РЅРµРіРѕ РґРµСЂРµРІР° = РЅРёР¶РЅРµРµ РѕРєРЅРѕ РїРµСЂРµСЃС‚СЂР°РёРІР°РµС‚СЃСЏ РЅР° СЌС‚Сѓ РґРµС‚Р°Р»СЊ
    ltv.bind("<Double-1>", lambda ev: _goto_node(ltv, _LTREE, ev))
    ltv2.bind("<Double-1>", lambda ev: _goto_node(ltv2, _LLINKS, ev))
    lout = tk.Text(llinks, height=4, font=("Consolas", 9), bg="#fbfbfb")   # РІС‹РІРѕРґ РєРЅРѕРїРѕРє (РїРµСЂРµРЅРµСЃРµРЅРѕ РёР· В«Р”РµСЂРµРІР°В»)
    lout.pack(fill="x")

    # ==== 07.10.2026: РІРєР»Р°РґРєР° В«Р”РµСЂРµРІРѕ С‚РµРєСЃС‚РѕРј (РІРІРµСЂС…+РІРЅРёР·)В» вЂ” РџРћР›РќРћР• ASCII-РґРµСЂРµРІРѕ РїСЂРѕРёР·РІРѕРґСЃС‚РІР° ====
    ltext = ttk.Frame(lnb, padding=4)
    ltext_sum = ttk.Label(ltext, text="РІС‹Р±РµСЂРё РёР·РґРµР»РёРµ вЂ” РїРѕРєР°Р¶Сѓ РџРћР›РќРћР• РґРµСЂРµРІРѕ: СЃРѕСЃС‚Р°РІ РІРЅРёР· Рё РІС…РѕРґРёРјРѕСЃС‚СЊ РІРІРµСЂС…")
    ltext_sum.pack(anchor="w")
    ltctl = ttk.Frame(ltext)                       # 07.10.2026: СЂР°СЃРєСЂС‹С‚РёРµ РґРµСЂРµРІР°
    ltctl.pack(anchor="w", pady=2)
    ttk.Label(ltctl, text="Р“Р»СѓР±РёРЅР°:").pack(side="left")
    lt_depth = ttk.Spinbox(ltctl, from_=1, to=25, width=4)
    lt_depth.set(6)
    lt_depth.pack(side="left", padx=(2, 8))
    lt_int = ttk.Checkbutton(ltctl, text="РІРЅСѓС‚СЂРµРЅРЅРёРµ РєРѕРґС‹ Creo")
    lt_int.pack(side="left", padx=(0, 8))

    def lt_apply():
        _last["lt_depth"] = int(lt_depth.get() or 6)
        _last["lt_int"] = bool(lt_int.instate(["selected"]))
        _text_tree_show()

    ttk.Button(ltctl, text="РћР±РЅРѕРІРёС‚СЊ", command=lt_apply).pack(side="left")
    ttk.Label(ltctl, text="в†ђ Р”Р’РћР™РќРћР™ РєР»РёРє РїРѕ РёР·РґРµР»РёСЋ = РЅРёР¶РЅРµРµ РѕРєРЅРѕ РїРµСЂРµС…РѕРґРёС‚ РЅР° РЅРµРіРѕ; РїРѕ В«вЂ¦ РµС‰С‘ NВ» вЂ” РІРµСЃСЊ СЃРїРёСЃРѕРє",
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

    # ==== 07.10.2026: РІРєР»Р°РґРєР° В«РСЃС‚РѕСЂРёСЏ С„Р°Р№Р»Р°В» вЂ” Р’РЎРЇ РёСЃС‚РѕСЂРёСЏ РїСЂР°РІРѕРє РїРѕ Р’РЎР•Рњ С„Р°Р№Р»Р°Рј РёР·РґРµР»РёСЏ ====
    lhist = ttk.Frame(lnb, padding=4)
    lhist_sum = ttk.Label(lhist, text="РІС‹Р±РµСЂРё РёР·РґРµР»РёРµ вЂ” РїРѕРєР°Р¶Сѓ Р’РЎР® РёСЃС‚РѕСЂРёСЋ РµРіРѕ С„Р°Р№Р»РѕРІ: "
                                      "СЂРµРІРёР·РёСЏ, РґР°С‚Р°, РєС‚Рѕ, РєРѕРјРїСЊСЋС‚РµСЂ, РІРµСЂСЃРёСЏ Creo, С‡С‚Рѕ РёР·РјРµРЅРµРЅРѕ")
    lhist_sum.pack(anchor="w")
    var_hide = tk.BooleanVar(value=False)      # 07.10.2026: СЃРєСЂС‹С‚СЊ СѓРЅР°СЃР»РµРґРѕРІР°РЅРЅС‹Рµ (РїРµСЂРµРЅРµСЃС‘РЅРЅС‹Рµ РёР· РёСЃС…РѕРґРЅРѕР№)
    ttk.Checkbutton(lhist, text="СЃРєСЂС‹С‚СЊ СѓРЅР°СЃР»РµРґРѕРІР°РЅРЅС‹Рµ (РїРµСЂРµРЅРµСЃС‘РЅРЅС‹Рµ РїСЂРё РєРѕРїРёСЂРѕРІР°РЅРёРё)",
                    variable=var_hide, command=lambda: _hist_show()).pack(anchor="w")
    HCOLS = ("Р¤Р°Р№Р»", "Р РµРІРёР·РёСЏ", "Р”Р°С‚Р°", "РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ", "РљРѕРјРїСЊСЋС‚РµСЂ", "Р’РµСЂСЃРёСЏ Creo", "Р§С‚Рѕ РёР·РјРµРЅРµРЅРѕ")
    hbox = ttk.Frame(lhist)
    hbox.pack(fill="both", expand=True)
    ltv_h = ttk.Treeview(hbox, columns=HCOLS, show="headings", height=8)
    ltv_h.tag_configure("inh", foreground="#8a8a8a")   # СѓРЅР°СЃР»РµРґРѕРІР°РЅРЅС‹Рµ Р·Р°РїРёСЃРё вЂ” СЃРµСЂС‹Рј
    for _c in HCOLS:
        ltv_h.heading(_c, text=_c)
        ltv_h.column(_c, width=320 if _c == "Р§С‚Рѕ РёР·РјРµРЅРµРЅРѕ" else 118, anchor="w")
    hvs = ttk.Scrollbar(hbox, orient="vertical", command=ltv_h.yview)
    hhs = ttk.Scrollbar(hbox, orient="horizontal", command=ltv_h.xview)
    ltv_h.configure(yscrollcommand=hvs.set, xscrollcommand=hhs.set)
    hbox.rowconfigure(0, weight=1)
    hbox.columnconfigure(0, weight=1)
    ltv_h.grid(row=0, column=0, sticky="nsew")
    hvs.grid(row=0, column=1, sticky="ns")
    hhs.grid(row=1, column=0, sticky="ew")

    # ==== 04.10.2026: РІРєР»Р°РґРєР° В«РЎРІРѕР№СЃС‚РІР° РґРµС‚Р°Р»РёВ» вЂ” РїР»РѕС‰Р°РґСЊ, РўРў, РїР°СЂР°РјРµС‚СЂС‹, Р РђР—РњР•Р Р«, С‡РµСЂС‚РµР¶Рё ====
    lprop = ttk.Frame(lnb, padding=4)
    lnb.add(lprop, text=" РЎРІРѕР№СЃС‚РІР° РґРµС‚Р°Р»Рё ")
    lnb.add(ltext, text=" Р”РµСЂРµРІРѕ С‚РµРєСЃС‚РѕРј (РІРІРµСЂС…+РІРЅРёР·) ")   # 4-СЏ РІРєР»Р°РґРєР°: РїРѕР»РЅРѕРµ РґРµСЂРµРІРѕ С‚РµРєСЃС‚РѕРј (РІРІРµСЂС…+РІРЅРёР·)
    lnb.add(lhist, text=" РСЃС‚РѕСЂРёСЏ С„Р°Р№Р»Р° ")                 # 5-СЏ: РёСЃС‚РѕСЂРёСЏ РїСЂР°РІРѕРє РІСЃРµС… С„Р°Р№Р»РѕРІ РёР·РґРµР»РёСЏ

    # ==== 08.10.2026 (V84): РІРєР»Р°РґРєР° В«РћР±Р·РѕСЂВ» вЂ” СЃРІРѕРґРєР° РїРѕ Р’РЎР•Р™ Р±Р°Р·Рµ (РІС‹Р±РѕСЂ РІС‹С€Рµ РЅРµ РІР°Р¶РµРЅ) ====
    lov = ttk.Frame(lnb, padding=4)
    lnb.add(lov, text=" РћР±Р·РѕСЂ ")                           # 6-СЏ: СЃС‚Р°С‚РёСЃС‚РёРєР°/РіРѕСЂСЏС‡РёРµ/СЃС‚Р°СЂС‹Рµ/СЃРёСЂРѕС‚С‹/РґСѓР±Р»Рё
    ovs_sum = ttk.Label(lov, text="СЃРІРѕРґРєР° РїРѕ Р±Р°Р·Рµ: СЃС‚Р°С‚РёСЃС‚РёРєР° В· РіРѕСЂСЏС‡РёРµ РїСЂР°РІРєРё В· СЃС‚Р°СЂС‹Рµ В· СЃРёСЂРѕС‚С‹ В· РґСѓР±Р»Рё В· Р°РІС‚РѕСЂС‹")
    ovs_sum.pack(anchor="w")
    ovctl = ttk.Frame(lov)
    ovctl.pack(anchor="w", pady=2)
    ttk.Button(ovctl, text="РћР±РЅРѕРІРёС‚СЊ", command=lambda: _overview_show(True)).pack(side="left")
    ttk.Label(ovctl, text="в†ђ СЃРІРѕРґРєР° РїРѕ Р’РЎР•Р™ Р±Р°Р·Рµ; РіРѕСЂСЏС‡РёРµ вЂ” 30 РґРЅРµР№, СЃС‚Р°СЂС‹Рµ вЂ” 2 РіРѕРґР°",
              foreground="#666").pack(side="left", padx=6)
    ovbox = ttk.Frame(lov)
    ovbox.pack(fill="both", expand=True)
    otv = tk.Text(ovbox, font=("Consolas", 9), wrap="none", bg="#fbfbfb", state="disabled")
    ovs = ttk.Scrollbar(ovbox, orient="vertical", command=otv.yview)
    otv.configure(yscrollcommand=ovs.set)
    ovs.pack(side="right", fill="y")
    otv.pack(side="left", fill="both", expand=True)

    # ==== 09.10.2026 (V85): РІРєР»Р°РґРєР° В«Р“СЂР°С„В» вЂ” РєР°СЂС‚Р° СЂРѕРґРѕСЃР»РѕРІРЅРѕР№ РЅР° canvas (РІРІРµСЂС…+РІРЅРёР·, РєР»РёРє=РїРµСЂРµС…РѕРґ) ====
    lgr = ttk.Frame(lnb, padding=4)
    lnb.add(lgr, text=" Р“СЂР°С„ ")                            # 7-СЏ: РІРёР·СѓР°Р»СЊРЅР°СЏ РєР°СЂС‚Р° СЃРІСЏР·РµР№
    grs = ttk.Label(lgr, text="РІС‹Р±РµСЂРё РёР·РґРµР»РёРµ вЂ” РїРѕРєР°Р¶Сѓ РєР°СЂС‚Сѓ: СЃРѕСЃС‚Р°РІ РІРЅРёР·, РІС…РѕРґРёРјРѕСЃС‚СЊ РІРІРµСЂС…, РёР· С‡РµРіРѕ СЃРґРµР»Р°РЅР°")
    grs.pack(anchor="w")
    grctl = ttk.Frame(lgr)
    grctl.pack(anchor="w", pady=2)
    ttk.Button(grctl, text="РћР±РЅРѕРІРёС‚СЊ", command=lambda: _graph_show(True)).pack(side="left")
    ttk.Label(grctl, text="РІРЅРёР·:").pack(side="left", padx=(8, 2))
    gr_dd = ttk.Spinbox(grctl, from_=1, to=8, width=3)
    gr_dd.set(4)
    gr_dd.pack(side="left")
    ttk.Label(grctl, text="РІРІРµСЂС…:").pack(side="left", padx=(6, 2))
    gr_du = ttk.Spinbox(grctl, from_=1, to=6, width=3)
    gr_du.set(3)
    gr_du.pack(side="left")
    ttk.Button(grctl, text="+", width=3, command=lambda: _graph_zoom(1.2)).pack(side="left", padx=(8, 0))
    ttk.Button(grctl, text="в€’", width=3, command=lambda: _graph_zoom(1 / 1.2)).pack(side="left")
    ttk.Label(grctl, text=" в†ђ Р”Р’РћР™РќРћР™ РєР»РёРє РїРѕ СѓР·Р»Сѓ = РїРµСЂРµР№С‚Рё РЅР° РЅРµРіРѕ; РєРѕР»РµСЃРѕ = Р·СѓРј; С‚СЏРЅСѓС‚СЊ вЂ” Р·Р° РїСѓСЃС‚РѕРµ РјРµСЃС‚Рѕ",
              foreground="#666").pack(side="left", padx=6)
    grbox = ttk.Frame(lgr)
    grbox.pack(fill="both", expand=True)
    gr_canvas = tk.Canvas(grbox, bg="#fbfbfb", highlightthickness=0)
    gr_ys = ttk.Scrollbar(grbox, orient="vertical", command=gr_canvas.yview)
    gr_xs = ttk.Scrollbar(grbox, orient="horizontal", command=gr_canvas.xview)
    gr_canvas.configure(yscrollcommand=gr_ys.set, xscrollcommand=gr_xs.set)
    gr_ys.pack(side="right", fill="y")
    gr_xs.pack(side="bottom", fill="x")
    gr_canvas.pack(side="left", fill="both", expand=True)
    lpsum = ttk.Label(lprop, text="РІС‹Р±РµСЂРё РёР·РґРµР»РёРµ вЂ” РїРѕРєР°Р¶Сѓ РїР»РѕС‰Р°РґСЊ, С‚РµС…С‚СЂРµР±РѕРІР°РЅРёСЏ, "
                                   "С‡РёСЃР»РѕРІС‹Рµ РїР°СЂР°РјРµС‚СЂС‹, Р РђР—РњР•Р Р« Рё СЃРІСЏР·Р°РЅРЅС‹Рµ С‡РµСЂС‚РµР¶Рё")
    lpsum.pack(anchor="w")
    pbox = ttk.Frame(lprop)
    pbox.pack(fill="both", expand=True)
    PROPCOLS = ("РџРѕРєР°Р·Р°С‚РµР»СЊ", "Р—РЅР°С‡РµРЅРёРµ")
    ptv = ttk.Treeview(pbox, columns=PROPCOLS, show="headings", height=8)
    ptv.heading("РџРѕРєР°Р·Р°С‚РµР»СЊ", text="РџРѕРєР°Р·Р°С‚РµР»СЊ")
    ptv.heading("Р—РЅР°С‡РµРЅРёРµ", text="Р—РЅР°С‡РµРЅРёРµ")
    ptv.column("РџРѕРєР°Р·Р°С‚РµР»СЊ", width=250, anchor="w")
    ptv.column("Р—РЅР°С‡РµРЅРёРµ", width=620, anchor="w")
    pvs = ttk.Scrollbar(pbox, orient="vertical", command=ptv.yview)
    ptv.configure(yscrollcommand=pvs.set)
    ptv.pack(side="left", fill="both", expand=True)
    pvs.pack(side="left", fill="y")

    def _fmt(x):
        """Р§РёСЃР»Рѕ вЂ” Р±РµР· С…РІРѕСЃС‚РѕРІС‹С… РЅСѓР»РµР№; СЃС‚СЂРѕРєР° вЂ” РєР°Рє РµСЃС‚СЊ."""
        if isinstance(x, float):
            return ("%.2f" % x).rstrip("0").rstrip(".")
        return x

    def _prop_show(model):
        """РџРѕРєР°Р·Р°С‚СЊ СЃРІРѕРґРЅС‹Рµ СЃРІРѕР№СЃС‚РІР° РёР·РґРµР»РёСЏ РёР· С„Р°Р№Р»Р° РјРѕРґРµР»Рё (Р±РµР· Р±Р°Р·С‹ PLM)."""
        ptv.delete(*ptv.get_children())
        model = eng.stem(model or "")
        if not model:
            lpsum.config(text="РІС‹Р±РµСЂРё РёР·РґРµР»РёРµ вЂ” РїРѕРєР°Р¶Сѓ РїР»РѕС‰Р°РґСЊ, С‚РµС…С‚СЂРµР±РѕРІР°РЅРёСЏ, "
                               "С‡РёСЃР»РѕРІС‹Рµ РїР°СЂР°РјРµС‚СЂС‹, Р РђР—РњР•Р Р« Рё СЃРІСЏР·Р°РЅРЅС‹Рµ С‡РµСЂС‚РµР¶Рё")
            return
        # РїСѓС‚СЊ Р±РµСЂС‘Рј РёР· Р±Р°Р·С‹ (Р°РєС‚РёРІРЅРѕР№), РїРѕСЃР»РµРґРЅСЏСЏ РІРµСЂСЃРёСЏ РёР·РґРµР»РёСЏ
        path = latest_path(model)
        if not path:
            lpsum.config(text="РІ Р±Р°Р·Рµ РЅРµС‚ РЅРё РѕРґРЅРѕРіРѕ С„Р°Р№Р»Р° РёР·РґРµР»РёСЏ: %s" % model)
            return
        if not os.path.isfile(path):
            lpsum.config(text="С„Р°Р№Р» СѓРєР°Р·Р°РЅ РІ Р±Р°Р·Рµ, РЅРѕ РѕС‚СЃСѓС‚СЃС‚РІСѓРµС‚ РЅР° РґРёСЃРєРµ: %s" % path)
            return
        try:
            raw = read_bytes(path, 0)          # 0 = Р±РµР· РѕРіСЂР°РЅРёС‡РµРЅРёСЏ СЂР°Р·РјРµСЂР°: СЃРІРѕР№СЃС‚РІР° РЅСѓР¶РЅС‹ РІСЃРµРіРґР°
        except Exception as e:
            lpsum.config(text="РЅРµ РїСЂРѕС‡РёС‚Р°С‚СЊ С„Р°Р№Р»: %s (%s)" % (os.path.basename(path), e))
            return
        if not raw:
            lpsum.config(text="РїСѓСЃС‚РѕР№/Р±РёС‚С‹Р№ С„Р°Р№Р»: %s" % os.path.basename(path))
            return

        sec = sections(raw)
        area = real_value(raw, "surfarea")
        notes = tech_notes(raw)               # 04.10.2026: СЃ РѕС‚СЃРµРІРѕРј СЃР»СѓР¶РµР±РЅС‹С… РїРѕРґРїРёСЃРµР№
        nums = sorted(numeric_params(raw).items(), key=lambda kv: kv[0])

        def add(k, v, bold=False):
            ptv.insert("", "end", values=(k, v),
                       tags=("hdr",) if bold else ())

        add("Р¤Р°Р№Р»", os.path.basename(path), True)
        add("РџРѕР»РЅС‹Р№ РїСѓС‚СЊ", path)
        v = real_value(raw, "volume")
        add("РћР±СЉС‘Рј, РјРјВі", _fmt(v) if v else "вЂ” РЅРµС‚ РІ С„Р°Р№Р»Рµ")
        add("РџР»РѕС‰Р°РґСЊ РїРѕРІРµСЂС…РЅРѕСЃС‚Рё, РјРјВІ", _fmt(area) if area else "вЂ” РЅРµС‚ РІ С„Р°Р№Р»Рµ")
        # вљ пёЏ С€С‚Р°С‚РЅС‹Р№ outline_mm РЅР° Р¶РёРІС‹С… С„Р°Р№Р»Р°С… РґР°С‘С‚ РЅРµ РіР°Р±Р°СЂРёС‚ (РѕРґРЅРѕ С‡РёСЃР»Рѕ 31.59 Сѓ РґРµС‚Р°Р»Рё
        # СЃ СЂРµР·СЊР±РѕР№ Рњ12), РїРѕСЌС‚РѕРјСѓ РїРѕРєР°Р·С‹РІР°РµРј РµРіРѕ С‡РµСЃС‚РЅРѕ вЂ” РєР°Рє В«РЅРµРїРѕРґС‚РІРµСЂР¶РґС‘РЅРЅС‹Р№ СЂР°Р·Р±РѕСЂВ»
        ol = outline_mm(raw, sec)
        add("Р“Р°Р±Р°СЂРёС‚, РјРј", ("%s  в†ђ С€С‚Р°С‚РЅС‹Р№ СЂР°Р·Р±РѕСЂ, РќР• РїРѕРґС‚РІРµСЂР¶РґС‘РЅ" % ", ".join(
            "%.2f" % x for x in ol)) if ol else "вЂ” С„РѕСЂРјР°С‚ РЅРµ РїРѕРґС‚РІРµСЂР¶РґС‘РЅ")
        add("РўРµС…РЅРёС‡РµСЃРєРёРµ С‚СЂРµР±РѕРІР°РЅРёСЏ", "  |  ".join(notes) if notes else "вЂ” РЅРµС‚")
        add("Р§РёСЃР»РѕРІС‹С… РїР°СЂР°РјРµС‚СЂРѕРІ", str(len(nums)))
        for k, val in nums[:60]:
            add("   " + k, _fmt(val))
        # 06.10.2026: Р РђР—РњР•Р Р« РґРµС‚Р°Р»Рё Рё РёСЃС‚РѕСЂРёСЏ РёР·РјРµРЅРµРЅРёР№ (d_dims / dim_history)
        dims = read_dims_all(raw)
        add("Р Р°Р·РјРµСЂРѕРІ РІ С„Р°Р№Р»Рµ", str(len(dims)) if dims else "вЂ” РЅРµС‚ (С„РѕСЂРјР°С‚ РёР»Рё РёС… РЅРµС‚)")
        for dk in sorted(dims, key=lambda s: int(re.sub(r"\D", "", s) or 0)):
            add("   %s, РјРј" % dk, _fmt(dims[dk]))
        hist = read_history(raw)
        if hist:
            h0 = hist[0]
            add("РџРѕСЃР»РµРґРЅРµРµ РёР·РјРµРЅРµРЅРёРµ (С„Р°Р№Р»)", "%s: %s в†’ %s" % (
                h0["name"],
                _fmt(h0["old"]) if h0["old"] is not None else "вЂ”",
                _fmt(h0["new"])))
        else:
            add("РџРѕСЃР»РµРґРЅРµРµ РёР·РјРµРЅРµРЅРёРµ (С„Р°Р№Р»)", "вЂ” РЅРµС‚ Р±Р»РѕРєР° diff_vals")
        dims_db, hist_db = archive_dims(model)
        if dims_db:
            add("Р Р°Р·РјРµСЂРѕРІ РІ Р°СЂС…РёРІРµ (Р±Р°Р·Р°)", str(len(dims_db)))
        if hist_db:
            add("РСЃС‚РѕСЂРёСЏ СЂР°Р·РјРµСЂРѕРІ (Р±Р°Р·Р°)", "%d Р·Р°РїРёСЃРµР№" % len(hist_db))
            for (dt, dm, ov, nv, kd) in hist_db[:40]:
                add("   %s %s" % (dt, dm),
                    "%s в†’ %s  (%s)" % (ov or "вЂ”", nv or "", kd or ""))
        # 06.10.2026 (V43): РРЎРўРћР РРЇ РїРѕ РђР РҐРР’РќР«Рњ РЎР Р•Р—РђРњ вЂ” В«Р±РѕРµРІР°СЏ РёРЅС„РѕСЂРјР°С†РёСЏВ» РёР· СЃРѕР±СЂР°РЅРЅС‹С… Р±Р°Р·
        snaps_db, chg_db = archive_history(model)
        if snaps_db:
            add("РђР РҐРР’: СЃСЂРµР·РѕРІ РёР·РґРµР»РёСЏ", "%d (РѕС‚ %s РґРѕ %s)"
                % (len(snaps_db), snaps_db[0][0], snaps_db[-1][0]))
            for (dt, k, mv, rev, au, cr) in snaps_db[:40]:
                add("   СЃСЂРµР· %s" % dt,
                    "С„Р°Р№Р»РѕРІ %s В· РѕР±СЉС‘Рј %s В· СЂРµРІ. %s В· Р°РІС‚РѕСЂ %s В· Creo %s"
                    % (k, _vol_str(mv) if mv else "вЂ”", rev or "вЂ”", au or "вЂ”", cr or "вЂ”"))
        else:
            add("РђР РҐРР’: СЃСЂРµР·С‹ РёР·РґРµР»РёСЏ", "вЂ” РЅРµС‚ (Р°СЂС…РёРІ РЅРµ СЃР»РёС‚ РІ Р±Р°Р·Сѓ)")
        if chg_db:
            add("РђР РҐРР’: РїСЂР°РІРѕРє РёР·РґРµР»РёСЏ", str(len(chg_db)))
            for (ts, d) in chg_db[:40]:
                add("   %s" % (ts or "?"), (d or "")[:120])
        dwg = dwg_models(raw)
        add("РџРѕРєР°Р·С‹РІР°РµС‚ РјРѕРґРµР»Рё (РµСЃР»Рё СЌС‚Рѕ С‡РµСЂС‚С‘Р¶)", ", ".join(dwg) if dwg else "вЂ” РЅРµ С‡РµСЂС‚С‘Р¶")
        lpsum.config(text="%s вЂ” СЃРІРѕР№СЃС‚РІР° РёР· Р¤РђР™Р›Рђ РјРѕРґРµР»Рё (РїР»РѕС‰Р°РґСЊ, РўРў, РїР°СЂР°РјРµС‚СЂС‹, "
                          "СЂР°Р·РјРµСЂС‹, С‡РµСЂС‚РµР¶Рё)" % model)

    def _live_vals(m, i, qty=""):
        role = (i[5] or "") if len(i) > 5 else ""
        kind = "РѕСЃРЅР°СЃС‚РєР°" if role == "MFG" else ("РёР·РґРµР»РёРµ" if (i[6] or i[7]) else "РґРµС‚Р°Р»СЊ")
        return (kind, m, i[0] or "", i[1] or "", qty)

    _LTREE = {}
    _LLINKS = {}                               # СѓР·РµР» РЅРёР¶РЅРµРіРѕ В«РґРµСЂРµРІР° СЃРІСЏР·РµР№В» -> (РјРѕРґРµР»СЊ, СЂРµР¶РёРј down/up)

    def _branch_updown(node, model):
        """Р’РµС‚РєР° РёР·РґРµР»РёСЏ РІ РЅРёР¶РЅРµРј РѕРєРЅРµ вЂ” С‚РѕС‚ Р¶Рµ СЃС‚СЂРѕРёС‚РµР»СЊ, С‡С‚Рѕ Рё РІРѕ РІРєР»Р°РґРєРµ В«Р”РµСЂРµРІРѕВ»."""
        return _fill_node(ltv, node, model, with_up=True)

    def _ltv_model(node):
        """РњРѕРґРµР»СЊ СѓР·Р»Р° РЅРёР¶РЅРµРіРѕ РґРµСЂРµРІР° (РµСЃР»Рё СѓР·РµР» вЂ” РёР·РґРµР»РёРµ)."""
        return _LTREE.get(node, "")

    def ltv_open(event=None):
        node = ltv.focus()
        model = _ltv_model(node)
        if not model:
            return
        kids = ltv.get_children(node)
        if kids and ltv.item(kids[0], "text") == "Р·Р°РіСЂСѓР·РєР°вЂ¦":
            ltv.delete(*kids)
            _fill_node(ltv, node, model, with_up=True)      # С‚РѕС‚ Р¶Рµ СЃС‚СЂРѕРёС‚РµР»СЊ, С‡С‚Рѕ Рё РІРѕ РІРєР»Р°РґРєРµ В«Р”РµСЂРµРІРѕВ»

    _PLM = {"data": None}

    def _plm_data_ref():
        if _PLM["data"] is None:
            _PLM["data"] = eng.plm_tree_data()
        return _PLM["data"]

    def live_auto():
        """РћРќР›РђР™Рќ: РЅРёР¶РЅРµРµ РґРµСЂРµРІРѕ РџР›Рњ СЃС‚СЂРѕРёС‚СЃСЏ РЎРђРњРћ вЂ” РїСЂРё РѕС‚РєСЂС‹С‚РёРё, РїРѕСЃР»Рµ С„РёР»СЊС‚СЂР° Рё РїРѕСЃР»Рµ СЃРєР°РЅР°."""
        ltv.delete(*ltv.get_children())
        _LTREE.clear()
        pat = e_filter.get().strip()
        if pat:                                   # С„РёР»СЊС‚СЂ вЂ” РґРµСЂРµРІСЊСЏ РїРѕ РЅР°Р№РґРµРЅРЅС‹Рј РІРѕ Р’РЎР•Р™ Р±Р°Р·Рµ
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
            lsum.config(text="РѕРЅР»Р°Р№РЅ РїРѕ С„РёР»СЊС‚СЂСѓ: СЃРѕРІРїР°РґРµРЅРёР№ %d в†’ РґРµСЂРµРІСЊРµРІ %d" % (len(rows), shown))
            return
        tops, children, info, derived = _plm_data_ref()
        rn = ltv.insert("", "end", open=True,
                        text="Р’РЎРЃ РџР РћРР—Р’РћР”РЎРўР’Рћ (РџР›Рњ) вЂ” РІРµСЂС…РЅРёС… СЃР±РѕСЂРѕРє %d" % len(tops),
                        values=("РєРѕСЂРµРЅСЊ", "", "", "", ""))
        for m in tops:
            n = ltv.insert(rn, "end", text=m,
                           values=_live_vals(m, info.get(m, ("", "", "", 0, "", "", 0, 0))))
            _LTREE[n] = m
            ltv.insert(n, "end", text="Р·Р°РіСЂСѓР·РєР°вЂ¦")
        lsum.config(text="РґРµСЂРµРІРѕ РџР›Рњ: РІРµСЂС…РЅРёС… СЃР±РѕСЂРѕРє %d В· СЂР°СЃРєСЂС‹РІР°Р№ СѓР·Р»С‹ (СЃРѕСЃС‚Р°РІ / Р·Р°РіРѕС‚РѕРІРєР°-РѕС‚Р»РёРІРєР°) вЂ” СЃС‚СЂРѕРёС‚СЃСЏ СЃР°РјРѕ"
                    % len(tops))

    _last = {"model": ""}                      # РІС‹Р±СЂР°РЅРЅР°СЏ РјРѕРґРµР»СЊ вЂ” РѕР±С‰Р°СЏ РґР»СЏ РѕР±РµРёС… РІРєР»Р°РґРѕРє РЅРёР·Р°

    def _prod_show(model):
        """Р’РєР»Р°РґРєР° В«Р”РµСЂРµРІРѕ РїСЂРѕРёР·РІРѕРґСЃС‚РІР°В»: СЃРѕСЃС‚Р°РІ РІРЅРёР· + Р·Р°РіРѕС‚РѕРІРєР°/РѕС‚Р»РёРІРєР° + РІС…РѕРґРёРјРѕСЃС‚СЊ РІРІРµСЂС…."""
        ltv.delete(*ltv.get_children())
        _LTREE.clear()
        info = eng.models_info([model]).get(model, ("", "", "", 0, "", "", 0, 0))
        rn = ltv.insert("", "end", open=True, text=model, values=_live_vals(model, info))
        _LTREE[rn] = model                           # V81: РєРѕСЂРµРЅСЊ В«Р РѕРґРѕСЃР»РѕРІРЅРѕР№В» С‚РѕР¶Рµ РєР»РёРєР°Р±РµР»РµРЅ
        der, ups, dn = _branch_updown(rn, model)
        try:
            ltv.yview_moveto(0)                 # РїРѕРєР°Р·Р°С‚СЊ РЅР°С‡Р°Р»Рѕ РґРµСЂРµРІР°
            ltv.see(rn)
        except Exception:
            pass
        lsum.config(text="СЂРѕРґРѕСЃР»РѕРІРЅР°СЏ В«%sВ»: СЃРѕСЃС‚Р°РІ %d В· РІС…РѕРґРёС‚ РІ СЃР±РѕСЂРѕРє %d (РІСЃРµ СѓСЂРѕРІРЅРё) В· Р·Р°РіРѕС‚РѕРІРѕРє/РѕС‚Р»РёРІРѕРє %d"
                    % (model, dn, ups, der))

    def _links_show(model):
        """Р’РєР»Р°РґРєР° В«Р”РµСЂРµРІРѕ СЃРІСЏР·РµР№В»: в–І РІРІРµСЂС… вЂ” РіРґРµ РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ; в–ј РІРЅРёР· вЂ” СЃРѕСЃС‚Р°РІ + РѕС‚СЂР°Р¶РµРЅРёСЏ + РЅР°СЃР»РµРґРѕРІР°РЅРёРµ."""
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
        _LLINKS[rn] = (model, "down")                # V81: РєРѕСЂРµРЅСЊ В«Р”РµСЂРµРІР° СЃРІСЏР·РµР№В» С‚РѕР¶Рµ РєР»РёРєР°Р±РµР»РµРЅ

        # в–ј РІРЅРёР· вЂ” РЎРћРЎРўРђР’ (Р»РµРЅРёРІР°СЏ Р·Р°РіСЂСѓР·РєР° СѓСЂРѕРІРЅРµР№)
        dn = ltv2.insert(rn, "end", open=False, text="в–ј СЃРѕСЃС‚Р°РІ (РІРЅРёР·)")
        if not kids:
            ltv2.insert(dn, "end", text="вЂ” РІ Р±Р°Р·Рµ РЅРµС‚ СЃРѕСЃС‚Р°РІР°")
        for c, q in kids:
            nn = ltv2.insert(dn, "end", text="%s  x%d" % (c, q), values=iv(c, "x%d" % q))
            _LLINKS[nn] = (c, "down")
            ltv2.insert(nn, "end", text="Р·Р°РіСЂСѓР·РєР°вЂ¦")

        # в–ј РІРЅРёР· вЂ” РћРўР РђР–Р•РќРРЇ (РєС‚Рѕ СЃРґРµР»Р°РЅ РР— СЌС‚РѕР№ РјРѕРґРµР»Рё) вЂ” РѕРЅР° РґР»СЏ РЅРёС… В«РїРµСЂРµСЃРѕС…СЂР°РЅС‘РЅ РёСЃС‚РѕС‡РЅРёРєВ»
        ref = ltv2.insert(rn, "end", open=bool(refl), text="в–ј РёР· РЅРµС‘ РїРµСЂРµСЃРѕС…СЂР°РЅРµРЅРѕ (РѕС‚СЂР°Р¶РµРЅРёСЏ): %d" % len(refl))
        if not refl:
            ltv2.insert(ref, "end", text="вЂ” РѕР±СЂР°С‚РЅС‹С… СЃРІСЏР·РµР№ РЅРµС‚")
        for c, k in refl:
            kd = {"РЅР°СЃР»РµРґРѕРІР°РЅРёРµ": "Р·Р°РіРѕС‚РѕРІРєР°", "РїСЂРѕРёР·РІРѕРґРЅР°СЏ": "РѕС‚Р»РёРІРєР°"}.get(k, "Р·Р°РіРѕС‚РѕРІРєР°/РѕС‚Р»РёРІРєР°")
            ltv2.insert(ref, "end", text="%s: %s" % (kd, c), values=("РѕС‚СЂР°Р¶РµРЅРёРµ", c, "", "", ""))

        # в–ј РІРЅРёР· вЂ” РќРђРЎР›Р•Р”РћР’РђРќРќРђРЇ Р“Р•РћРњР•РўР РРЇ (Р·Р°РіРѕС‚РѕРІРєРё/РѕС‚Р»РёРІРєРё СЌС‚РѕР№ РјРѕРґРµР»Рё) вЂ” РѕРЅР° РџР•Р Р•РЎРћРҐР РђРќР•РќРђ РР— РЅРёС…
        inh = ltv2.insert(rn, "end", open=bool(bases),
                          text="в–ј РѕРЅР° РїРµСЂРµСЃРѕС…СЂР°РЅРµРЅР° РёР· (Р·Р°РіРѕС‚РѕРІРєР°/РѕС‚Р»РёРІРєР°): %d" % len(bases))
        if not bases:
            ltv2.insert(inh, "end", text="вЂ” РЅР°СЃР»РµРґРѕРІР°РЅРёСЏ РЅРµС‚")
        for b, k in bases:
            kd = {"РЅР°СЃР»РµРґРѕРІР°РЅРёРµ": "Р·Р°РіРѕС‚РѕРІРєР°", "РїСЂРѕРёР·РІРѕРґРЅР°СЏ": "РѕС‚Р»РёРІРєР°",
                  "hash": "Р·Р°РіРѕС‚РѕРІРєР°/РѕС‚Р»РёРІРєР°"}.get(k, "Р·Р°РіРѕС‚РѕРІРєР°/РѕС‚Р»РёРІРєР°")
            ltv2.insert(inh, "end", text="в—„ %s: %s" % (kd, b or "РёРјСЏ РЅРµ РЅР°Р№РґРµРЅРѕ (РІ С„Р°Р№Р»Рµ С‚РѕР»СЊРєРѕ РєРѕРґ)"),
                        values=(kd, b or "вЂ”", "", "", ""))

        # в–І РІРІРµСЂС… вЂ” Р“Р”Р• РРЎРџРћР›Р¬Р—РЈР•РўРЎРЇ (РІСЃРµ СЃР±РѕСЂРєРё, РІСЃРµ СѓСЂРѕРІРЅРё)
        n_up = len(up)
        un = ltv2.insert(rn, "end", open=True, text="в–І РіРґРµ РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏ (РІРІРµСЂС…): СЃР±РѕСЂРѕРє РІ С†РµРїРѕС‡РєРµ %d" % n_up)
        if not up:
            ltv2.insert(un, "end", text="вЂ” РЅРё РІ РѕРґРЅСѓ СЃР±РѕСЂРєСѓ РЅРµ РІС…РѕРґРёС‚ (РІРµСЂС…РЅРµРµ РёР·РґРµР»РёРµ)")
        else:
            _fill_up(un, model, up, info, 1, frozenset((model,)))

        try:
            ltv2.yview_moveto(0)
            ltv2.see(rn)
        except Exception:
            pass
        lsum2.config(text="СЃРІСЏР·Рё: %s вЂ” СЃРѕСЃС‚Р°РІ %d В· РёР· РЅРµС‘ РїРµСЂРµСЃРѕС…СЂР°РЅРµРЅРѕ %d В· РїРµСЂРµСЃРѕС…СЂР°РЅРµРЅР° РёР· %d В· СЃР±РѕСЂРѕРє РІРІРµСЂС… %d"
                     % (model, len(kids), len(refl), len(bases), n_up))

    def _fill_up(parent_node, model, up, info, depth, seen):
        """Р’РµС‚РєР° В«РіРґРµ РёСЃРїРѕР»СЊР·СѓРµС‚СЃСЏВ»: СЂРµРєСѓСЂСЃРёРІРЅРѕ РїРѕ РєР°СЂС‚Рµ plm_up_data (РІСЃРµ СЃР±РѕСЂРєРё, РІСЃРµ СѓСЂРѕРІРЅРё)."""
        for p, q in up.get(model, []):
            if p in seen:
                continue
            nn = ltv2.insert(parent_node, "end", text="%s  в†‘ x%d" % (p, q),
                             values=_live_vals(p, info.get(p, ("", "", "", 0, "", "", 0, 0)), "x%d" % q))
            _LLINKS[nn] = (p, "up")
            if depth < 8:
                _fill_up(nn, p, up, info, depth + 1, seen | {p})

    def ltv2_open(event=None):
        """Р Р°СЃРєСЂС‹С‚РёРµ СѓР·Р»Р° В«Р”РµСЂРµРІР° СЃРІСЏР·РµР№В»: Р»РµРЅРёРІР°СЏ РґРѕСЃС‚СЂРѕР№РєР° СЃРѕСЃС‚Р°РІР°/РІС…РѕРґРёРјРѕСЃС‚Рё РїРѕ Р±Р°Р·Рµ."""
        node = ltv2.focus()
        rec = _LLINKS.get(node)
        if not rec:
            return
        c_model, mode = rec
        kids = ltv2.get_children(node)
        if not (kids and ltv2.item(kids[0], "text") == "Р·Р°РіСЂСѓР·РєР°вЂ¦"):
            return
        ltv2.delete(*kids)
        info = eng.models_info([c_model]).get(c_model, ("", "", "", 0, "", "", 0, 0))
        if mode == "down":
            pairs = [(c, q, "%s  x%d" % (c, q), "x%d" % q) for c, q in eng.plm_children(c_model)]
        else:
            pairs = [(p, q, "%s  в†‘ x%d" % (p, q), "в†‘ x%d" % q) for p, q in eng.plm_parents(c_model)]
        for nm, q, label, qv in pairs:
            nn = ltv2.insert(node, "end", text=label,
                             values=_live_vals(nm, info.get(nm, ("", "", "", 0, "", "", 0, 0)), qv))
            _LLINKS[nn] = (nm, mode)
            ltv2.insert(nn, "end", text="Р·Р°РіСЂСѓР·РєР°вЂ¦")

    def _made_window(mdl):
        """РћРєРЅРѕ: Р’Р•РЎР¬ СЃРїРёСЃРѕРє В«РєС‚Рѕ СЃРґРµР»Р°РЅ РР— РјРѕРґРµР»РёВ» (СЃС‚СЂРѕРєР° В«вЂ¦ РµС‰С‘ NВ» РІ РґРµСЂРµРІРµ)."""
        try:
            rows = eng.made_of_list(mdl, 0)
        except Exception as e:
            _text_window("РЎРґРµР»Р°РЅРѕ РёР· В«%sВ»" % mdl, "РѕС€РёР±РєР°", "РЅРµ СѓРґР°Р»РѕСЃСЊ РїРѕР»СѓС‡РёС‚СЊ СЃРїРёСЃРѕРє: %s" % e)
            return
        txt = "СЃРґРµР»Р°РЅРѕ РёР· В«%sВ» вЂ” РІСЃРµРіРѕ %d\n\n" % (mdl, len(rows))
        for nm, kind, name, vol, rev in rows:
            txt += "%-46s %-13s %s%s%s\n" % (nm, kind,
                                             ("В«%sВ» " % name) if name else "",
                                             ("%.0f РјРјВі " % vol) if vol else "",
                                             ("rev%s" % rev) if rev else "")
        _text_window("РЎРґРµР»Р°РЅРѕ РёР· В«%sВ»" % mdl, "СЃРґРµР»Р°РЅРѕ РёР· В«%sВ» вЂ” РІСЃРµРіРѕ %d" % (mdl, len(rows)), txt)

    _TMAP = {}                              # V82: РЅРѕРјРµСЂ СЃС‚СЂРѕРєРё Text -> (kind, payload) РґР»СЏ РєР»РёРєРѕРІ

    def _text_line_at(ev):
        """РЎС‚СЂРѕРєР° В«Р”РµСЂРµРІР° С‚РµРєСЃС‚РѕРјВ» РїРѕРґ РєСѓСЂСЃРѕСЂРѕРј: (РЅРѕРјРµСЂ, kind, payload) Р»РёР±Рѕ None."""
        try:
            ln = int(ltree.index("@%d,%d" % (ev.x, ev.y)).split(".")[0])
        except Exception:
            return None
        rec = _TMAP.get(ln)
        return (ln, rec[0], rec[1]) if rec else None

    def _text_dbl(ev):
        """V82: РћР”РРќ РѕР±СЂР°Р±РѕС‚С‡РёРє РґРІРѕР№РЅРѕРіРѕ РєР»РёРєР° вЂ” РїРµСЂРµС…РѕРґ РїРѕ СЃС‚СЂРѕРєРµ РїРѕРґ РєСѓСЂСЃРѕСЂРѕРј.

        Р Р°РЅСЊС€Рµ tag_bind Р·РІР°Р»СЃСЏ РІ С†РёРєР»Рµ РџРћ РЎРўР РћРљР• Рё Р—РђРњР•РќРЇР› СЃР°Рј СЃРµР±СЏ (Tk: Р±РµР· В«+В» вЂ”
        replace), РІС‹Р¶РёРІР°Р»Р° РїРѕСЃР»РµРґРЅСЏСЏ Р»СЏРјР±РґР° вЂ” РєР»РёРє РІС‘Р» РЅРµ С‚СѓРґР° (В«РЅРµ СЂР°Р±РѕС‚Р°РµС‚В»)."""
        rec = _text_line_at(ev)
        if rec:
            if rec[1] == "nd" and rec[2]:
                _goto_model(rec[2])
            return "break"
        return None

    def _text_more(ev):
        """V82: РєР»РёРє РїРѕ В«вЂ¦ РµС‰С‘ NВ» вЂ” РѕРєРЅРѕ СЃРѕ Р’РЎР•Рњ СЃРїРёСЃРєРѕРј (С‚РѕР¶Рµ РїРѕ СЃС‚СЂРѕРєРµ РїРѕРґ РєСѓСЂСЃРѕСЂРѕРј)."""
        rec = _text_line_at(ev)
        if rec and rec[1] == "more" and rec[2]:
            _made_window(rec[2])
            return "break"
        return None

    def _text_tree_show(model=None):
        """Р’РєР»Р°РґРєР° В«Р”РµСЂРµРІРѕ С‚РµРєСЃС‚РѕРјВ»: РџРћР›РќРћР• РґРµСЂРµРІРѕ СЃРІСЏР·РµР№.

        Р”Р’РћР™РќРћР™ РєР»РёРє РїРѕ РР—Р”Р•Р›РР® вЂ” РЅРёР¶РЅРµРµ РѕРєРЅРѕ РїРµСЂРµСЃС‚СЂР°РёРІР°РµС‚СЃСЏ РЅР° РЅРµРіРѕ (РєР°Рє РІС‹Р±РѕСЂ РІ РІРµСЂС…РЅРµРј РѕРєРЅРµ).
        РљР»РёРє РїРѕ В«вЂ¦ РµС‰С‘ СЃРґРµР»Р°РЅРѕ РёР· РЅРµС‘: NВ» вЂ” РѕРєРЅРѕ СЃРѕ Р’РЎР•Рњ СЃРїРёСЃРєРѕРј."""
        if model:
            _last["lroot"] = model
        m = _last.get("lroot") or _last.get("model")
        try:
            ltree.configure(state="normal")
            ltree.delete("1.0", "end")
            _TMAP.clear()
            for tg in ("nd", "mr", "hd"):
                ltree.tag_delete(tg)
            # V82: РѕРґРёРЅ РѕР±СЂР°Р±РѕС‚С‡РёРє РЅР° РІРёРґР¶РµС‚ (replace С‚РµРј Р¶Рµ С…СЌРЅРґР»РµСЂРѕРј Р±РµР·РІСЂРµРґРµРЅ)
            ltree.bind("<Double-1>", _text_dbl)
            ltree.bind("<Button-1>", _text_more)
        except Exception:
            pass
        ltree.tag_configure("nd", foreground="#0a4a8a", underline=True)
        ltree.tag_configure("mr", foreground="#8a4a00", underline=True)
        ltree.tag_configure("hd", foreground="#123", background="#eef3f8")
        try:
            if not m:
                ltree.insert("end", "РІС‹Р±РµСЂРё РёР·РґРµР»РёРµ РІ Р›Р®Р‘РћР™ РІРєР»Р°РґРєРµ СЃРІРµСЂС…Сѓ вЂ” РїРѕРєР°Р¶Сѓ РїРѕР»РЅРѕРµ РґРµСЂРµРІРѕ\n")
                ltext_sum.config(text="РІС‹Р±РµСЂРё РёР·РґРµР»РёРµ вЂ” РїРѕР»РЅРѕРµ РґРµСЂРµРІРѕ: СЃРѕСЃС‚Р°РІ + РІС…РѕРґРёРјРѕСЃС‚СЊ + РЅР°СЃР»РµРґРѕРІР°РЅРёРµ")
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
                    # V82: РІРјРµСЃС‚Рѕ tag_bind РІ С†РёРєР»Рµ (replace) вЂ” РєР°СЂС‚Р° СЃС‚СЂРѕРєР°->payload;
                    # РєР»СЋС‡ = СЃС‚СЂРѕРєР° РџР•Р Р•Р” РІСЃС‚Р°РІРєРѕР№ (start), С‚.Рє. end-1c Сѓ Tk вЂ” В«С„Р°РЅС‚РѕРјРЅР°СЏВ» СЃР»РµРґСѓСЋС‰Р°СЏ СЃС‚СЂРѕРєР°
                    _TMAP[int(start.split(".")[0])] = ("nd", payload)
                elif kind == "more" and payload:
                    ltree.tag_add("mr", start, end)
                    _TMAP[int(start.split(".")[0])] = ("more", payload)
                elif kind == "head":
                    ltree.tag_add("hd", start, end)
            ltext_sum.config(text="РїРѕР»РЅРѕРµ РґРµСЂРµРІРѕ: %s (РіР»СѓР±РёРЅР° %d) В· Р”Р’РћР™РќРћР™ РєР»РёРє РїРѕ РёР·РґРµР»РёСЋ = РїРµСЂРµР№С‚Рё РЅР° РЅРµРіРѕ, "
                                  "РїРѕ В«вЂ¦ РµС‰С‘ NВ» = РІРµСЃСЊ СЃРїРёСЃРѕРє" % (m, depth))
            ltree.configure(state="disabled")
        except Exception as e:
            try:
                ltree.configure(state="disabled")
            except Exception:
                pass
            ltext_sum.config(text="РЅРµ СѓРґР°Р»РѕСЃСЊ РїРѕСЃС‚СЂРѕРёС‚СЊ РґРµСЂРµРІРѕ: %s" % e)

    def _hist_show(model=None):
        """Р’РєР»Р°РґРєР° В«РСЃС‚РѕСЂРёСЏ С„Р°Р№Р»Р°В»: РџРћР›РќРђРЇ РёСЃС‚РѕСЂРёСЏ РїСЂР°РІРѕРє РїРѕ Р’РЎР•Рњ С„Р°Р№Р»Р°Рј РёР·РґРµР»РёСЏ.

        РСЃС‚РѕСЂРёСЏ Р±РµСЂС‘С‚СЃСЏ РР— РЎРђРњРРҐ Р¤РђР™Р›РћР’ (trail Creo). Р•СЃР»Рё РёР·РґРµР»РёРµ вЂ” РљРћРџРРЇ, Creo РїРµСЂРµРЅС‘СЃ РІ С„Р°Р№Р»
        РёСЃС‚РѕСЂРёСЋ РРЎРҐРћР”РќРћР™ РјРѕРґРµР»Рё: С‚Р°РєРёРµ Р·Р°РїРёСЃРё РїРѕРєР°Р·С‹РІР°РµРј СЃ РёРјРµРЅРµРј РРЎРҐРћР”РќРћР“Рћ С„Р°Р№Р»Р° (СЃРµСЂС‹Рј), Р° РіР°Р»РєР°
        В«СЃРєСЂС‹С‚СЊ СѓРЅР°СЃР»РµРґРѕРІР°РЅРЅС‹РµВ» СѓР±РёСЂР°РµС‚ РёС… СЃРѕРІСЃРµРј. РСЃС‚РѕС‡РЅРёРє Р±РµСЂС‘Рј РёР· С„Р°Р№Р»Р° (`from_mdl_name`).
        """
        m = model or _last.get("model") or ""
        try:
            ltv_h.delete(*ltv_h.get_children())
        except Exception:
            return
        if not m:
            lhist_sum.config(text="РІС‹Р±РµСЂРё РёР·РґРµР»РёРµ РІ Р›Р®Р‘РћР™ РІРєР»Р°РґРєРµ СЃРІРµСЂС…Сѓ вЂ” РїРѕРєР°Р¶Сѓ РёСЃС‚РѕСЂРёСЋ РµРіРѕ С„Р°Р№Р»РѕРІ")
            return
        try:
            con = eng.connect()
            paths = [r[0] for r in con.execute("SELECT path FROM snapshots WHERE model=? ORDER BY path",
                                               (eng.stem(m),))]
            con.close()
        except Exception:
            paths = []
        if not paths:
            lhist_sum.config(text="РёР·РґРµР»РёРµ %s: С„Р°Р№Р»РѕРІ РІ Р±Р°Р·Рµ РЅРµС‚" % m)
            return
        hide_inh = bool(var_hide.get())
        src, _sp, src_keys, src_found = copy_source_of(paths, settings)
        total, inh, own_iso = 0, 0, []
        for p in paths:
            try:
                rows = history_rows(p, settings)
            except Exception as ex:
                ltv_h.insert("", "end", values=(os.path.basename(p), "РѕС€РёР±РєР°", str(ex), "", "", "", ""))
                continue
            pbase = os.path.basename(p)
            pstem = eng.stem(pbase)
            own_suffix = pbase[len(pstem):] if pbase.upper().startswith(pstem) else ""
            src_name = (src + own_suffix) if (src and own_suffix) else pbase
            for row in rows:
                total += 1
                own = True
                if src_found:
                    own = ((row.get("Р РµРІРёР·РёСЏ", ""), row.get("Р”Р°С‚Р°", ""), row.get("РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ", ""))
                           not in src_keys)
                if not own:
                    inh += 1
                    if hide_inh:
                        continue
                fname = row.get("Р¤Р°Р№Р»", "") if own else src_name
                item = ltv_h.insert("", "end", values=(fname, row.get("Р РµРІРёР·РёСЏ", ""),
                                                       row.get("Р”Р°С‚Р°", ""), row.get("РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ", ""),
                                                       row.get("РљРѕРјРїСЊСЋС‚РµСЂ", ""), row.get("Р’РµСЂСЃРёСЏ Creo", ""),
                                                       row.get("Р§С‚Рѕ РёР·РјРµРЅРµРЅРѕ", "")))
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
            lhist_sum.config(text="вљ  РјРѕРґРµР»СЊ СЃРєРѕРїРёСЂРѕРІР°РЅР° РёР· %s%s; Р·Р°РїРёСЃРё Р РђРќР¬РЁР• РєРѕРїРёРё РѕС‚РЅРѕСЃСЏС‚СЃСЏ Рє "
                                  "РРЎРҐРћР”РќРћР™ РјРѕРґРµР»Рё В· С„Р°Р№Р»РѕРІ %d, Р·Р°РїРёСЃРµР№ %d (СѓРЅР°СЃР»РµРґРѕРІР°РЅРЅС‹С… %d%s)"
                             % (src, (" (РєРѕРїРёСЏ ~%s)" % cdate) if cdate else "",
                                len(paths), shown, inh, ", СЃРєСЂС‹С‚С‹ РіР°Р»РєРѕР№" if hide_inh else ""))
        else:
            lhist_sum.config(text="РёСЃС‚РѕСЂРёСЏ В«%sВ»: С„Р°Р№Р»РѕРІ %d, Р·Р°РїРёСЃРµР№ %d" % (m, len(paths), shown))

    def _overview_text():
        """V84: СЃРІРѕРґРєР° РїРѕ Р’РЎР•Р™ Р±Р°Р·Рµ РѕРґРЅРёРј С‚РµРєСЃС‚РѕРј: СЃС‚Р°С‚РёСЃС‚РёРєР°, РіРѕСЂСЏС‡РёРµ, СЃС‚Р°СЂС‹Рµ, СЃРёСЂРѕС‚С‹, РґСѓР±Р»Рё, Р°РІС‚РѕСЂС‹."""
        from collections import Counter
        now = time.time()
        cut_hot = time.strftime("%Y-%m-%d", time.localtime(now - 30 * 86400))  # ts вЂ” СЃС‚СЂРѕРєР° ISO
        cut_old = now - 730 * 86400                       # В«СЃС‚Р°СЂС‹РµВ» вЂ” 2 РіРѕРґР°
        out, con = [], eng.connect()
        try:
            n_files, n_models = con.execute(
                "SELECT COUNT(*), COUNT(DISTINCT model) FROM snapshots").fetchone()
            n_links = con.execute("SELECT COUNT(*) FROM links").fetchone()[0]
            n_der = con.execute("SELECT COUNT(*) FROM derived").fetchone()[0]
            n_ch = con.execute("SELECT COUNT(*) FROM changes").fetchone()[0]
            last_scan = con.execute("SELECT MAX(ts) FROM changes").fetchone()[0] or "вЂ”"
            out.append("Р‘РђР—Рђ: С„Р°Р№Р»РѕРІ %d В· РјРѕРґРµР»РµР№ %d В· СЃРІСЏР·РµР№ %d В· РїСЂРѕРёР·РІРѕРґРЅС‹С… %d В· Р¶СѓСЂРЅР°Р» РїСЂР°РІРѕРє %d"
                       % (n_files, n_models, n_links, n_der, n_ch))
            out.append("РїРѕСЃР»РµРґРЅРёР№ СЃРєР°РЅ: %s В· СЃРІРѕРґРєР° СЃРѕР±СЂР°РЅР°: %s"
                       % (last_scan, time.strftime("%d.%m.%Y %H:%M", time.localtime(now))))
            marks = {}                             # V86: РЅРѕРјРµСЂ СЃС‚СЂРѕРєРё (1-based) -> РјРѕРґРµР»СЊ (РєР»РёРє = РїРµСЂРµС…РѕРґ)
            # РјРЅРѕР¶РµСЃС‚РІР° РјРѕРґРµР»РµР№ вЂ” РћР”РќРРњ РїСЂРѕС…РѕРґРѕРј Р·Р°СЂР°РЅРµРµ: С„РёР»СЊС‚СЂ С€Р°Р±Р»РѕРЅРѕРІ + СЂР°Р·РґРµР» В«РЎРёСЂРѕС‚С‹В»
            models = {r[0] for r in con.execute(
                "SELECT DISTINCT model FROM snapshots WHERE model != ''")}
            children = {r[0] for r in con.execute(
                "SELECT DISTINCT child FROM links WHERE child != ''")}
            parents = {r[0] for r in con.execute(
                "SELECT DISTINCT parent FROM links WHERE parent != ''")}
            # Р“РћР РЇР§РР•: СЂРµР°Р»СЊРЅС‹Рµ РёР·РјРµРЅРµРЅРёСЏ РїР°СЃРїРѕСЂС‚РѕРІ (modify) Р·Р° 30 РґРЅРµР№
            rows = con.execute("SELECT item, ts FROM changes WHERE kind='modify' AND ts >= ? "
                               "ORDER BY id DESC", (cut_hot,)).fetchall()
            hot, hot_ts = Counter(), {}
            skipped = set()
            for item, ts in rows:
                m = eng.stem(os.path.basename(item or ""))
                if len(m) < 3 or m not in models:   # V86: С€Р°Р±Р»РѕРЅС‹/РЅРµС‚ РІ Р±Р°Р·Рµ вЂ” РјСѓСЃРѕСЂ Р¶СѓСЂРЅР°Р»Р°
                    if m:
                        skipped.add(m)
                    continue
                hot[m] += 1
                hot_ts.setdefault(m, ts)              # ORDER BY id DESC в†’ РїРµСЂРІР°СЏ РІСЃС‚СЂРµС‡Р° СЃР°РјР°СЏ СЃРІРµР¶Р°СЏ
            out.append("")
            out.append("Р“РћР РЇР§РР• РџР РђР’РљР Р·Р° 30 РґРЅРµР№: Р·Р°РїРёСЃРµР№ %d, РјРѕРґРµР»РµР№ %d" % (len(rows), len(hot)))
            if skipped:
                out.append("   (С€Р°Р±Р»РѕРЅРЅС‹С…/РЅРµ РЅР°Р№РґРµРЅРѕ РІ Р±Р°Р·Рµ РѕРїСѓС‰РµРЅРѕ: %d РјРѕРґРµР»РµР№)" % len(skipped))
            if not hot:
                out.append("   вЂ” РїСЂР°РІРѕРє РїР°СЃРїРѕСЂС‚РѕРІ Р·Р° РїРµСЂРёРѕРґ РЅРµ Р±С‹Р»Рѕ")
            for m, c in hot.most_common(15):
                out.append("   %4d  %-42s  РїРѕСЃР»РµРґРЅСЏСЏ %s" % (c, m[:42], hot_ts.get(m, "")[:19]))
                marks[len(out)] = m                  # V86: РєР»РёРє РїРѕ СЌС‚РѕР№ СЃС‚СЂРѕРєРµ = РїРµСЂРµС…РѕРґ РЅР° РјРѕРґРµР»СЊ
            if len(hot) > 15:
                out.append("   вЂ¦ РµС‰С‘ %d РјРѕРґРµР»РµР№" % (len(hot) - 15))
            # РЎРўРђР Р«Р•: С„Р°Р№Р» РјРѕРґРµР»Рё РЅРµ РјРµРЅСЏР»СЃСЏ Р±РѕР»СЊС€Рµ 2 Р»РµС‚
            n_old = con.execute("SELECT COUNT(*) FROM (SELECT model FROM snapshots "
                                "WHERE model != '' GROUP BY model HAVING MAX(mtime) < ?)",
                                (cut_old,)).fetchone()[0]
            old = con.execute("SELECT model, MAX(mtime) FROM snapshots WHERE model != '' "
                              "GROUP BY model HAVING MAX(mtime) < ? ORDER BY 2 LIMIT 15",
                              (cut_old,)).fetchall()
            out.append("")
            out.append("РЎРўРђР Р«Р• (С„Р°Р№Р» РЅРµ РјРµРЅСЏР»СЃСЏ >2 Р»РµС‚): РјРѕРґРµР»РµР№ %d" % n_old)
            for m, mt in old:
                out.append("   %-46s %s" % (m[:46],
                                            time.strftime("%d.%m.%Y", time.localtime(mt or 0))))
                marks[len(out)] = m                  # V86: РєР»РёРє = РїРµСЂРµС…РѕРґ
            if n_old > 15:
                out.append("   вЂ¦ РµС‰С‘ %d" % (n_old - 15))
            # РЎРР РћРўР«: РЅРµ РІС…РѕРґРёС‚ РЅРё РІ РѕРґРЅСѓ СЃР±РѕСЂРєСѓ (РјРЅРѕР¶РµСЃС‚РІР° РІС‹С‡РёСЃР»РµРЅС‹ РІС‹С€Рµ)
            orphans = models - children
            solo = sorted(orphans - parents)
            out.append("")
            out.append("РЎРР РћРўР«: РЅРµ РІС…РѕРґРёС‚ РЅРё РІ РѕРґРЅСѓ СЃР±РѕСЂРєСѓ вЂ” %d (РІРµСЂС…РЅРёС… СЃР±РѕСЂРѕРє %d, "
                       "РѕРґРёРЅРѕС‡РЅС‹С… С„Р°Р№Р»РѕРІ %d)" % (len(orphans), len(orphans & parents), len(solo)))
            if solo:
                info = eng.models_info(solo[:20])
                for m in solo[:20]:
                    i8 = info.get(m, ("", "", "", 0, "", "", 0, 0))
                    out.append("   %-40s %s" % (m[:40], (i8[1] or i8[0] or "")[:44]))
                    marks[len(out)] = m              # V86: РєР»РёРє = РїРµСЂРµС…РѕРґ
                if len(solo) > 20:
                    out.append("   вЂ¦ РµС‰С‘ %d" % (len(solo) - 20))
            # Р”РЈР‘Р›Р: РјРѕРґРµР»СЊ РІ РЅРµСЃРєРѕР»СЊРєРёС… РїР°РїРєР°С…
            mp = {}
            for m, f in con.execute("SELECT DISTINCT model, folder FROM snapshots "
                                    "WHERE model != '' AND folder != ''"):
                mp.setdefault(m, set()).add(f)
            dups = sorted(((len(fs), m) for m, fs in mp.items() if len(fs) > 1), reverse=True)
            out.append("")
            out.append("Р”РЈР‘Р›Р (РјРѕРґРµР»СЊ РІ РЅРµСЃРєРѕР»СЊРєРёС… РїР°РїРєР°С…): РјРѕРґРµР»РµР№ %d" % len(dups))
            for c, m in dups[:10]:
                out.append("   %-44s РїР°РїРѕРє: %d" % (m[:44], c))
                marks[len(out)] = m                  # V86: РєР»РёРє = РїРµСЂРµС…РѕРґ
            if len(dups) > 10:
                out.append("   вЂ¦ РµС‰С‘ %d" % (len(dups) - 10))
            # РћР”РРќРђРљРћР’Р«Р™ РћР‘РЄРЃРњ: РІРѕР·РјРѕР¶РЅС‹Рµ РєРѕРїРёРё
            n_vol = con.execute("SELECT COUNT(*) FROM (SELECT volume FROM snapshots "
                                "WHERE volume > 0 GROUP BY volume "
                                "HAVING COUNT(DISTINCT model) > 1)").fetchone()[0]
            vols = con.execute("SELECT volume, COUNT(DISTINCT model) FROM snapshots "
                               "WHERE volume > 0 GROUP BY volume "
                               "HAVING COUNT(DISTINCT model) > 1 ORDER BY 2 DESC LIMIT 8").fetchall()
            out.append("")
            out.append("РћР”РРќРђРљРћР’Р«Р™ РћР‘РЄРЃРњ (РІРѕР·РјРѕР¶РЅС‹Рµ РєРѕРїРёРё): СЃРѕС‡РµС‚Р°РЅРёР№ %d, С‚РѕРї-8" % n_vol)
            if not vols:
                out.append("   вЂ” СЃРѕРІРїР°РґРµРЅРёР№ РѕР±СЉС‘РјРѕРІ РЅРµС‚")
            for v, c in vols:
                ms = [r[0] for r in con.execute(
                    "SELECT DISTINCT model FROM snapshots WHERE volume = ? LIMIT 3", (v,))]
                out.append("   %10.0f РјРјВі: РјРѕРґРµР»РµР№ %d вЂ” %s" % (v, c, ", ".join(ms)))
            # РђР’РўРћР Р« РІ Р¶СѓСЂРЅР°Р»Рµ РїСЂР°РІРѕРє
            authors = con.execute("SELECT who, COUNT(*) FROM changes WHERE who != '' "
                                  "GROUP BY who ORDER BY 2 DESC LIMIT 8").fetchall()
            n_anon = con.execute("SELECT COUNT(*) FROM changes WHERE who = ''").fetchone()[0]
            out.append("")
            out.append("РђР’РўРћР Р« Р’ Р–РЈР РќРђР›Р• РџР РђР’РћРљ (Р·Р°РїРёСЃРµР№ %d, Р±РµР· Р°РІС‚РѕСЂР° %d):" % (n_ch, n_anon))
            if not authors:
                out.append("   вЂ” Р°РІС‚РѕСЂС‹ РЅРµ Р·Р°РїРёСЃР°РЅС‹")
            for who, c in authors:
                out.append("   %-18s %d" % (who[:18], c))
        finally:
            con.close()
        return "\n".join(out), marks                 # V86: (С‚РµРєСЃС‚, РєР°СЂС‚Р° СЃС‚СЂРѕРє -> РјРѕРґРµР»СЊ РґР»СЏ РєР»РёРєРѕРІ)

    def _ov_dbl(ev=None):
        """V86: РґРІРѕР№РЅРѕР№ РєР»РёРє РїРѕ СЃС‚СЂРѕРєРµ В«РћР±Р·РѕСЂР°В» = РїРµСЂРµР№С‚Рё РЅР° РјРѕРґРµР»СЊ СЌС‚РѕР№ СЃС‚СЂРѕРєРё."""
        try:
            line = int(otv.index("@%d,%d" % (ev.x, ev.y)).split(".")[0])
            m = (_last.get("ov_marks") or {}).get(line)
            if m:
                _goto_model(m)
        except Exception:
            pass

    def _overview_show(force=False):
        """V84: РІРєР»Р°РґРєР° В«РћР±Р·РѕСЂВ» вЂ” СЃРІРѕРґРєР° РїРѕ РІСЃРµР№ Р±Р°Р·Рµ (РєСЌС€ РІ _last['ov_text']; В«РћР±РЅРѕРІРёС‚СЊВ» = force)."""
        try:
            otv.configure(state="normal")
            otv.delete("1.0", "end")
            otv.bind("<Double-1>", _ov_dbl)             # V86: replace С‚РµРј Р¶Рµ С…СЌРЅРґР»РµСЂРѕРј Р±РµР·РІСЂРµРґРµРЅ
            if force or not _last.get("ov_text"):
                _last["ov_text"], _last["ov_marks"] = _overview_text()
                _last["ov_built"] = time.strftime("%d.%m.%Y %H:%M:%S")
            otv.insert("end", _last["ov_text"] + "\n")
        except Exception as e:                          # РІРєР»Р°РґРєР° РЅРµ РґРѕР»Р¶РЅР° СЂРѕРЅСЏС‚СЊ РѕРєРЅРѕ
            try:
                otv.configure(state="normal")
                otv.insert("end", "СЃРІРѕРґРєР° РЅРµ РїРѕСЃС‚СЂРѕРµРЅР°: %s" % e)
            except Exception:
                pass
        finally:
            try:
                otv.configure(state="disabled")
            except Exception:
                pass
        try:
            ovs_sum.config(text="РѕР±Р·РѕСЂ Р±Р°Р·С‹ РѕС‚ %s В· В«РћР±РЅРѕРІРёС‚СЊВ» вЂ” РїРµСЂРµСЃС‡РёС‚Р°С‚СЊ"
                           % _last.get("ov_built", "?"))
        except Exception:
            pass

    def _graph_data(model, ddown=4, dup=3):
        """V85: СѓР·Р»С‹/СЂС‘Р±СЂР° В«Р“СЂР°С„Р°В»: РєРѕСЂРµРЅСЊ (level 0), СЃРѕСЃС‚Р°РІ РІРЅРёР·, РІС…РѕРґРёРјРѕСЃС‚СЊ РІРІРµСЂС…, РёР· С‡РµРіРѕ СЃРґРµР»Р°РЅР°."""
        root = eng.stem(model or "")
        nodes, edges = {}, []
        if not root:
            return nodes, edges
        nodes[root] = {"kind": "root", "level": 0}
        down = eng.plm_down_data(root, ddown)
        up = eng.plm_up_data(root, dup)
        level, frontier = 0, [root]                   # РІРЅРёР·: BFS РїРѕ СѓСЂРѕРІРЅСЏРј
        while frontier and level < ddown and len(nodes) < 1500:
            nxt = []
            for m in frontier:
                for ch, q in down.get(m, []) or []:
                    if ch in nodes:
                        edges.append((m, ch, "down", q))     # РѕР±Р° РєРѕРЅС†Р° РµСЃС‚СЊ
                    elif len(nodes) < 1500:                  # cap: РЅРё СѓР·Р»Р°, РЅРё СЂРµР±СЂР°
                        nodes[ch] = {"kind": "down", "level": level + 1}
                        edges.append((m, ch, "down", q))
                        nxt.append(ch)
            frontier, level = nxt, level + 1
        level, frontier = 0, [root]                   # РІРІРµСЂС…: level РѕС‚СЂРёС†Р°С‚РµР»СЊРЅС‹Р№
        while frontier and level > -dup and len(nodes) < 1500:
            nxt = []
            for m in frontier:
                for p, q in up.get(m, []) or []:
                    if p in nodes:                              # СѓР·РµР» РµСЃС‚СЊ вЂ” СѓСЂРѕРІРµРЅСЊ РЅРµ РґРІРёРіР°РµРј
                        edges.append((m, p, "up", q))
                    elif len(nodes) < 1500:                     # cap: РЅРё СѓР·Р»Р°, РЅРё СЂРµР±СЂР°
                        nodes[p] = {"kind": "up", "level": level - 1}
                        edges.append((m, p, "up", q))
                        nxt.append(p)
            frontier, level = nxt, level - 1
        try:
            der = eng.derived_bases(root)[:6]         # РёР· С‡РµРіРѕ СЃРґРµР»Р°РЅР° вЂ” СЃР»РµРІР° РѕС‚ РєРѕСЂРЅСЏ
        except Exception:
            der = []
        if len(nodes) < 1500:                         # cap: РІР·СЂС‹РІРѕРѕРїР°СЃРЅС‹Рµ С€Р°Р±Р»РѕРЅС‹ РЅРµ СЂРёСЃСѓРµРј С†РµР»РёРєРѕРј
            for b, k in der:
                if b and b not in nodes:
                    nodes[b] = {"kind": "der", "level": 0}
                    edges.append((b, root, "der", ""))
        return nodes, edges

    def _graph_layout(nodes, edges):
        """V85: РїРѕР·РёС†РёРё СѓР·Р»РѕРІ (x РІ В«СѓР·Р»Р°С…В», y = СѓСЂРѕРІРµРЅСЊ): РїРѕСЃС‚-РѕР±С…РѕРґ РґРІСѓС… РґРµСЂРµРІСЊРµРІ + СЃРґРІРёРі Рє РѕР±С‰РµРјСѓ РєРѕСЂРЅСЋ."""
        root = next((n for n, d in nodes.items() if d.get("kind") == "root"), None) or next(iter(nodes))
        down_kids = {n: [] for n in nodes}
        up_kids = {n: [] for n in nodes}
        par_d, par_u = set(), set()                   # Сѓ СѓР·Р»Р° РћР”РРќ СЂР°СЃРєР»Р°РґРѕС‡РЅС‹Р№ СЂРѕРґРёС‚РµР»СЊ (РїРµСЂРІС‹Р№ РїРѕР±РµРґРёР»)
        for a, b, kind, q in edges:
            if a not in nodes or b not in nodes or a == b:
                continue
            if kind == "down" and b not in par_d:
                down_kids[a].append(b)
                par_d.add(b)
            elif kind == "up" and b not in par_u:
                up_kids[a].append(b)
                par_u.add(b)
        x_d, x_u = {}, {}
        cnt_d, cnt_u = [0.0], [0.0]

        def place(node, kids, out, cnt, guard):
            if node in out:
                return out[node]
            if node in guard:                         # С†РёРєР» вЂ” РЅРµ СѓРіР»СѓР±Р»СЏРµРјСЃСЏ
                out[node] = cnt[0] + 0.5
                cnt[0] += 1.0
                return out[node]
            ch = [k for k in kids.get(node, []) if k in nodes and k != node]
            if not ch:
                val = cnt[0] + 0.5
                cnt[0] += 1.0
            else:
                xs = [place(k, kids, out, cnt, guard | {node}) for k in ch]
                val = (min(xs) + max(xs)) / 2.0
            out[node] = val
            return val

        place(root, down_kids, x_d, cnt_d, frozenset())
        place(root, up_kids, x_u, cnt_u, frozenset())
        shift = x_d.get(root, 0.0) - x_u.get(root, 0.0)
        for n in x_u:
            x_u[n] += shift                           # РїРѕРґРІРµСЃС‚Рё РІРІРµСЂС…-РґРµСЂРµРІРѕ Рє РєРѕСЂРЅСЋ
        x = dict(x_u)
        x.update(x_d)                                 # РІРЅРёР· РїСЂРёРѕСЂРёС‚РµС‚ РїСЂРё РѕР±С‰РёС… СѓР·Р»Р°С…
        der = [n for n, d in nodes.items() if d.get("kind") == "der"]
        rx = x.get(root, 0.0)
        for i, n in enumerate(der):
            x[n] = rx - (len(der) - i) - 0.5          # Р»РµРІС‹Р№ СЂСЏРґ СѓСЂРѕРІРЅСЏ 0
        return {n: (x.get(n, 0.0), float(nodes[n]["level"])) for n in nodes}

    def _graph_dbl(ev=None):
        """V85: РґРІРѕР№РЅРѕР№ РєР»РёРє РїРѕ СѓР·Р»Сѓ РєР°СЂС‚С‹ = РїРµСЂРµСЃС‚СЂРѕРёС‚СЊ РЅРёР· РЅР° СЌС‚Сѓ РјРѕРґРµР»СЊ (РєР°Рє РІРµР·РґРµ)."""
        try:
            iid = gr_canvas.find_withtag("current")
            for t in (gr_canvas.gettags(iid[0]) if iid else ()):
                if t.startswith("n:"):
                    _goto_model(t[2:])
                    return
        except Exception:
            pass

    def _graph_drag(ev):
        """V85: С‚СЏРЅСѓС‚СЊ С…РѕР»СЃС‚ Р·Р° РїСѓСЃС‚РѕРµ РјРµСЃС‚Рѕ (РїРѕ СѓР·Р»Сѓ вЂ” РЅРµ С‚СЏРЅРµРј, С‡С‚РѕР±С‹ РЅРµ РјРµС€Р°С‚СЊ РєР»РёРєР°Рј)."""
        try:
            if gr_canvas.find_withtag("current"):
                return
            gr_canvas.scan_dragto(ev.x, ev.y, gain=1)
        except Exception:
            pass

    def _graph_wheel(ev):
        """V85: РєРѕР»РµСЃРѕ = Р·СѓРј РєР°СЂС‚С‹ Рє С‚РѕС‡РєРµ РєСѓСЂСЃРѕСЂР°."""
        try:
            f = 1.15 if ev.delta > 0 else 1 / 1.15
            cx, cy = gr_canvas.canvasx(ev.x), gr_canvas.canvasy(ev.y)
            gr_canvas.scale("all", cx, cy, f, f)
            gr_canvas.config(scrollregion=gr_canvas.bbox("all"))
        except Exception:
            pass

    def _graph_zoom(f):
        """V85: Р·СѓРј РєРЅРѕРїРєР°РјРё В± (Рє С†РµРЅС‚СЂСѓ РєР°СЂС‚С‹)."""
        try:
            bb = gr_canvas.bbox("all")
            if not bb:
                return
            gr_canvas.scale("all", (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2, f, f)
            gr_canvas.config(scrollregion=gr_canvas.bbox("all"))
        except Exception:
            pass

    def _graph_show(force=False):
        """V85: РЅР°СЂРёСЃРѕРІР°С‚СЊ РєР°СЂС‚Сѓ СЂРѕРґРѕСЃР»РѕРІРЅРѕР№ РІС‹Р±СЂР°РЅРЅРѕР№ РјРѕРґРµР»Рё (РІРєР»Р°РґРєР° В«Р“СЂР°С„В»)."""
        try:
            gr_canvas.bind("<Double-1>", _graph_dbl)     # replace С‚РµРј Р¶Рµ С…СЌРЅРґР»РµСЂРѕРј Р±РµР·РІСЂРµРґРµРЅ
            gr_canvas.bind("<Button-1>", lambda e: gr_canvas.scan_mark(e.x, e.y))
            gr_canvas.bind("<B1-Motion>", _graph_drag)
            gr_canvas.bind("<MouseWheel>", _graph_wheel)
            gr_canvas.delete("all")
            root = eng.stem(_last.get("model") or "")
            if not root:
                grs.config(text="РІС‹Р±РµСЂРё РёР·РґРµР»РёРµ РІ Р›Р®Р‘РћР™ РІРєР»Р°РґРєРµ СЃРІРµСЂС…Сѓ вЂ” РїРѕСЃС‚СЂРѕСЋ РєР°СЂС‚Сѓ")
                gr_canvas.create_text(16, 16, anchor="nw", fill="#777", text="РЅРµС‚ РІС‹Р±СЂР°РЅРЅРѕР№ РјРѕРґРµР»Рё")
                return
            try:
                ddown = int(gr_dd.get() or 4)
            except Exception:
                ddown = 4
            try:
                dup = int(gr_du.get() or 3)
            except Exception:
                dup = 3
            t0 = time.time()
            nodes, edges = _graph_data(root, ddown, dup)
            if not nodes:
                grs.config(text="РЅРµС‚ РґР°РЅРЅС‹С… РґР»СЏ РєР°СЂС‚С‹ В«%sВ»" % root)
                return
            pos = _graph_layout(nodes, edges)
            unit, row, nw, nh = 170, 64, 158, 40
            fills = {"root": "#ffe9a8", "up": "#d9e8fb", "down": "#eaf7ea", "der": "#fbe3d0", "mfg": "#ffe0b0"}
            # Legend РґР»СЏ РІРёР·СѓР°Р»РёР·Р°С†РёРё РЅР°РїСЂР°РІР»РµРЅРёР№
            leg_items = [
                ("root", "РєРѕСЂРµРЅСЊ", "#ffe9a8"),
                ("up", "РІРІРµСЂС… (СЂРѕРґРёС‚РµР»СЊ)", "#d9e8fb"),
                ("down", "РІРЅРёР· (РїРѕС‚РѕРјРѕРє)", "#eaf7ea"),
                ("der", "Р·Р°РіРѕС‚РѕРІРєР°/РѕС‚Р»РёРІРєР°", "#fbe3d0"),
                ("mfg", "РѕСЃРЅР°СЃС‚РєР°", "#ffe0b0"),
            ]
            x0, y0 = 10, 8
            for kind, label, color in leg_items:
                gr_canvas.create_rectangle(x0, y0, x0 + 14, y0 + 12, fill=color, outline="#555")
                gr_canvas.create_text(x0 + 18, y0 + 6, text=label, font=("Consolas", 8))
                y0 += 16
            grs.config(text="Р»РµРіРµРЅРґР°: в–ј-СЃРѕР·РґР°РЅРёРµ, в–І-СЂРѕРґРѕСЃР»РѕРІРЅР°СЏ, в—„-Р·Р°РіРѕС‚РѕРІРєР°, в—†-РѕСЃРЅР°СЃС‚РєР°")
                if a not in pos or b not in pos:
                    continue
                xa, ya = pos[a]
                xb, yb = pos[b]
                x1, y1, x2, y2 = xa * unit, ya * row, xb * unit, yb * row
                if kind == "der":
                    gr_canvas.create_line(x1 + nw // 2, y1, x2 - nw // 2, y2,
                                          dash=(4, 3), fill="#c47a3a")
                elif nodes[a]["level"] <= nodes[b]["level"]:
                    gr_canvas.create_line(x1, y1 + nh // 2, x2, y2 - nh // 2, fill="#8aa0b5")
                else:
                    gr_canvas.create_line(x1, y1 - nh // 2, x2, y2 + nh // 2, fill="#8aa0b5")
                if q and q != 1:
                    gr_canvas.create_text((x1 + x2) / 2 + 8, (y1 + y2) / 2, text="x%s" % q,
                                          fill="#666", font=("Consolas", 8))
            for n, (x, y) in pos.items():               # СѓР·Р»С‹
                d = nodes[n]
                gr_canvas.create_rectangle(x * unit - nw // 2, y * row - nh // 2,
                                           x * unit + nw // 2, y * row + nh // 2,
                                           fill=fills.get(d["kind"], "#eee"), outline="#555",
                                           tags=("node", "n:" + n))
                label = n if len(n) <= 24 else n[:22] + "вЂ¦"
                gr_canvas.create_text(x * unit, y * row, text=label, font=("Consolas", 9),
                                      tags=("node", "n:" + n))
            gr_canvas.config(scrollregion=gr_canvas.bbox("all"))
            grs.config(text="РєР°СЂС‚Р° В«%sВ»: СѓР·Р»РѕРІ %d В· СЂС‘Р±РµСЂ %d В· РІРЅРёР· %d / РІРІРµСЂС… %d В· %.2f СЃ"
                       % (root, len(nodes), len(edges), ddown, dup, time.time() - t0))
        except Exception as e:                          # РІРєР»Р°РґРєР° РЅРµ РґРѕР»Р¶РЅР° СЂРѕРЅСЏС‚СЊ РѕРєРЅРѕ
            try:
                grs.config(text="РєР°СЂС‚Р° РЅРµ РїРѕСЃС‚СЂРѕРµРЅР°: %s" % e)
            except Exception:
                pass

    def _bottom_render():
        """РќР°РїРѕР»РЅРёС‚СЊ РђРљРўРР’РќРЈР® РІРєР»Р°РґРєСѓ РЅРёР¶РЅРµРіРѕ РѕРєРЅР° РІС‹Р±СЂР°РЅРЅРѕР№ РјРѕРґРµР»СЊСЋ (РёР»Рё Р°РІС‚РѕСЃРІРѕРґРєРѕР№)."""
        model = _last["model"]
        try:
            sel = lnb.select()
        except Exception:
            sel = ""
        # СЃСЂР°РІРЅРёРІР°РµРј РїРѕ РЎРђРњРћРњРЈ РІРёРґР¶РµС‚Сѓ (Р° РЅРµ РїРѕ РЅРѕРјРµСЂСѓ РІРєР»Р°РґРєРё) вЂ” РїРѕСЂСЏРґРѕРє РІРєР»Р°РґРѕРє РјРѕР¶РµС‚ РјРµРЅСЏС‚СЊСЃСЏ
        if sel == str(lprop):
            # 04.10.2026: В«РЎРІРѕР№СЃС‚РІР° РґРµС‚Р°Р»РёВ» вЂ” РїР»РѕС‰Р°РґСЊ, РўРў, РїР°СЂР°РјРµС‚СЂС‹, С‡РµСЂС‚РµР¶Рё
            try:
                _prop_show(model)
            except Exception as e:      # РІРєР»Р°РґРєР° РЅРµ РґРѕР»Р¶РЅР° СЂРѕРЅСЏС‚СЊ РІСЃС‘ РѕРєРЅРѕ
                ptv.delete(*ptv.get_children())
                ptv.insert("", "end", values=("РћС€РёР±РєР° СЂР°Р·Р±РѕСЂР°",
                                               "%s: %s" % (type(e).__name__, e)))
                lpsum.config(text="РЅРµ СѓРґР°Р»РѕСЃСЊ РїРѕРєР°Р·Р°С‚СЊ СЃРІРѕР№СЃС‚РІР°: %s" % e)
            return
        if sel == str(ltext):           # 07.10.2026: РїРѕР»РЅРѕРµ РґРµСЂРµРІРѕ СЃРІСЏР·РµР№ (СѓР·Р»С‹ РєР»РёРєР°Р±РµР»СЊРЅС‹)
            _text_tree_show()
            return
        if sel == str(lhist):           # 07.10.2026: РёСЃС‚РѕСЂРёСЏ РїСЂР°РІРѕРє РІСЃРµС… С„Р°Р№Р»РѕРІ РёР·РґРµР»РёСЏ
            _hist_show(model)
            return
        if sel == str(lov):             # 08.10.2026 (V84): В«РћР±Р·РѕСЂВ» вЂ” СЃРІРѕРґРєР° РїРѕ РІСЃРµР№ Р±Р°Р·Рµ (Р±РµР· РјРѕРґРµР»Рё)
            _overview_show()
            return
        if sel == str(lgr):             # 09.10.2026 (V85): В«Р“СЂР°С„В» вЂ” РєР°СЂС‚Р° СЂРѕРґРѕСЃР»РѕРІРЅРѕР№ РІС‹Р±СЂР°РЅРЅРѕР№ РјРѕРґРµР»Рё
            _graph_show()
            return
        if not model:
            if sel == str(llinks):
                ltv2.delete(*ltv2.get_children())
                _LLINKS.clear()
                lsum2.config(text="РІС‹Р±РµСЂРё С‡С‚Рѕ-Р»РёР±Рѕ РІ Р›Р®Р‘РћР™ РІРєР»Р°РґРєРµ СЃРІРµСЂС…Сѓ вЂ” СЃРІСЏР·Рё РїРѕСЃС‚СЂРѕСЏС‚СЃСЏ СЃР°РјРё")
            else:
                live_auto()
            return
        if sel == str(llinks):
            try:
                _prod_show(model)        # В«Р”РµСЂРµРІРѕ РїСЂРѕРёР·РІРѕРґСЃС‚РІР°В» РґРµСЂР¶РёРј РіРѕС‚РѕРІС‹Рј вЂ” РїСЂРё РїРµСЂРµС…РѕРґРµ РЅР° РІРєР»Р°РґРєСѓ РЅРµ Р±СѓРґРµС‚ РїСѓСЃС‚Рѕ
            except Exception:
                pass
            _links_show(model)
        else:
            _prod_show(model)

    def _bottom_show(model, pick=False):
        """РџРѕРєР°Р·Р°С‚СЊ РІ РќРР–РќР•Рњ РѕРєРЅРµ СЃРІСЏР·Рё РјРѕРґРµР»Рё. Р—РѕРІСѓС‚ РІРєР»Р°РґРєРё РЎР’Р•Р РҐРЈ (pick=True) Рё РїРµСЂРµС…РѕРґС‹ РІРЅРёР·Сѓ."""
        model = eng.stem(model or "")
        _last["model"] = model
        if pick:
            _last["pick"] = model     # 08.10.2026: СЃС‚СЂРѕРєР°, РІС‹Р±СЂР°РЅРЅР°СЏ Р’Р’Р•Р РҐРЈ, вЂ” Рє РЅРµР№ РІРѕР·РІСЂР°С‰Р°РµС‚ РєРЅРѕРїРєР°
        _last.pop("lroot", None)
        try:                          # 08.10.2026: СЃС‚СЂРѕРєР° РЅР°Рґ РЅРёР¶РЅРёРј РѕРєРЅРѕРј вЂ” С‡С‚Рѕ РёРјРµРЅРЅРѕ РїРѕРєР°Р·С‹РІР°РµС‚ РЅРёР·
            _txt = ("РЅРёР· РїРѕРєР°Р·С‹РІР°РµС‚: %s" % model) if model else ""
            if model and not pick and _last.get("pick") and _last.get("pick") != model:
                _txt += "   (РїРµСЂРµС…РѕРґ; РєРЅРѕРїРєР° РІРµСЂРЅС‘С‚ Рє РІРµСЂС…РЅРµРјСѓ РІС‹Р±РѕСЂСѓ)"
            lsubj.config(text=_txt)
        except Exception:
            pass
        _bottom_render()
        _nav_record(model)                     # V83: РёСЃС‚РѕСЂРёСЏ РґР»СЏ РєРЅРѕРїРѕРє в†ђ в†’
        _nav_state()

    def _goto_model(m):
        """08.10.2026: Р”Р’РћР™РќРћР™ РєР»РёРє РїРѕ РґРµС‚Р°Р»Рё РІ РЅРёР¶РЅРµРј РѕРєРЅРµ = РїРµСЂРµСЃС‚СЂРѕРёС‚СЊ РЅРёР· РЅР° РЅРµС‘ (РєР°Рє РІС‹Р±РѕСЂ СЃРІРµСЂС…Сѓ)."""
        if m:
            _bottom_show(m)

    def _return_to_pick():
        """08.10.2026: В«Р’РµСЂРЅСѓС‚СЊСЃСЏ Рє РІС‹Р±СЂР°РЅРЅРѕРјСѓВ» вЂ” РїСЂРµРґРјРµС‚ РЅРёР·Р° = СЃС‚СЂРѕРєР°, РІС‹Р±СЂР°РЅРЅР°СЏ РІ Р’Р•Р РҐРќР•Рњ РѕРєРЅРµ."""
        m = _last.get("pick") or _last.get("model")
        if m:
            _bottom_show(m)

    def _nav_record(model):
        """V83: Р·Р°РїРёСЃСЊ РёСЃС‚РѕСЂРёРё РїРµСЂРµС…РѕРґРѕРІ РЅРёР·Р° (РєРЅРѕРїРєРё в†ђ в†’). РџСѓСЃС‚С‹Рµ/РїРѕРІС‚РѕСЂС‹ РЅРµ РїРёС€РµРј, lock РїСЂРѕРїСѓСЃРєР°РµРј."""
        if not model or _last.get("nav_lock"):
            return
        nav = _last.setdefault("nav", [])
        i = _last.get("nav_i", -1)
        if 0 <= i < len(nav) and nav[i] == model:
            return                            # СѓР¶Рµ Р·РґРµСЃСЊ вЂ” РґСѓР±Р»РёРєР°С‚ РЅРµ РЅСѓР¶РµРЅ
        del nav[i + 1:]                       # РЅРѕРІР°СЏ РІРµС‚РєР° вЂ” В«РІРїРµСЂС‘РґВ» РѕС‚СЂРµР·Р°РµРј
        nav.append(model)
        if len(nav) > 200:
            del nav[:-200]                    # РѕРіСЂР°РЅРёС‡РёС‚РµР»СЊ РёСЃС‚РѕСЂРёРё
        _last["nav_i"] = len(nav) - 1

    def _nav_state():
        """V83: РґРѕСЃС‚СѓРїРЅРѕСЃС‚СЊ РєРЅРѕРїРѕРє в†ђ в†’ (Р·РѕРІС‘С‚СЃСЏ РїРѕСЃР»Рµ РєР°Р¶РґРѕРіРѕ РїРѕРєР°Р·Р°)."""
        try:
            nav = _last.get("nav") or []
            i = _last.get("nav_i", -1)
            btn_back.state(["!disabled"] if i > 0 else ["disabled"])
            btn_fwd.state(["!disabled"] if 0 <= i < len(nav) - 1 else ["disabled"])
        except Exception:
            pass

    def _nav_show(m):
        """V83: РїРѕРєР°Р· РёР· РёСЃС‚РѕСЂРёРё вЂ” СЃР°Рј РІ РёСЃС‚РѕСЂРёСЋ РќР• РїРёС€РµС‚СЃСЏ (nav_lock)."""
        _last["nav_lock"] = True
        try:
            _bottom_show(m)
        finally:
            _last["nav_lock"] = False
            _nav_state()

    def _nav_back():
        """V83: в†ђ РЅР°Р·Р°Рґ РїРѕ РёСЃС‚РѕСЂРёРё РїРµСЂРµС…РѕРґРѕРІ."""
        nav = _last.get("nav") or []
        i = _last.get("nav_i", -1)
        if i > 0:
            _last["nav_i"] = i - 1
            _nav_show(nav[i - 1])

    def _nav_fwd():
        """V83: в†’ РІРїРµСЂС‘Рґ РїРѕ РёСЃС‚РѕСЂРёРё РїРµСЂРµС…РѕРґРѕРІ."""
        nav = _last.get("nav") or []
        i = _last.get("nav_i", -1)
        if 0 <= i < len(nav) - 1:
            _last["nav_i"] = i + 1
            _nav_show(nav[i + 1])

    def _goto_entry(ev=None):
        """V83: РїРѕР»Рµ В«РџРµСЂРµР№С‚Рё Рє РјРѕРґРµР»РёВ» вЂ” Enter/РєРЅРѕРїРєР° = РїРµСЂРµС…РѕРґ РЅРёР·Р° (РєР°Рє РґРІРѕР№РЅРѕР№ РєР»РёРє)."""
        m = eng.stem((e_goto.get() or "").strip())
        if not m:
            return
        try:
            known = bool(eng.models_info([m]).get(m)) or bool(eng.plm_children(m))
        except Exception:
            known = True                      # СЃР±РѕР№ РїСЂРѕРІРµСЂРєРё РЅРµ РґРѕР»Р¶РµРЅ Р±Р»РѕРєРёСЂРѕРІР°С‚СЊ РїРµСЂРµС…РѕРґ
        if not known:
            try:
                lsubj.config(text="РЅРµ РЅР°Р№РґРµРЅРѕ РІ Р±Р°Р·Рµ: %s" % m)
            except Exception:
                pass
            return
        _goto_model(m)

    def _goto_node(tree_widget, registry, event=None):
        """07.10.2026/08.10.2026: РїРµСЂРµС…РѕРґ РїРѕ СѓР·Р»Сѓ РЅРёР¶РЅРµРіРѕ РґРµСЂРµРІР° РЅР° Р”Р’РћР™РќРћР™ РєР»РёРє (СѓР·РµР» Р±РµСЂС‘Рј РїРѕРґ РєСѓСЂСЃРѕСЂРѕРј)."""
        try:
            node = tree_widget.identify_row(event.y) if event is not None else tree_widget.focus()
        except Exception:
            node = tree_widget.focus()
        rec = registry.get(node)
        m = rec[0] if isinstance(rec, tuple) else rec
        if not m:
            # V81 (08.10.2026): СѓР·Р»Р° РјРѕР¶РµС‚ РќР•РўР¬ РІ СЂРµРµСЃС‚СЂРµ (РІС…РѕРґРёС‚-РІ / MFG / Р·Р°РіРѕС‚РѕРІРєР° / РєРѕСЂРµРЅСЊ) вЂ”
            # РјРѕРґРµР»СЊ Р±РµСЂС‘Рј РёР· 1-Р№ РєРѕР»РѕРЅРєРё values СЃС‚СЂРѕРєРё; Р·Р°РіР»СѓС€РєРё (В«вЂ”В», РїСѓСЃС‚Рѕ) РЅРёРєСѓРґР° РЅРµ РІРµРґСѓС‚.
            try:
                vals = tree_widget.item(node, "values")
            except Exception:
                vals = ()
            cand = ((vals[1] if len(vals) > 1 else "") or "").strip()
            m = "" if cand in ("", "вЂ”", "-") else cand
        if m:
            _bottom_show(m)

    lnb.bind("<<NotebookTabChanged>>", lambda ev: _bottom_render())

    def live_tree(event=None):
        """РћРќР›РђР™Рќ РїРѕ РІС‹Р±СЂР°РЅРЅРѕР№ СЃС‚СЂРѕРєРµ РўРђР‘Р›РР¦Р«: СЃРѕСЃС‚Р°РІ Р’РќРР— Рё Р’РЎР• СЃР±РѕСЂРєРё Р’Р’Р•Р РҐ."""
        sel = tree.selection()
        row = _ROWS.get(sel[0]) if sel else None
        if not row:
            live_auto()
            return
        p = row.get("_path") or ""
        _bottom_show(eng.stem(os.path.basename(p)) if p else "", pick=True)

    tree.bind("<<TreeviewSelect>>", live_tree)

    def expl_live(event=None):
        """Р’С‹Р±РѕСЂ РІ РџР РћР’РћР”РќРРљР• в†’ РЅРёР¶РЅРµРµ РѕРєРЅРѕ (РІС‹Р±СЂР°РЅ С„Р°Р№Р» в†’ СЃРІСЏР·Рё РµРіРѕ РјРѕРґРµР»Рё)."""
        p = _EFILE.get(eview.focus())
        if p:
            _bottom_show(eng.stem(os.path.basename(p)), pick=True)

    eview.bind("<<TreeviewSelect>>", expl_live)

    def tree_live(event=None):
        """Р’С‹Р±РѕСЂ РІ Р”Р•Р Р•Р’Р• в†’ РЅРёР¶РЅРµРµ РѕРєРЅРѕ (СѓР·РµР» в†’ СЃРІСЏР·Рё РµРіРѕ РјРѕРґРµР»Рё)."""
        sel = tview.focus()
        if not sel:
            return
        txt = (tview.item(sel, "text") or "").strip()
        m = eng.stem(txt.split()[0]) if txt else ""
        if m:
            _bottom_show(m, pick=True)

    tview.bind("<<TreeviewSelect>>", tree_live)
    _plm_extra.update({"ltv": ltv, "ltv2": ltv2, "lnb": lnb, "live_tree": live_tree,
                       "live_auto": live_auto, "bottom_show": _bottom_show})   # РґР»СЏ СЃР°РјРѕРїСЂРѕРІРµСЂРєРё

    _auto = {"done": False}

    def on_tab(ev=None):
        """РџСЂРё РІС…РѕРґРµ РЅР° РІРєР»Р°РґРєСѓ вЂ” С‚РѕР»СЊРєРѕ СЃРїРёСЃРѕРє РІРµСЂС…РЅРёС… СЃР±РѕСЂРѕРє (Р±РµР· В«СЂР°Р·РІРµСЂРЅСѓС‚СЊ РІСЃС‘В»)."""
        try:
            if nb.index(nb.select()) == 1 and not _auto["done"]:
                _auto["done"] = True
                fill_tree_view()              # СЃРІС‘СЂРЅСѓС‚С‹Р№ РІРёРґ: РєРѕСЂРµРЅСЊ + РІРµСЂС…РЅРёРµ СЃР±РѕСЂРєРё
        except Exception:
            pass

    nb.bind("<<NotebookTabChanged>>", on_tab)

    def sort_key(r, col):
        v = r.get(col, "")
        if col in ("Р—Р°РїРёСЃРµР№", "Р РµРІРёР·РёСЏ"):
            try:
                return (0, int(v))
            except (TypeError, ValueError):
                return (1, 0)
        if col == "РћР±СЉС‘Рј, РјРјВі":
            try:
                return (0, float(v))
            except (TypeError, ValueError):
                return (1, 0.0)
        if col == "Р”Р°С‚Р°":
            d = parse_dt(v)
            return (0, d.timestamp()) if d else (1, 0)
        if col == "РЎРѕР·РґР°РЅ":
            return (0, float(r.get("_created_ts") or 0))
        if col == "РР·РјРµРЅС‘РЅ":
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
        if pat:                       # Р¤РР›Р¬РўР  вЂ” РїРѕ Р’РЎР•Р™ Р‘РђР—Р•, Р° РЅРµ РїРѕ Р·Р°РіСЂСѓР¶РµРЅРЅРѕР№ СЃС‚СЂР°РЅРёС†Рµ
            rows, hits, mode = db_search_rows(pat.split(), int(settings.get("show_limit") or 50000))
            rts = [r for r in roots_of(e_folder.get(), e_folder2.get()) if os.path.isdir(r)]
            in_r = sum(1 for r in rows if path_under(r["_path"], rts)) if rts else len(rows)
            tail = (" В· РїРѕ С„РёР»СЊС‚СЂСѓ %d РІ Р±Р°Р·Рµ %d (СЃР»РѕРІР°: %s) В· РІ РїР°РїРєР°С… РѕРєРЅР° %d, РІРЅРµ РїР°РїРѕРє %d%s"
                    % (hits, db_total(None), mode, in_r, len(rows) - in_r,
                       (" В· РїРѕРєР°Р·Р°РЅС‹ РїРµСЂРІС‹Рµ %d вЂ” СѓС‚РѕС‡РЅРёС‚Рµ СЃР»РѕРІР°" % len(rows)) if hits > len(rows) else ""))
        else:
            rows = list(rows_all)
            tail = " РёР· %d Р·Р°РіСЂСѓР¶РµРЅРЅС‹С…" % len(rows_all)
        rows.sort(key=lambda r: sort_key(r, sort_state["col"]), reverse=sort_state["desc"])
        shown[:] = rows
        tree.delete(*tree.get_children())
        for r in rows:
            tree.insert("", "end", iid=row_uid(r), values=[r.get(c, "") for c in cols])
        for c in cols:
            mark = "  в–ј" if (sort_state["col"] == c and sort_state["desc"]) else \
                   ("  в–І" if sort_state["col"] == c else "")
            tree.heading(c, text=c + mark)
        lbl.config(text="РїРѕРєР°Р·Р°РЅРѕ %d%s" % (len(rows), tail))
        if keep and keep in tree.get_children():
            tree.selection_set(keep)          # РІС‹Р±РѕСЂ СЃРѕС…СЂР°РЅСЏРµС‚СЃСЏ РїСЂРё СЃРѕСЂС‚РёСЂРѕРІРєРµ/С„РёР»СЊС‚СЂРµ
        try:
            live_tree()                       # РЅРёР· РІСЃРµРіРґР° СЃР»РµРґСѓРµС‚ Р·Р° РІС‹Р±РѕСЂРѕРј (РёРЅР°С‡Рµ вЂ” РѕР±С‰РµРµ РґРµСЂРµРІРѕ)
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
            lbl.config(text="README РЅРµ РїСЂРѕС‡РёС‚Р°РЅ: %s" % e)
            return
        win = tk.Toplevel(root)
        root._readme_win = win
        win.title("README вЂ” PLM Reader")
        win.geometry("900x680")
        t = tk.Text(win, wrap="word", font=("Consolas", 9))
        t.pack(fill="both", expand=True)
        t.insert("1.0", text)

    def check_base():
        """Р‘С‹СЃС‚СЂРѕ: Р°РєС‚СѓР°Р»СЊРЅР° Р±Р°Р·Р° РёР»Рё РЅСѓР¶РµРЅ СЃРєР°РЅ (РѕР±С…РѕРґ+stat, Р‘Р•Р— С‡С‚РµРЅРёСЏ С„Р°Р№Р»РѕРІ)."""
        lbl.config(text="РїСЂРѕРІРµСЂСЏСЋ Р°РєС‚СѓР°Р»СЊРЅРѕСЃС‚СЊ Р±Р°Р·С‹вЂ¦")

        def work():
            try:
                import engine as eng
                r = eng.do_check(exclude=exclude_list(settings.get("exclude")))
            except Exception as e:
                try:
                    root.after(0, lambda: lbl.config(text="РїСЂРѕРІРµСЂРєР° РЅРµ СѓРґР°Р»Р°СЃСЊ: %s" % e))
                except Exception:
                    pass
                return
            try:
                root.after(0, lambda: show_check(r))
            except Exception:
                pass                    # РѕРєРЅРѕ СѓР¶Рµ Р·Р°РєСЂС‹С‚Рѕ вЂ” РјРѕР»С‡Р°


        threading.Thread(target=work, daemon=True).start()

    def show_check(r):
        _p = r.get("purged", 0)
        _tail = ("  В·  СЃС‚Р°СЂС‹Рµ РІРµСЂСЃРёРё РїРѕСЃР»Рµ Purge: %d вЂ” РЅРѕСЂРјР°" % _p) if _p else ""
        if r.get("need"):
            lbl.config(text="РќРЈР–Р•Рќ РЎРљРђРќ: РЅРѕРІС‹С… %d В· РёР·РјРµРЅС‘РЅРЅС‹С… %d В· РїСЂРѕРїР°Р»Рѕ %d (%.1f СЃ)%s"
                       % (r["new"], r["mod"], r["gone"], r["secs"], _tail))
        else:
            lbl.config(text="Р‘РђР—Рђ РђРљРўРЈРђР›Р¬РќРђ: РёР·РґРµР»РёР№ %d (С„Р°Р№Р»РѕРІ РЅР° РґРёСЃРєРµ %d, СЃ РєРѕРїРёСЏРјРё РІРµСЂСЃРёР№), РёР·РјРµРЅРµРЅРёР№ РЅРµС‚ (%.1f СЃ)%s"
                       % (r.get("models", r["total"]), r["total"], r["secs"], _tail))
        log_line("check: %s" % r.get("verdict", ""))

    def load_base(limit=None):
        """РџРѕРєР°Р·Р°С‚СЊ Р±Р°Р·Сѓ Р‘Р•Р— С‡С‚РµРЅРёСЏ С„Р°Р№Р»РѕРІ: СЃС‚СЂРѕРєРё РїР°СЃРїРѕСЂС‚РѕРІ РёР· plm_reader.db."""
        if not limit:
            limit = int(settings.get("show_limit") or 50000)   # Р»РёРјРёС‚ РїРѕРєР°Р·Р° вЂ” РёР· РЅР°СЃС‚СЂРѕР№РєРё В«РџРћРљРђР— СЃС‚СЂРѕРєВ»
        roots = [r for r in roots_of(e_folder.get(), e_folder2.get()) if os.path.isdir(r)]
        rows_all.clear()
        tree.delete(*tree.get_children())
        rows_all.extend(db_rows(roots or None, limit))
        redraw()
        tot = db_total(roots or None)
        where = " + ".join(roots) if roots else "РІСЃСЏ Р±Р°Р·Р°"
        lbl.config(text="РёР· Р±Р°Р·С‹: РїРѕРєР°Р·Р°РЅРѕ %d РёР· %d (%s)" % (len(rows_all), tot, where))
        log_line("base: РїРѕРєР°Р·Р°РЅРѕ %d РёР· %d (%s)" % (len(rows_all), tot, where))

    def _active_stamp():
        """РћС‚РїРµС‡Р°С‚РѕРє Р°РєС‚РёРІРЅРѕР№ Р±Р°Р·С‹ (РёРјСЏ+РІСЂРµРјСЏ) вЂ” РїРѕ РЅРµРјСѓ Р·Р°РјРµС‡Р°РµРј РїСѓР±Р»РёРєР°С†РёСЋ РґСЂСѓРіРѕРіРѕ РџРљ."""
        try:
            p = _active_db_file()
            return "%s|%d" % (os.path.basename(p), int(os.path.getmtime(p)))
        except Exception:
            return ""

    def refresh_from_db(reason=None, stamp=None):
        """РџРµСЂРµС‡РёС‚Р°С‚СЊ С‚Р°Р±Р»РёС†Сѓ РёР· РЎР’Р•Р–РђР™РЁР•Р™ Р±Р°Р·С‹ (С„РёР»СЊС‚СЂ Рё РІС‹РґРµР»РµРЅРёРµ СЃРѕС…СЂР°РЅСЏСЋС‚СЃСЏ)."""
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
        """Р Р°Р· РІ 15 СЃ: РЅРµ РїРѕСЏРІРёР»Р°СЃСЊ Р»Рё РЅР° СЃРєР»Р°РґРµ Р±РѕР»РµРµ СЃРІРµР¶Р°СЏ Р±Р°Р·Р° (РµС‘ РѕРїСѓР±Р»РёРєРѕРІР°Р» РґСЂСѓРіРѕР№ РџРљ)."""
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
                            "Р±Р°Р·Р° РѕР±РЅРѕРІР»РµРЅР° РЅР° РґСЂСѓРіРѕР№ РјР°С€РёРЅРµ вЂ” С‚Р°Р±Р»РёС†Р° РїРµСЂРµС‡РёС‚Р°РЅР°", st))
                    except Exception:
                        pass
            try:
                threading.Thread(target=work, daemon=True).start()
            except Exception:
                pass
        root.after(15000, watch_db)

    ALL_FIELDS = ["Р¤Р°Р№Р»", "РћР±РѕР·РЅР°С‡РµРЅРёРµ", "РќР°РёРјРµРЅРѕРІР°РЅРёРµ", "РњР°С‚РµСЂРёР°Р»", "РћР±СЉС‘Рј, РјРјВі", "РўРёРї",
                  "Р РѕР»СЊ", "Р РѕРґРёС‚РµР»СЊ", "Р—Р°РїРёСЃРµР№", "Р’РµСЂСЃРёР№", "Р РµРІРёР·РёСЏ", "Р”Р°С‚Р°",
                  "РЎРѕР·РґР°РЅ", "РР·РјРµРЅС‘РЅ", "РџРѕР»СЊР·РѕРІР°С‚РµР»СЊ", "Р’РµСЂСЃРёСЏ Creo", "Р“Р°Р±Р°СЂРёС‚, РјРј"]

    def save_settings():
        save_settings_file(settings)                    # Р°С‚РѕРјР°СЂРЅР°СЏ Р·Р°РїРёСЃСЊ; РѕС€РёР±РєР° вЂ” РІ Р»РѕРі

    def save_ui():
        """РЎРѕР±СЂР°С‚СЊ РІ РЅР°СЃС‚СЂРѕР№РєРё С‚Рѕ, С‡С‚Рѕ РЅР° СЌРєСЂР°РЅРµ, Рё СЃРѕС…СЂР°РЅРёС‚СЊ (Р·РѕРІС‘С‚СЃСЏ РїСЂРё Р·Р°РєСЂС‹С‚РёРё РѕРєРЅР°)."""
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

    if os.environ.get("PLM_SELFCHECK"):        # СЃР°РјРѕРїСЂРѕРІРµСЂРєР° РІРёРґР°: РєР»СЋС‡РµРІС‹Рµ РєРЅРѕРїРєРё РІРёРґРЅС‹ Рё РІРЅСѓС‚СЂРё РѕРєРЅР°
        def _selfcheck():
            try:
                root.update_idletasks()
                w, h = root.winfo_width(), root.winfo_height()
                bad = []
                for name, wdg in (("РџСѓС‚РёвЂ¦", btn_paths), ("РџРѕРєР°Р·С‹РІР°С‚СЊ", sp_limit), ("РЎРєР°РЅРёСЂРѕРІР°С‚СЊ", btn),
                                  ("РЎС‚РѕРї", b_stop), ("РђРєС‚СѓР°Р»СЊРЅРѕ?", b_check),
                                  ("Purge-РџР›РђРќ", b_purge_plan), ("Purge-Р±СЌРєР°Рї", b_purge_run)):
                    vis = wdg.winfo_ismapped()
                    x = wdg.winfo_rootx() - root.winfo_rootx()
                    y = wdg.winfo_rooty() - root.winfo_rooty()
                    if not vis or not (0 <= x < w and 0 <= y < h):
                        bad.append("%s(vis=%s,%d,%d)" % (name, vis, x, y))
                log_line("selfcheck: РѕРєРЅРѕ %dx%d, РїСЂРѕРІРµСЂРµРЅРѕ РІРёРґР¶РµС‚РѕРІ 7, СЃРєСЂС‹С‚Рѕ/РІРЅРµ РѕРєРЅР°: %s"
                         % (w, h, ", ".join(bad) if bad else "РЅРµС‚"))
                log_line("selfcheck: Р»РёРјРёС‚=%s | %s | %s"
                         % (sp_limit.get(), lbl_p.cget("text").replace("\n", " | ")[:80],
                            lbl_e.cget("text").replace("\n", " | ")[:80]))
                tabs = nb.tabs()
                bad_tabs = []
                for t in tabs:
                    nb.select(t)
                    root.update_idletasks()
                    if not ltv.winfo_ismapped():
                        bad_tabs.append(nb.tab(t, "text").strip())
                log_line("selfcheck: РЅРёР¶РЅРµРµ РґРµСЂРµРІРѕ РїСЂРѕРёР·РІРѕРґСЃС‚РІР° РІРёРґРЅРѕ РЅР° РІРєР»Р°РґРєР°С…: %s"
                         % (("РќР•Рў РЅР°: " + ", ".join(bad_tabs)) if bad_tabs
                            else "РІСЃРµ %d" % len(tabs)))
                log_line("selfcheck: РїРѕР»РѕСЃР° РЅРёР·Р° вЂ” lpane(%s,h=%d) liv(%s,h=%d) ltv(%s,h=%d)"
                         % (lpane.winfo_ismapped(), lpane.winfo_height(),
                            liv.winfo_ismapped(), liv.winfo_height(),
                            ltv.winfo_ismapped(), ltv.winfo_height()))
                log_line("selfcheck: РЅРёР¶РЅРёР№ РЅРѕСѓС‚Р±СѓРє вЂ” РІРєР»Р°РґРѕРє %d, Р°РєС‚РёРІРЅР° В«%sВ», ltv2(h=%d)"
                         % (len(lnb.tabs()), lnb.tab(lnb.select(), "text").strip(),
                            ltv2.winfo_height()))
                if os.environ.get("PLM_SELFCHECK") == "2":     # РїСЂРѕРІРµСЂРєР° РєРЅРѕРїРєРё РџРЈР Р“Р•: РџР›РђРќ С†РµР»РёРєРѕРј
                    try:
                        purge_show()
                        log_line("selfcheck: РџРЈР Р“Р• РџР›РђРќ РІС‹РїРѕР»РЅРµРЅ вЂ” РѕРєРЅРѕ РїР»Р°РЅР° РѕС‚РєСЂС‹С‚Рѕ")
                    except Exception as e:
                        log_line("selfcheck: РџРЈР Р“Р• РџР›РђРќ СѓРїР°Р»: %s" % e)
                nb.select(tabs[0])
            except Exception as e:
                log_line("selfcheck: РѕС€РёР±РєР° %s" % e)
        root.after(1500, _selfcheck)

    def split_list(s):
        return [x.strip() for x in (s or "").replace(";", ",").split(",") if x.strip()]

    def choose_columns():
        win = tk.Toplevel(root)
        win.title("РЎС‚РѕР»Р±С†С‹ Рё РїР°СЂР°РјРµС‚СЂС‹ вЂ” СЃРѕС…СЂР°РЅСЏСЋС‚СЃСЏ РІ РЅР°СЃС‚СЂРѕР№РєР°С…")
        win.geometry("780x600")
        ttk.Label(win, text="РљР°РєРёРµ СЃС‚РѕР»Р±С†С‹ РїРѕРєР°Р·С‹РІР°С‚СЊ (В«Р¤Р°Р№Р»В» вЂ” РІСЃРµРіРґР° РїРµСЂРІС‹Р№):").pack(anchor="w", padx=8, pady=(8, 0))
        box = ttk.Frame(win, padding=8)
        box.pack(fill="x")
        vars_ = {}
        for i, f in enumerate(ALL_FIELDS):
            vars_[f] = tk.BooleanVar(value=f in cols)
            cb = ttk.Checkbutton(box, text=f, variable=vars_[f])
            cb.grid(row=i // 3, column=i % 3, sticky="w", padx=6, pady=2)
            if f == "Р¤Р°Р№Р»":
                cb.state(["disabled"])
        pf = ttk.Frame(win, padding=8)
        pf.pack(fill="x")
        ttk.Label(pf, text="РРјРµРЅР° РїР°СЂР°РјРµС‚СЂРѕРІ РґР»СЏ В«РћР±РѕР·РЅР°С‡РµРЅРёРµВ» (С‡РµСЂРµР· Р·Р°РїСЏС‚СѓСЋ, РїРѕ РїРѕСЂСЏРґРєСѓ РїРѕРёСЃРєР°):").pack(anchor="w")
        e_des = ttk.Entry(pf, width=92)
        e_des.insert(0, ", ".join(settings.get("param_designation", DEFAULT_SETTINGS["param_designation"])))
        e_des.pack(fill="x", pady=(0, 6))
        ttk.Label(pf, text="РРјРµРЅР° РїР°СЂР°РјРµС‚СЂРѕРІ РґР»СЏ В«РќР°РёРјРµРЅРѕРІР°РЅРёРµВ»:").pack(anchor="w")
        e_nam = ttk.Entry(pf, width=92)
        e_nam.insert(0, ", ".join(settings.get("param_name", DEFAULT_SETTINGS["param_name"])))
        e_nam.pack(fill="x", pady=(0, 6))
        ttk.Label(pf, text="РРјРµРЅР° РїР°СЂР°РјРµС‚СЂРѕРІ РґР»СЏ В«РњР°С‚РµСЂРёР°Р»В»:").pack(anchor="w")
        e_mat = ttk.Entry(pf, width=92)
        e_mat.insert(0, ", ".join(settings.get("param_material", DEFAULT_SETTINGS["param_material"])))
        e_mat.pack(fill="x")
        ttk.Label(win, text="РЎРїРёСЃРѕРє РїСЂРѕРІРµСЂСЏРµС‚СЃСЏ РїРѕ РїРѕСЂСЏРґРєСѓ вЂ” Р±РµСЂС‘С‚СЃСЏ РїРµСЂРІРѕРµ РќР•РџРЈРЎРўРћР•.\n"
                            "Р Р°Р·РґРµР»РёС‚РµР»СЊ РїСЂР°РІРёР» вЂ” Р—РђРџРЇРўРђРЇ. РџСЂР°РІРёР»Рѕ = РёРјСЏ РїР°СЂР°РјРµС‚СЂР° РР›Р С€Р°Р±Р»РѕРЅ:\n"
                            "  {NAME_1} {NAME_2}      в†’ СЃРєР»РµРёС‚ РІ РѕРґРЅСѓ СЃС‚СЂРѕРєСѓ: M5x20 Р“РћРЎРў 11738-72\n"
                            "  {РРњРЇ} вЂ” Р·РЅР°С‡РµРЅРёРµ; \"С‚РµРєСЃС‚\" вЂ” РІСЃС‚Р°РІРёС‚СЊ С‚РµРєСЃС‚ (РєР°РІС‹С‡РєРё РќР• РІС‹РІРѕРґСЏС‚СЃСЏ);\n"
                            "  + вЂ” СЃРєР»РµР№РєР° Р±РµР· РїСЂРѕР±РµР»Р°; РѕР±С‹С‡РЅС‹Р№ РїСЂРѕР±РµР» = РїСЂРѕР±РµР»; РїСѓСЃС‚С‹Рµ С‡Р°СЃС‚Рё РѕС‚Р±СЂР°СЃС‹РІР°СЋС‚СЃСЏ.\n"
                            "РџСЂРёРјРµСЂ:  NAME_1, NAME_2, РќРђРРњР•РќРћР’РђРќРР•    РёР»Рё    {NAME_1} {NAME_2}, РќРђРРњР•РќРћР’РђРќРР•",
                  justify="left").pack(anchor="w", padx=8, pady=(0, 8))

        def apply():
            cols[:] = ["Р¤Р°Р№Р»"] + [f for f in ALL_FIELDS if f != "Р¤Р°Р№Р»" and vars_[f].get()]
            settings["columns"] = list(cols)
            settings["param_designation"] = split_list(e_des.get())
            settings["param_name"] = split_list(e_nam.get())
            settings["param_material"] = split_list(e_mat.get())
            save_settings()
            rebuild_tree()
            lbl.config(text="СЃС‚РѕР»Р±С†С‹ СЃРѕС…СЂР°РЅРµРЅС‹")
            win.destroy()

        ttk.Button(win, text="РџСЂРёРјРµРЅРёС‚СЊ Рё СЃРѕС…СЂР°РЅРёС‚СЊ", command=apply).pack(anchor="w", padx=8, pady=(0, 10))

    def hist_settings():
        return {"max_size_mb": float(e_max.get() or 0), "recurse": var_rec.get()}

    def show_history():
        items = tree.selection()
        if not items:
            messagebox.showinfo(APP_TITLE, "Р’С‹Р±РµСЂРёС‚Рµ СЃС‚СЂРѕРєСѓ РІ С‚Р°Р±Р»РёС†Рµ.")
            return
        row = _ROWS.get(items[0]) or {}
        path = row.get("_path")
        if not path:
            return
        history_window(root, tk, ttk, filedialog,
                       "РСЃС‚РѕСЂРёСЏ РёР·РјРµРЅРµРЅРёР№ вЂ” %s" % os.path.basename(path),
                       lambda: history_rows_copy_aware(path, hist_settings()),
                       settings=settings, save_settings=save_settings,
                       status=os.path.basename(path))

    def show_folder_history():
        folder = e_folder.get().strip()
        if not os.path.isdir(folder):
            messagebox.showwarning(APP_TITLE, "РЎРЅР°С‡Р°Р»Р° РІС‹Р±РµСЂРёС‚Рµ РїР°РїРєСѓ.")
            return
        history_window(root, tk, ttk, filedialog,
                       "РСЃС‚РѕСЂРёСЏ РёР·РјРµРЅРµРЅРёР№ вЂ” %s" % folder,
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
                    lbl.config(text="РёС‰Сѓ С„Р°Р№Р»С‹: РЅР°Р№РґРµРЅРѕ %d%s (%.0f СЃ)"
                               % (msg[1], " вЂ” РѕР±С…РѕРґ РіРѕС‚РѕРІ, С‡РёС‚Р°СЋ РёР·РјРµРЅС‘РЅРЅРѕРµвЂ¦" if msg[2] else "", _secs))
                elif msg[0] == "prog":
                    _secs = time.time() - getattr(root, "_plm_t0", time.time())
                    lbl.config(text="%d / %d В· РїСЂРѕС‡РёС‚Р°РЅРѕ %d, РїСЂРѕРїСѓС‰РµРЅРѕ (СѓР¶Рµ РІ Р±Р°Р·Рµ) %d В· %.0f СЃ В· %s"
                               % (msg[1], msg[2], msg[4], msg[5], _secs, msg[3][:40]))
                else:
                    st = msg[2] if len(msg) > 2 else {}
                    _secs = time.time() - getattr(root, "_plm_t0", time.time())
                    if st.get("busy"):
                        lbl.config(text="Р—Р°РЅСЏС‚Рѕ: %s" % st["error"])
                    elif st.get("error"):
                        lbl.config(text="СЃРєР°РЅ РЅРµ СѓРґР°Р»СЃСЏ: %s" % st["error"])
                    else:
                        roots_now = [r for r in roots_of(e_folder.get(), e_folder2.get())
                                     if os.path.isdir(r)]
                        rows = db_rows(roots_now or None, int(settings.get("show_limit") or 50000))
                        total = db_total(roots_now or None)
                        rows_all.clear()
                        tree.delete(*tree.get_children())
                        rows_all.extend(rows)
                        redraw()
                        lbl.config(text="СЃРєР°РЅ Р±Р°Р·С‹ Р·Р° %.1f СЃ: РЅРѕРІС‹С… %d В· РёР·РјРµРЅС‘РЅРЅС‹С… %d В· "
                                        "РїСЂРѕРїСѓС‰РµРЅРѕ (СѓР¶Рµ РІ Р±Р°Р·Рµ) %d В· РІ Р±Р°Р·Рµ %d, РїРѕРєР°Р·Р°РЅРѕ %d В· РёСЃРєР»СЋС‡РµРЅРѕ РїР°РїРѕРє %d В· "
                                        "СѓР±СЂР°РЅРѕ СЃС‚СЂРѕРє %d%s"
                                   % (_secs, st.get("new", 0), st.get("mod", 0), st.get("skipped", 0),
                                      total, len(rows), len(exclude_list(settings.get("exclude"))),
                                      st.get("excluded", 0),
                                      "; РћРЎРўРђРќРћР’Р›Р•РќРћ" if st.get("stopped") else ""))
                        log_line("scan: %s -> РЅРѕРІС‹С… %d, РёР·РјРµРЅС‘РЅРЅС‹С… %d, РїСЂРѕРїСѓС‰РµРЅРѕ %d Р·Р° %.1f СЃ"
                                 % (" + ".join(roots_now) or "РІСЃСЏ Р±Р°Р·Р°", st.get("new", 0),
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
            res = eng.scan_to_base(roots, float(opts.get("max_size_mb", 24)), 3600.0,   # V86: В«or 8В» СѓР±РёРІР°Р» 0
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
            messagebox.showwarning(APP_TITLE, "Р’С‹Р±РµСЂРёС‚Рµ РїР°РїРєСѓ.")
            return
        folder2 = norm_path(e_folder2.get()) if e_folder2.get().strip() else ""
        roots = [r for r in scan_roots(folder, folder2, settings.get("folders")) if os.path.isdir(r)]
        if folder2 and not os.path.isdir(folder2):
            messagebox.showwarning(APP_TITLE, "РџР°РїРєР°2 РЅРµ РЅР°Р№РґРµРЅР° вЂ” СЃРєР°РЅ РµС‘ РїСЂРѕРїСѓСЃС‚РёС‚,\n"
                                              "РЅРѕ РїСѓС‚СЊ СЏ СЃРѕС…СЂР°РЅСЋ:\n%s" % folder2)
        # СЃРїРёСЃРѕРє РїСѓС‚РµР№ РґРµСЂР¶РёРј СЃРѕРіР»Р°СЃРЅС‹Рј СЃ РїРѕР»СЏРјРё: РїРµСЂРІС‹Рµ РґРІРµ вЂ” РџР°РїРєР°1 Рё РџР°РїРєР°2, РґР°Р»СЊС€Рµ вЂ” РёР· В«РџСѓС‚РµР№вЂ¦В»
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
        root._plm_scan_active = True          # РїРѕРєР° СЃРєР°РЅ РёРґС‘С‚ вЂ” Р°РІС‚РѕРѕР±РЅРѕРІР»РµРЅРёРµ РЅРµ РјРµС€Р°РµС‚
        root._plm_t0 = time.time()
        _hint = ""
        try:
            import engine as _e
            _roots = json.loads(_e.meta_get("roots") or "null") or []
            if _roots and not any(folder.lower().startswith(r.rstrip("\\").lower()) for r in _roots):
                _hint = "  (РїР°РїРєР° Р’РќР• Р±Р°Р·С‹: %s вЂ” Р±СѓРґРµС‚ РїСЂРѕС‡РёС‚Р°РЅРѕ Р·Р°РЅРѕРІРѕ)" % "; ".join(_roots)
        except Exception:
            pass
        lbl.config(text="РёС‰Сѓ С„Р°Р№Р»С‹вЂ¦" + _hint)
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
            lbl.config(text="РІС‹РіСЂСѓР¶РµРЅРѕ: %s" % os.path.basename(p))

    def _bom_rows(model, depth=25):
        """V83: СЂРµРєСѓСЂСЃРёРІРЅС‹Р№ СЃРѕСЃС‚Р°РІ РёР·РґРµР»РёСЏ РґР»СЏ CSV: [(СѓСЂРѕРІРµРЅСЊ, РјРѕРґРµР»СЊ, РѕР±РѕР·РЅР°С‡РµРЅРёРµ, РЅР°РёРјРµРЅРѕРІР°РЅРёРµ,
        РјР°С‚РµСЂРёР°Р», РєРѕР»-РІРѕ, РѕР±СЉС‘Рј, rev, СЂРѕР»СЊ)]. РљРѕР»-РІРѕ вЂ” РЅР° СЂРѕРґРёС‚РµР»СЊСЃРєСѓСЋ РїРѕР·РёС†РёСЋ; РїРѕРІС‚РѕСЂС‹ СЃРѕС…СЂР°РЅСЏСЋС‚СЃСЏ."""
        down = eng.plm_down_data(model, depth)
        plan, order, cap = [(model, 1, 0)], [], 50000
        qi = 0
        while qi < len(plan):
            m, q, lvl = plan[qi]
            qi += 1
            order.append((m, q, lvl))
            if len(order) >= cap:
                break
            for ch, cq in down.get(m, []) or []:
                plan.append((ch, cq, lvl + 1))
        info = {}
        mods = [m for m, _, _ in order]
        for s in range(0, len(mods), 500):     # РїР°С‡РєР°РјРё вЂ” Р»РёРјРёС‚ РїР°СЂР°РјРµС‚СЂРѕРІ SQLite
            info.update(eng.models_info(mods[s:s + 500]))
        rows = []
        for m, q, lvl in order:
            i8 = info.get(m, ("", "", "", 0, "", "", 0, 0))
            rows.append((lvl, m, i8[0], i8[1], i8[2], q,
                         ("%.0f" % i8[3]) if i8[3] else "", i8[4], i8[5]))
        return rows

    def export_bom():
        """V83: СЃРѕСЃС‚Р°РІ С‚РµРєСѓС‰РµРіРѕ РёР·РґРµР»РёСЏ РЅРёР¶РЅРµРіРѕ РѕРєРЅР° -> CSV (utf-8-sig + В«;В», РєР°Рє save_csv)."""
        import csv
        m = _last.get("model") or _last.get("pick") or ""
        if not m:
            lbl.config(text="РІС‹Р±РµСЂРё РёР·РґРµР»РёРµ вЂ” РѕС‚ С‡РµРіРѕ СЃС‚СЂРѕРёС‚СЊ СЃРѕСЃС‚Р°РІ CSV")
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv",
                                         initialfile="%s_СЃРѕСЃС‚Р°РІ.csv" % m,
                                         filetypes=[("CSV", "*.csv")])
        if not p:
            return
        try:
            rows = _bom_rows(m)
            with open(p, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(["РЈСЂРѕРІРµРЅСЊ", "РњРѕРґРµР»СЊ", "РћР±РѕР·РЅР°С‡РµРЅРёРµ", "РќР°РёРјРµРЅРѕРІР°РЅРёРµ",
                            "РњР°С‚РµСЂРёР°Р»", "РљРѕР»-РІРѕ", "РћР±СЉС‘Рј,РјРјВі", "Rev", "Р РѕР»СЊ"])
                w.writerows(rows)
            lbl.config(text="РІС‹РіСЂСѓР¶РµРЅРѕ: %s (РїРѕР·РёС†РёР№ %d)" % (os.path.basename(p), len(rows)))
        except Exception as e:
            lbl.config(text="CSV РЅРµ РІС‹РіСЂСѓР¶РµРЅ: %s" % e)

    # --- РљРћРџРР РћР’РђРўР¬ / Р’РЎРўРђР’РРўР¬: Ctrl+C/V/X/A Рё РџРљРњ РІРѕ РІСЃРµС… РїРѕР»СЏС… Рё С‚Р°Р±Р»РёС†Р°С… ---
    # Р“Р РђР‘Р›РЇ (V35): РќР•Р›Р¬Р—РЇ РІРµС€Р°С‚СЊ bind_all РЅР° Ctrl+V Рё С‚СѓС‚ Р¶Рµ РґРµР»Р°С‚СЊ event_generate("<<Paste>>") вЂ”
    # Сѓ РїРѕР»РµР№ (Entry/TEntry/Text/Spinbox/Combobox) РЎР’РћР™ class-binding РЅР° <<Paste>>, Р° РѕРЅ СЃСЂР°Р±Р°С‚С‹РІР°РµС‚
    # Р РђРќР¬РЁР• С‚РµРіР° "all" (РїРѕСЂСЏРґРѕРє bindtags: РІРёРґР¶РµС‚ в†’ РєР»Р°СЃСЃ в†’ СЂРѕРґРёС‚РµР»СЊ в†’ all). РС‚РѕРі: РЅР°С‚РёРІРЅР°СЏ РІСЃС‚Р°РІРєР°
    # + РЅР°С€Р° = Р”Р’Р• РІСЃС‚Р°РІРєРё РїРѕРґСЂСЏРґ (Р¶Р°Р»РѕР±Р° РІР»Р°РґРµР»СЊС†Р° 02.10.2026, РѕРєРЅРѕ В«РЎС‚РѕР»Р±С†С‹ Рё РїР°СЂР°РјРµС‚СЂС‹В»).
    # РџРѕСЌС‚РѕРјСѓ: РµСЃР»Рё РєР»Р°СЃСЃ РІРёРґР¶РµС‚Р° СѓРјРµРµС‚ СЃРѕР±С‹С‚РёРµ СЃР°Рј вЂ” РјРѕР»С‡Р° РІРѕР·РІСЂР°С‰Р°РµРј "break" Рё РќР• РіРµРЅРµСЂРёСЂСѓРµРј.
    _NATIVE = {}

    def _has_native(w, seq):
        """Р•СЃС‚СЊ Р»Рё Сѓ РєР»Р°СЃСЃР° РІРёРґР¶РµС‚Р° СЃРѕР±СЃС‚РІРµРЅРЅР°СЏ РѕР±СЂР°Р±РѕС‚РєР° РІРёСЂС‚СѓР°Р»СЊРЅРѕРіРѕ СЃРѕР±С‹С‚РёСЏ."""
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
        """РљРѕРїРёСЂРѕРІР°С‚СЊ РџР РЇРњРћ (СЂРѕРґРЅРѕР№ <<Copy>> РІ СЂСѓСЃСЃРєРѕР№ СЂР°СЃРєР»Р°РґРєРµ РЅРµ СЃСЂР°Р±Р°С‚С‹РІР°РµС‚)."""
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
        """Р’СЃС‚Р°РІРёС‚СЊ РџР РЇРњРћ РёР· Р±СѓС„РµСЂР° (СЂРѕРґРЅРѕР№ <<Paste>> РІ СЂСѓСЃСЃРєРѕР№ СЂР°СЃРєР»Р°РґРєРµ РЅРµ СЃСЂР°Р±Р°С‚С‹РІР°РµС‚)."""
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
            w.focus_set()                      # РґРµР№СЃС‚РІРёСЏ вЂ” РїРѕ Р­РўРћРњРЈ РІРёРґР¶РµС‚Сѓ
        except Exception:
            pass
        m = tk.Menu(root, tearoff=0)
        try:
            m.add_command(label="РљРѕРїРёСЂРѕРІР°С‚СЊ", command=_on_copy)
            if not isinstance(w, ttk.Treeview):
                m.add_command(label="Р’С‹СЂРµР·Р°С‚СЊ", command=_on_cut)
                m.add_command(label="Р’СЃС‚Р°РІРёС‚СЊ", command=_on_paste)
            m.add_separator()
            m.add_command(label="Р’С‹РґРµР»РёС‚СЊ РІСЃС‘", command=_sel_all)
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

    # Ctrl+C/V/X/A РІ Р›Р®Р‘РћР™ СЂР°СЃРєР»Р°РґРєРµ. Р’ РєРёСЂРёР»Р»РёС†Рµ keysym РґСЂСѓРіРѕР№, РїРѕСЌС‚РѕРјСѓ <Control-c>
    # РЅРµ СЃСЂР°Р±Р°С‚С‹РІР°РµС‚; РѕСЂРёРµРЅС‚РёСЂСѓРµРјСЃСЏ РЅР° Р¤РР—РР§Р•РЎРљРЈР® РєР»Р°РІРёС€Сѓ (keycode=VK: C=67, V=86, X=88, A=65)
    # РїР»СЋСЃ Р·Р°РїР°СЃРЅРѕР№ РІР°СЂРёР°РЅС‚ РїРѕ keysym (Р»Р°С‚РёРЅРёС†Р° Рё РєРёСЂРёР»Р»РёС†Р°).
    def _clip_ctrl(ev):
        # Р›РђРўРРќРЎРљРђРЇ СЂР°СЃРєР»Р°РґРєР°: Сѓ РїРѕР»РµР№ (Entry/TEntry/Text/Spinbox/Combobox) Р•РЎРўР¬ РЅР°С‚РёРІРЅС‹Р№
        # `<<Copy/Paste/Cut/SelectAll>>` (РїСЂРѕРІРµСЂРµРЅРѕ `bind <РєР»Р°СЃСЃ> <<Paste>>`), Рё РѕРЅ СЃСЂР°Р±Р°С‚С‹РІР°РµС‚
        # Р РђРќР¬РЁР• С‚РµРіР° "all" (РїРѕСЂСЏРґРѕРє РІРёРґР¶РµС‚в†’РєР»Р°СЃСЃв†’СЂРѕРґРёС‚РµР»СЊв†’all). РџРѕСЌС‚РѕРјСѓ РќР• РґСѓР±Р»РёСЂСѓРµРј: РѕС‚РґР°С‘Рј РїРѕР»СЋ.
        # РќРµС‚ РЅР°С‚РёРІРЅРѕРіРѕ (Treeview) вЂ” РґРµР»Р°РµРј СЃР°РјРё. РљРР РР›Р›РР¦Рђ/РїСЂРѕС‡Р°СЏ СЂР°СЃРєР»Р°РґРєР°: РЅР°С‚РёРІРЅРѕРіРѕ РЅРµС‚ РІРѕРІСЃРµ в†’
        # РґРµР»Р°РµРј СЃР°РјРё РїРѕ Р¤РР—РР§Р•РЎРљРћР™ РєР»Р°РІРёС€Рµ (keycode: C=67, V=86, X=88, A=65 вЂ” РЅРµ Р·Р°РІРёСЃРёС‚ РѕС‚ СЂР°СЃРєР»Р°РґРєРё).
        w = _foc()
        kc = getattr(ev, "keycode", None)
        ks = (getattr(ev, "keysym", "") or "").lower()
        latin = {"c": ("<<Copy>>", _on_copy), "v": ("<<Paste>>", _on_paste),
                 "x": ("<<Cut>>", _on_cut), "a": ("<<SelectAll>>", _sel_all)}
        if ks in latin:
            seq, fn = latin[ks]
            if w is not None and _has_native(w, seq):
                return "break"            # РїРѕР»Рµ РѕР±СЂР°Р±РѕС‚Р°РµС‚ СЃР°РјРѕ вЂ” Р”Р’РћР™РќРћР™ РІСЃС‚Р°РІРєРё РЅРµ Р±СѓРґРµС‚
            return fn(ev)
        if kc == 67:
            return _on_copy(ev)
        if kc == 86:
            return _on_paste(ev)
        if kc == 88:
            return _on_cut(ev)
        if kc == 65:
            return _sel_all(ev)

    # 07.10.2026: Р±СѓРєРІРµРЅРЅС‹Рµ Ctrl-РїСЂРёРІСЏР·РєРё РЈР‘Р РђРќР« вЂ” РёС… РґСѓР±Р»РёСЂРѕРІР°Р» РѕР±С‰РёР№ `_clip_ctrl` (РїР»СЋСЃ РЅР°С‚РёРІРЅС‹Р№
    # РєР»Р°СЃСЃ-Р±Р°РЅС‚РёРЅРі РїРѕР»РµР№) в†’ Р”Р’РћР™РќРђРЇ РІСЃС‚Р°РІРєР° Ctrl+V. РћСЃС‚Р°СЋС‚СЃСЏ С‚РѕР»СЊРєРѕ Insert-РІР°СЂРёР°РЅС‚С‹ (РёС… `_clip_ctrl`
    # РЅРµ С‚СЂРѕРіР°РµС‚ вЂ” РґСЂСѓРіРѕР№ keycode) + РµРґРёРЅС‹Р№ СЂР°Р·Р±РѕСЂ `_clip_ctrl` РЅРёР¶Рµ.
    for _seq, _fn in (
        ("<Control-Insert>", _on_copy), ("<Shift-Insert>", _on_paste),
    ):
        try:
            root.bind_all(_seq, _fn)
        except Exception:
            pass
    root.bind_all("<Control-KeyPress>", _clip_ctrl, add="+")
    root.after(700, _bind_clip_all)                 # РџРљРњ-РјРµРЅСЋ РІ СЃСѓС‰РµСЃС‚РІСѓСЋС‰РёС… РїРѕР»СЏС…

    def _offer_archive_cleanup():
        """РЎРђРњРћРџР•Р Р•РЎРўР РћР™РљРђ: РµСЃР»Рё РІ Р±Р°Р·Рµ РѕСЃС‚Р°Р»СЃСЏ С‚СЏР¶С‘Р»С‹Р№ Р°СЂС…РёРІРЅС‹Р№ СЃС‹СЂРѕР№ РёРјРїРѕСЂС‚ вЂ” РїСЂРµРґР»РѕР¶РёС‚СЊ СѓР±СЂР°С‚СЊ.
        Р Р°Р·РјРµСЂС‹/РёСЃС‚РѕСЂРёСЏ (arch_dims/arch_dim_ch) Рё С‚РµРєСѓС‰РµРµ СЃРѕСЃС‚РѕСЏРЅРёРµ РќР• С‚СЂРѕРіР°РµРј."""
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
                    "РЈР±РѕСЂРєР° Р°СЂС…РёРІР°",
                    "Р’ Р±Р°Р·Рµ %s Р»РёС€РЅРёС… Р°СЂС…РёРІРЅС‹С… СЃС‚СЂРѕРє (СЃС‹СЂРѕР№ РёРјРїРѕСЂС‚ СЃСЂРµР·РѕРІ).\n\n"
                    "РЈР±СЂР°С‚СЊ? Р‘Р°Р·Р° СѓРјРµРЅСЊС€РёС‚СЃСЏ РІ СЂР°Р·С‹. Р Р°Р·РјРµСЂС‹/РёСЃС‚РѕСЂРёСЏ Рё РўР•РљРЈР©Р•Р• СЃРѕСЃС‚РѕСЏРЅРёРµ "
                    "РёР·РґРµР»РёР№ РѕСЃС‚Р°РЅСѓС‚СЃСЏ." % rus(n)):
                def work():
                    res = eng.cleanup_archive_tables(do=True)
                    tail = ("\n(СЃР¶Р°С‚РёРµ С„Р°Р№Р»Р° РЅРµ РїСЂРѕС€Р»Рѕ: %s)" % res.get("vacuum_error")
                            ) if res.get("vacuum_error") else ""
                    root.after(0, lambda: messagebox.showinfo(
                        "РЈР±РѕСЂРєР° Р°СЂС…РёРІР°",
                        "РЈР±СЂР°РЅРѕ С‚Р°Р±Р»РёС†: %d, СЃС‚СЂРѕРє: %s.%s"
                        % (len(res.get("dropped", [])), rus(res.get("rows", 0)), tail)))
                threading.Thread(target=work, daemon=True).start()

        try:
            root.after(0, ask)
        except Exception:
            pass

    root.after(1200, _offer_archive_cleanup)

    btn.config(command=go)
    _bs = db_summary()
    log_line("base: РёР·РґРµР»РёР№ %d, С„Р°Р№Р»РѕРІ СЃ РєРѕРїРёСЏРјРё РІРµСЂСЃРёР№ %d, СЃРІСЏР·РµР№ %d, РїР°РїРѕРє %d, РёР·РјРµРЅРµРЅРёР№ %d"
             % (_bs.get("models", 0), _bs.get("files", 0), _bs.get("links", 0),
                _bs.get("folders", 0), _bs.get("changes", 0)))
    if _bs.get("files"):
        # V35: С†РёС„СЂС‹ РїРѕ-С‡РµР»РѕРІРµС‡РµСЃРєРё вЂ” РіР»Р°РІРЅР°СЏ = РР—Р”Р•Р›РРЇ (Р±РµР· РґСѓР±Р»РµР№ .1/.2), СЂСЏРґРѕРј С„Р°Р№Р»С‹ СЃ РєРѕРїРёСЏРјРё РІРµСЂСЃРёР№
        # 07.10.2026: РµСЃР»Рё РїСЂР°РІРёР»Р° СЂР°Р·Р±РѕСЂР° РЅРѕРІРµРµ Р±Р°Р·С‹ вЂ” РџР РЇРњРћ Р“РћР’РћР РРњ, С‡С‚Рѕ РЅСѓР¶РµРЅ РїРѕР»РЅС‹Р№ СЃРєР°РЅ
        _tag_note = "   вљ  РџР РђР’РР›Рђ Р РђР—Р‘РћР Рђ РР—РњР•РќРР›РРЎР¬ вЂ” РЅСѓР¶РµРЅ РЎРљРђРќ (РїРµСЂРµС‡РёС‚Р°РµС‚ РІСЃРµ С„Р°Р№Р»С‹)"
        try:
            _tag_note = _tag_note if eng.parser_tag_changed() else ""
        except Exception:
            _tag_note = ""
        lbl.config(text="Р±Р°Р·Р°: РёР·РґРµР»РёР№ %d (С„Р°Р№Р»РѕРІ СЃ РєРѕРїРёСЏРјРё РІРµСЂСЃРёР№ %d) В· РёР·РјРµРЅРµРЅРёР№ %d вЂ” С‡РёС‚Р°СЋ РёР· Р±Р°Р·С‹вЂ¦%s"
                   % (_bs.get("models", 0), _bs.get("files", 0), _bs.get("changes", 0), _tag_note))
        load_base()
        root._plm_db_stamp = _active_stamp()
        check_base()
        root.after(500, live_auto)         # РЅРёР¶РЅРµРµ РґРµСЂРµРІРѕ РџР›Рњ СЃС‚СЂРѕРёС‚СЃСЏ СЃР°РјРѕ РїСЂРё РѕС‚РєСЂС‹С‚РёРё

    root.after(15000, watch_db)            # Р°РІС‚РѕРѕР±РЅРѕРІР»РµРЅРёРµ: РµСЃР»Рё Р±Р°Р·Сѓ РѕР±РЅРѕРІРёР» РґСЂСѓРіРѕР№ РџРљ

    # 07.10.2026 (V54): РќРђРЎРўР РћР™РљР вЂ” РЎР›Р•Р’Рђ (СѓР·РєР°СЏ РїСЂРѕРєСЂСѓС‡РёРІР°РµРјР°СЏ РєРѕР»РѕРЅРєР°), СЃС‚Р°С‚СѓСЃ вЂ” Р’РќРР—РЈ,
    # РѕСЃРЅРѕРІРЅРѕРµ РїРѕР»Рµ вЂ” РџРћРџРћР›РђРњ СЃРїСЂР°РІР° (РІРµСЂС…: СЃРїРёСЃРѕРє РёР·РґРµР»РёР№, РЅРёР·: РґРµС‚Р°Р»Рё)
    try:
        for _w in (top, data, vpan, lhost):
            _w.pack_forget()
        data.pack(side="bottom", fill="x", padx=6, pady=(0, 6))    # СЃР°РјС‹Р№ РЅРёР· вЂ” СЃС‚СЂРѕРєР° СЃРѕСЃС‚РѕСЏРЅРёСЏ
        lhost.pack(side="left", fill="y", padx=(6, 0), pady=6)     # СЃР»РµРІР° вЂ” РЅР°СЃС‚СЂРѕР№РєРё Рё РєРЅРѕРїРєРё
        vpan.pack(side="left", fill="both", expand=True, padx=6, pady=(0, 6))   # СЃРїСЂР°РІР° вЂ” РґРІР° РѕРєРЅР°
    except Exception:
        pass

    try:                                   # РѕРєРЅРѕ РЅРµ В«РїСЂС‹РіР°РµС‚В» РїСЂРё РїРµСЂРµРєР»СЋС‡РµРЅРёРё РІРєР»Р°РґРѕРє
        root.update_idletasks()
        root.geometry("1520x900")          # СЃР»РµРІР° РїР°РЅРµР»СЊ РЅР°СЃС‚СЂРѕРµРє, СЃРїСЂР°РІР° РґРІР° РѕРєРЅР° РїРѕРїРѕР»Р°Рј
        _half_try()                        # СЂР°Р·РґРµР»РёС‚РµР»СЊ вЂ” РІ РїРѕР»РѕРІРёРЅСѓ (СЃ РїРѕРІС‚РѕСЂР°РјРё, РїРѕРєР° РЅРµ СЂР°Р·Р»РѕР¶РёС‚СЃСЏ)
    except Exception:
        pass
    try:                                   # С‚РёС…Р°СЏ РїСЂРѕРІРµСЂРєР° РѕР±РЅРѕРІР»РµРЅРёР№ РїСЂРё СЃС‚Р°СЂС‚Рµ (РµСЃС‚СЊ вЂ” РїСЂРµРґР»РѕР¶РёС‚)
        root.after(2500, lambda: check_updates_ui(False))
    except Exception:
        pass
    root.mainloop()

