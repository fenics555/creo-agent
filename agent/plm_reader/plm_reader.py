# -*- coding: utf-8 -*-
r"""PLM Reader — автономный просмотр данных изделий из файлов CAD (детали, сборки, чертежи).

Кнопка «Сканировать» обходит выбранную папку и показывает таблицу:
Обозначение · Наименование · Материал · Объём (мм³) · Роль/родитель · Ревизия · Записей · Дата · Пользователь · Версия Creo · Файл.
Двойной клик по строке (или «История выбранного») — полная история изменений файла, с фильтром по датам.
Кнопка «История по папке» — сводная история изменений всех моделей папки.

Запуск:
    python plm_reader.py                            — окно
    python plm_reader.py --folder DIR               — без окна: таблица в консоль
    python plm_reader.py --folder DIR --csv out.csv — без окна: выгрузка в CSV
    python plm_reader.py --history FILE|DIR         — без окна: история изменений

Зависимости: только стандартная библиотека Python (tkinter — для окна).
"""
import argparse
import csv
import datetime
import json
import os
import queue
import re
import struct
import sys
import threading
import time

# Распил: модули (plm_history/…) тянут имена из plm_reader. Если plm_reader запущен как СКРИПТ
# (__name__=="__main__", так его зовёт .bat), регистрируем его в sys.modules под именем 'plm_reader',
# иначе `from plm_reader import ...` переимпортирует файл и зациклится (ImportError).








if __name__ == "__main__":
    import sys as _sys
    _sys.modules.setdefault("plm_reader", _sys.modules["__main__"])

APP_VERSION = "V79"
APP_TITLE = "PLM Reader " + APP_VERSION          # версия ОДНА: заголовок берёт её из константы
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db")          # данные — в подпапке db\
SETTINGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings")  # настройки — в подпапке settings\
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")                          # (не затираются при обновлении кода)
CACHE_FILE = os.path.join(DATA_DIR, "scan_cache.json")






DB_FILE = os.path.join(DATA_DIR, "plm_reader.db")
























# Логи: дома — в общий D:\AI\log, на чужой машине — рядом с инструментом (переносимость)
LOG_DIR = os.environ.get("PLM_LOG") or (
    r"D:\AI\log\plm_reader" if os.path.isdir(r"D:\AI\log")
    else os.path.join(os.path.dirname(os.path.abspath(__file__)), "log"))
REPORTS_DIR = os.path.join(os.path.dirname(LOG_DIR), "reports")





















# --- 04.10.2026: связь чертёж → модель (`model_names\0 \xf8 <байт> <ИМЯ>\0`) -------------
# ГРАБЛИ, учтённые здесь (проверены на байтах, давали 0 % / 49 % разбора):
#   1) поле — `model_names` (с S), не `model_name`;
#   2) кириллица в UTF-8 = D0 9A, а 0x9A не входит в [\x20-\x7e] → нужен \x80-\xff;
#   3) байт после \xf8 не всегда 0x01 (бывают 0x08, 0x09, 0x0B).
DRW_MODEL_RE = re.compile(rb"model_names\x00\xf8[\x01-\x0f]([\x20-\x7e\x80-\xff]{3,160}?)\x00",
                          re.S)




# --- 04.10.2026: техтребования и ЧИСЛОВЫЕ параметры из тела файла --------------------
# Штатный parameters() даёт 3 параметра там, где из файла читается 9: он ищет только
# в секциях NeuPrtSld/LargeText и по другому шаблону. Ниже — проверенный разбор.
TEXT_VALUE_RE = re.compile(rb"text_value\x00([^\x00]{2,600}?)\x00", re.S)
PARAM_NUM_RE = re.compile(rb"\xe3([\x20-\x7e\xc0-\xff]{2,48}?)\x00\xe2\x32", re.S)
# служебные имена в техтребованиях: DTM1, A_1, RIGHT, ASM_DEF_CSYS …
_NOTES_JUNK = re.compile(r"^(DTM\d*|A_?\d+|D\d+|PRT|ASM|MFG)\b|"
                         r"^(RIGHT|LEFT|TOP|BOTTOM|FRONT|BACK|DEFAULT|USER_DEF|"
                         r"DEF_CSYS|CSYS|HOLDER|TIP|SHEET)\b", re.IGNORECASE)








# --- 05.10.2026: РАЗМЕРЫ детали и ИСТОРИЯ их изменений (перенесено из archive_scan.py) ---
# Число: 2^(E+1)*(1+F/4096), F — 12 БИТ, маркер первого байта ЛЮБОЙ.
#   (а) значение ДО имени:   f1 f7 37 e3 32 <3 байта> … f2 f7 38 "d12" 00
#   (б) значение ПОСЛЕ имени: d11 00 37 e3 0b 08 … <число на +9>
DIM_HEAD_RE = re.compile(rb"\xf1\xf7\x37\xe3\x32", re.S)
DIM_NAME_RE = re.compile(rb"\xf2\xf7\x38(d\d{1,5})\x00", re.S)
DIM_AFTER_RE = re.compile(rb"(?<![A-Za-z0-9_])(d\d{1,5})\x00\x37", re.S)




















def latest_path(model):
    """Путь к ПОСЛЕДНЕЙ версии файла изделия из активной базы (или None).

    ⚠️ В базе имена в ВЕРХНЕМ регистре ('A348-6-E1'), а из GUI приходят как угодно
    ('a887-94-1500-01') — ищем регистронезависимо (04.10.2026)."""
    model = (model or "").strip()
    if not model:
        return None
    try:
        con = db_conn(ro=True)
    except Exception:
        return None
    rows = []
    try:
        rows = con.execute("SELECT path FROM snapshots WHERE model=? ORDER BY mtime DESC",
                           (model,)).fetchall()
        if not rows:
            rows = con.execute("SELECT path FROM snapshots WHERE UPPER(model)=UPPER(?) "
                               "ORDER BY mtime DESC", (model,)).fetchall()
    except Exception:
        return None
    finally:
        try:
            con.close()
        except Exception:
            pass
    for (p,) in rows:
        if p and os.path.isfile(p):
            return p
    return rows[0][0] if rows else None








COLS_WIDTH = {"Обозначение": 130, "Наименование": 210, "Материал": 110, "Объём, мм³": 100,
              "Роль": 110, "Родитель": 140, "Ревизия": 80, "Записей": 80, "Версий": 70, "Дата": 120,
              "Создан": 125, "Изменён": 125, "Пользователь": 100, "Версия Creo": 110, "Файл": 215}












VERSION_FIELDS = ("Ревизия", "Дата", "Пользователь", "Версия Creo", "Объём, мм³", "Габарит, мм")
VER_COLUMNS = ("Версия", "Ревизия", "Дата", "Пользователь", "Версия Creo", "Объём, мм³",
               "Габарит, мм", "Изменение")








# ==== 07.10.2026: честная история для СКОПИРОВАННЫХ моделей ====
import engine as eng   # движок: нужен хелперам ниже (импорт чистый — только stdlib)
# Creo при копировании переносит в файл историю исходной модели. Раньше вкладка «История файла»
# печатала эти записи под ТЕКУЩИМ именем (АЛ116-…), хотя до копии модель называлась иначе
# (ЧСЗ-Л_801_04_75-401-10). Теперь источник берём из самого файла (`from_mdl_name` — движок уже
# умеет, `engine.copy_from_of`) и унаследованные записи показываем с ИСХОДНЫМ именем.

























VERSION_RE = re.compile(r"^(.*)\.([A-Za-z_]{2,4})\.(\d+)$", re.IGNORECASE)



































# ------------------------------------------------------------------ окно истории




# ------------------------------------------------------------------ окно


def main():
    try:                                   # консоль cp1251 не умеет «³» — печатаем заменой, без падения
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=APP_TITLE)
    ap.add_argument("--folder", help="папка для сканирования (режим без окна)")
    ap.add_argument("--csv", help="файл выгрузки (режим без окна)")
    ap.add_argument("--max-mb", type=float, default=DEFAULT_SETTINGS["max_size_mb"])
    ap.add_argument("--no-recurse", action="store_true")
    ap.add_argument("--history", nargs="+", help="файл(ы) или папка: показать историю изменений (без окна)")
    ap.add_argument("--history-csv", help="CSV для истории изменений")
    a = ap.parse_args()
    if a.history:
        _t0 = time.time()
        rows = []
        for f in a.history:
            if os.path.isdir(f):
                for dp, _, files in os.walk(f):
                    for n in files:
                        if MODELFILE.search(n):
                            rows += history_rows(os.path.join(dp, n), {"max_size_mb": a.max_mb})
            else:
                rows += history_rows(f, {"max_size_mb": a.max_mb})
        rows.sort(key=lambda r: (r.get("_dt", "") == "", r.get("_dt", ""), r.get("Файл", "")))
        cols = ["Файл", "Ревизия", "Дата", "Пользователь", "Компьютер", "Версия Creo", "Что изменено"]
        print(" | ".join(cols))
        for r in rows:
            print(" | ".join(str(r[c]) for c in cols))
        print("\nзаписей всего: %d за %.1f с" % (len(rows), time.time() - _t0))
        log_line("history: %s -> записей %d%s" % ("; ".join(a.history), len(rows),
                                                  " -> " + a.history_csv if a.history_csv else ""))
        if a.history_csv:
            save_csv(rows, a.history_csv)
            print("CSV: %s" % a.history_csv)
        return
    if a.folder:
        _t0 = time.time()
        rows = scan_folder(a.folder, {"max_size_mb": a.max_mb, "recurse": not a.no_recurse})
        cols = DEFAULT_SETTINGS["columns"]
        print(" | ".join(cols))
        for r in rows:
            print(" | ".join(str(r.get(c, "")) for c in cols))
        print("\nвсего моделей: %d за %.1f с" % (len(rows), time.time() - _t0))
        log_line("scan: %s -> моделей %d%s" % (a.folder, len(rows), " -> " + a.csv if a.csv else ""))
        if a.csv:
            save_csv(rows, a.csv)
            print("CSV: %s" % a.csv)
        return
    from plm_toolwin import run_gui      # Шаг 1 распила: окно вынесено; импорт ЛЕНИВЫЙ (без цикла)
    run_gui()
































from plm_parse import (
    MDL_NAME_RE,
    MODELFILE,
    _dec3_any,
    _dec_ef,
    _dec_num,
    _dim_name,
    _hist_val,
    changes_line,
    clean_computer,
    clean_name,
    dwg_models,
    kind,
    numeric_params,
    outline_mm,
    packed_at,
    parameters,
    parent_file,
    parse_changes,
    provenance,
    read_bytes,
    read_dims_all,
    read_history,
    read_history_vals,
    real_value,
    sections,
    sibling_versions,
    tech_notes,
)


from plm_dbview import (
    _active_db_file,
    _fs_date,
    _ver,
    _vol_str,
    db_conn,
    db_facts,
    db_rows,
    db_rows_map,
    db_search_rows,
    db_summary,
    db_total,
    load_cache,
    log_line,
    save_cache,
)


from plm_settings import (
    CURRENT_SETTINGS_VERSION,
    DEFAULT_SETTINGS,
    _archive_old_settings,
    _rotate_settings_backups,
    _settings_migrations,
    _validate_settings,
    apply_db_paths,
    load_settings_file,
    norm_path,
    save_settings_file,
)


from plm_scan import (
    _compose_par,
    exclude_list,
    first_param,
    match_filter,
    path_under,
    pick_latest,
    roots_of,
    scan_file,
    scan_folder,
    scan_roots,
    version_key,
)


from plm_history import (
    HIST_ALL,
    HIST_DEFAULT,
    HIST_WIDTH,
    _WINS,
    _model_paths,
    archive_dims,
    archive_history,
    copy_source_keys,
    copy_source_of,
    filter_history,
    history,
    history_folder,
    history_rows,
    history_rows_copy_aware,
    history_window,
    parse_dt,
    save_csv,
    version_change,
    version_diff,
    versions_window,
)


from plm_paths_window import (
    PathsWindow,
)


if __name__ == "__main__":
    main()

