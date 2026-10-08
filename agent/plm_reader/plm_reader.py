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

APP_VERSION = "V71"
APP_TITLE = "PLM Reader " + APP_VERSION          # версия ОДНА: заголовок берёт её из константы
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db")          # данные — в подпапке db\
SETTINGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings")  # настройки — в подпапке settings\
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")                          # (не затираются при обновлении кода)
CACHE_FILE = os.path.join(DATA_DIR, "scan_cache.json")
CURRENT_SETTINGS_VERSION = 3   # увеличивать при КАЖДОМ структурном изменении настроек (см. _settings_migrations)






DB_FILE = os.path.join(DATA_DIR, "plm_reader.db")
























# Логи: дома — в общий D:\AI\log, на чужой машине — рядом с инструментом (переносимость)
LOG_DIR = os.environ.get("PLM_LOG") or (
    r"D:\AI\log\plm_reader" if os.path.isdir(r"D:\AI\log")
    else os.path.join(os.path.dirname(os.path.abspath(__file__)), "log"))
REPORTS_DIR = os.path.join(os.path.dirname(LOG_DIR), "reports")



DEFAULT_SETTINGS = {
    "max_size_mb": 24,
    "recurse": True,
    "latest_only": True,
    "depth": 0,
    "purge_keep": 2,
    "auto_refresh": True,
    "full": False,
    "columns": ["Файл", "Обозначение", "Наименование", "Материал", "Объём, мм³",
                "Роль", "Родитель", "Ревизия", "Записей", "Версий", "Дата",
                "Создан", "Изменён", "Пользователь", "Версия Creo"],
    "param_designation": ["ОБОЗНАЧЕНИЕ", "OBOZNACHENIE", "DESIGNATION", "DESIGNATOR", "PART_NUMBER"],
    "param_name": ["НАИМЕНОВАНИЕ", "NAME", "PART_NAME", "DESCRIPTION", "TITLE"],
    "param_material": ["PTC_MASTER_MATERIAL", "MATERIAL", "МАТЕРИАЛ"],
    "folders": [],          # полный список папок сканирования (первые две = поля «Папка1»/«Папка2»)
    "exclude": [],          # папки-исключения: НЕ читать вовсе
    "db_dir": "",           # рабочая папка БАЗЫ (пусто = рядом, db\); можно увести на другой диск
    "db_mirror": [],        # папки-ЗЕРКАЛА базы: после каждого скана копия уезжает и туда
    "template_folders": [], # 07.10.2026: ПАПКИ шаблонов Creo — их модели служебные (не в связях)
    "service_models": [],   # 07.10.2026: явный список служебных стволов (если папка не намекает)
    "mirror_keep": 3,       # 07.10.2026: сколько свежих баз держать в КАЖДОМ зеркале
    "mirror_full_only": True,  # 07.10.2026: зеркалить только после ПОЛНОГО скана (не на каждый)
    "show_limit": 50000,    # сколько строк показывать за раз (крутилка на главной панели)
    "history_columns": ["Файл", "Путь", "Тип", "Ревизия", "Дата",
                        "Пользователь", "Компьютер", "Версия Creo", "Что изменено"],
}


















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

















def match_filter(row, cols, pattern):
    """Подходит ли строка под фильтр: КАЖДОЕ слово — в любом показанном столбце (без учёта регистра)."""
    words = [w for w in (pattern or "").lower().split() if w]
    if not words:
        return True
    blob = " ".join(str(row.get(c, "")) for c in cols).lower()
    return all(w in blob for w in words)


def _compose_par(par, rule):
    """Шаблон по словарю параметров: `{ИМЯ}` — значение, `"текст"` — литерал (кавычки не выводятся)."""
    out, i, n = [], 0, len(rule)
    while i < n:
        c = rule[i]
        if c == "{":
            j = rule.find("}", i)
            if j < 0:
                break
            v = first_param(par, [rule[i + 1:j].strip()])
            if v:
                out.append(str(v))
            i = j + 1
        elif c == '"':
            j = rule.find('"', i + 1)
            if j < 0:
                break
            out.append(rule[i + 1:j])
            i = j + 1
        elif c == "+":
            i += 1
        elif c.isspace():
            out.append(" ")                    # пробел в правиле = пробел в выводе
            i += 1
        else:
            j = i
            while j < n and rule[j] not in '{+"':
                j += 1
            out.append(rule[i:j])
            i = j
    return " ".join("".join(out).split())


def first_param(par, keys):
    """Первое непустое: имя параметра ИЛИ ШАБЛОН `{ИМЯ} "текст" +` (кавычки не выводятся)."""
    upper = {str(k).upper(): v for k, v in par.items()}
    for k in keys:
        k = (k or "").strip()
        if not k:
            continue
        if "{" in k or '"' in k:
            v = _compose_par(par, k)
            if v:
                return v
            continue
        v = par.get(k) or upper.get(k.upper())
        if v:
            return str(v)
    return ""


def scan_file(path, settings):
    raw = read_bytes(path, settings.get("max_size_mb", 0))
    if raw is None:
        return None
    sec = sections(raw)
    par = parameters(raw, sec)
    hist = history(raw)
    is_part = ".prt." in path.lower()
    role, parent = provenance(raw, is_part)
    vol = real_value(raw, "volume") or real_value(raw, "mtrl_volume")
    last = hist[-1] if hist else None
    return {
        "Файл": os.path.basename(path),
        "Тип": kind(raw),
        "Обозначение": first_param(par, settings.get("param_designation", DEFAULT_SETTINGS["param_designation"])),
        "Наименование": first_param(par, settings.get("param_name", DEFAULT_SETTINGS["param_name"])),
        "Материал": first_param(par, settings.get("param_material", DEFAULT_SETTINGS["param_material"])),
        "Объём, мм³": ("%.0f" % vol) if vol else "",
        "Габарит, мм": ", ".join("%.1f" % v for v in outline_mm(raw, sec)),
        "Роль": role,
        "Родитель": parent,
        "Ревизия": last[0] if last else "",
        "Дата": last[1].replace(tzinfo=datetime.timezone.utc).astimezone().strftime("%d.%m.%Y %H:%M")
                if last and last[1] else "",
        "Пользователь": last[2] if last else "",
        "Записей": len(hist),
        "Версия Creo": last[4] if last else "",
        "_path": path,
    }


VERSION_RE = re.compile(r"^(.*)\.([A-Za-z_]{2,4})\.(\d+)$", re.IGNORECASE)


def version_key(path):
    """Ключ изделия (папка, база, тип) и номер версии; None — если имя не похоже на модель."""
    m = VERSION_RE.match(os.path.basename(path))
    if not m:
        return None
    return (os.path.dirname(path).lower(), m.group(1).lower(), m.group(2).lower(),
            int(m.group(3)))


def pick_latest(paths, latest_only=True):
    """[(путь, всего_версий)]: при latest_only у изделия оставляем одну — старшую версию."""
    groups, plain = {}, []
    for p in paths:
        k = version_key(p)
        if not k:
            plain.append((p, 1))
            continue
        groups.setdefault(k[:3], []).append((k[3], p))
    out = []
    for lst in groups.values():
        lst.sort()
        if latest_only:
            out.append((lst[-1][1], len(lst)))
        else:
            for _, p in lst:
                out.append((p, len(lst)))
    out += plain
    return out


def scan_folder(folder, settings, progress=None, on_row=None, stop_cb=None, stats=None, walk_cb=None):
    rows, paths = [], []
    if settings.get("recurse", True):
        for dp, _, files in os.walk(folder):
            for f in files:
                if MODELFILE.search(f):
                    paths.append(os.path.join(dp, f))
                    if walk_cb and len(paths) % 200 == 0:
                        walk_cb(len(paths), False)
    else:
        for f in os.listdir(folder):
            if MODELFILE.search(f):
                paths.append(os.path.join(folder, f))
    if walk_cb:
        walk_cb(len(paths), True)             # обход закончен: всего найдено N моделей
    chosen = pick_latest(sorted(paths), settings.get("latest_only", True))
    cache = load_cache()                      # строки, прочитанные самим ридером (полные)
    known = db_rows_map(folder)               # ЕДИНАЯ БАЗА: что уже прочитано движком и не менялось
    fresh, read_n, from_cache = {}, 0, 0
    for n, (p, total) in enumerate(chosen, 1):
        if stop_cb and stop_cb():
            if stats is not None:
                stats["stopped"] = True
            break
        if progress:
            progress(n, len(chosen), p)
        try:
            st = os.stat(p)
        except OSError:
            continue
        old = cache.get(p)
        r = None
        if old and int(old.get("size", -1)) == st.st_size and abs(float(old.get("mtime", 0)) - st.st_mtime) < 1.0:
            r = old.get("row")                # НЕ изменился: берём из своего кэша (полная строка)
            from_cache += 1
        elif p in known and int(known[p][1] or 0) == st.st_size \
                and abs(float(known[p][2] or 0) - st.st_mtime) < 1.0:
            r = known[p][0]                   # НЕ изменился: берём из ЕДИНОЙ БАЗЫ — файл НЕ читаем
            from_cache += 1
        else:
            try:
                r = scan_file(p, settings)
            except Exception:
                r = None
            if r:
                fresh[p] = {"size": st.st_size, "mtime": st.st_mtime, "row": r}
            read_n += 1
        if r:
            r = dict(r)
            r["Версий"] = total
            rows.append(r)
            if on_row:
                on_row(r)
    if fresh:
        cache.update(fresh)
        save_cache(cache)
    if stats is not None:
        stats["read"] = read_n
        stats["cache"] = from_cache
        stats["rows"] = len(rows)
    return rows


def norm_path(s):
    """Привести вставленный путь к рабочему виду: убрать кавычки/пробелы по краям,
    заменить прямые слэши, отбросить хвостовой слэш; если вставлен файл — взять его папку."""
    s = (s or "").strip().strip('"').strip("'").strip("«»").strip()
    s = s.replace("/", "\\")
    while len(s) > 3 and s.endswith("\\"):
        s = s[:-1]
    if s and os.path.isfile(s):
        s = os.path.dirname(s)
    return s


def path_under(path, roots):
    """Путь внутри одного из корней (без учёта регистра, по границе папки).
    roots — путь ИЛИ список путей; безопасен к кривым строкам."""
    if isinstance(roots, str):
        roots = [roots]
    try:
        p = os.path.normcase(os.path.abspath(path))
    except Exception:
        return False
    for r in roots or []:
        try:
            rn = os.path.normcase(os.path.abspath(r)).rstrip("\\/")
        except Exception:
            continue
        if not rn:
            continue
        if p == rn or p.startswith(rn + "\\"):
            return True
    return False


def roots_of(folder, folder2=""):
    """Корни окна: основная папка + «Папка2» — только существующие, без дублей."""
    out = []
    for x in (folder, folder2):
        x = norm_path(x) if x else ""
        if x and x not in out:
            out.append(x)
    return out


def scan_roots(folder, folder2="", extra=None):
    """Корни СКАНА: поля окна («Папка1», «Папка2») + добавочные пути из настроек, без дублей."""
    out = roots_of(folder, folder2)
    for x in (extra or []):
        x = norm_path(x) if x else ""
        if x and x not in out:
            out.append(x)
    return out


def exclude_list(paths=None):
    """Папки-исключения в рабочем виде (нормализованные пути, без пустых)."""
    out = []
    for p in (paths or []):
        p = norm_path(str(p)) if str(p or "").strip() else ""
        if p and p not in out:
            out.append(p)
    return out

def apply_db_paths(settings, eng):
    """Применить настройки базы ДО первого обращения к ней: рабочая папка + пути зеркал.

    Возвращает (рабочая папка, список зеркал). Пустой db_dir = база рядом, в `db\\`."""
    db_dir = (settings.get("db_dir") or "").strip()
    mir = settings.get("db_mirror") or []
    if not isinstance(mir, list):
        mir = []
    mir = [norm_path(x) for x in mir if isinstance(x, str) and x.strip()]
    if db_dir:
        # рабочая папка уводится на другой диск: и база, и кэш, и бэкапы, и замок
        new_dir = os.path.abspath(db_dir)
        old_dir = globals().get("DATA_DIR")
        globals()["DATA_DIR"] = new_dir
        globals()["CACHE_FILE"] = os.path.join(new_dir, "scan_cache.json")
        globals()["DB_FILE"] = os.path.join(new_dir, "plm_reader.db")
        try:
            eng.set_base_dir(new_dir)
        except Exception as e:
            log_line("база: не удалось увести базу в %s (%s)" % (new_dir, e))
        # база на новом месте есть? если нет — переносим туда свежайшую (КОПИЯ, не перемещение)
        if old_dir and os.path.normcase(old_dir) != os.path.normcase(new_dir):
            try:
                have = [f for f in os.listdir(new_dir) if f.endswith(".db")] if os.path.isdir(new_dir) else []
                if not have:
                    import shutil as _sh
                    src = None
                    if os.path.isdir(old_dir):
                        ver = sorted(f for f in os.listdir(old_dir)
                                     if re.match(r"^plm_reader_\d{8}_\d{6}\.db$", f))
                        if ver:
                            src = os.path.join(old_dir, ver[-1])
                        elif os.path.isfile(os.path.join(old_dir, "plm_reader.db")):
                            src = os.path.join(old_dir, "plm_reader.db")
                    if src:
                        os.makedirs(new_dir, exist_ok=True)
                        _sh.copy2(src, os.path.join(new_dir, os.path.basename(src)))
                        log_line("база: перенесена копией на %s (%s)" % (new_dir, os.path.basename(src)))
                    else:
                        log_line("база: в %s пусто — наполнится после скана" % new_dir)
                else:
                    log_line("база: в %s уже есть файлы — оставляем как есть" % new_dir)
            except Exception as e:
                log_line("база: перенос на %s не удался (%s) — наполнится после скана" % (new_dir, e))
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception:
        pass
    return DATA_DIR, mir


class PathsWindow:
    """Окно «Пути и исключения…»: папки сканирования, папки-исключения и ГДЕ ЖИВЁТ БАЗА.

    «＋» добавляет строку, «−» удаляет; пустые строки и дубли отбрасываются при сохранении
    (поэтому запятые в именах папок ничему не мешают)."""

    def __init__(self, parent, settings, tk, ttk, filedialog, on_save=None):
        self.tk, self.ttk, self.filedialog = tk, ttk, filedialog
        self.settings = settings
        self.on_save = on_save
        self.win = tk.Toplevel(parent)
        self.win.title("Пути, исключения и база данных")
        self.win.geometry("860x720")
        self.win.transient(parent)
        self.rows = {"folders": [], "exclude": [], "template_folders": [], "db_mirror": []}
        box = ttk.Frame(self.win, padding=10)
        box.pack(fill="both", expand=True)
        ttk.Label(box, text="Папки сканирования (одна строка = один путь):",
                  font=("", 10, "bold")).pack(anchor="w")
        self.sec_scan = self._section(box, "folders")
        ttk.Label(box, text="ШАБЛОНЫ:", font=("", 10, "bold")).pack(anchor="w", pady=(14, 0))
        self.sec_tpl = self._section(box, "template_folders")
        ttk.Label(box, text="Папки исключений — НЕ читать вовсе (одна строка = один путь):",
                  font=("", 10, "bold")).pack(anchor="w", pady=(14, 0))
        self.sec_exc = self._section(box, "exclude")
        ttk.Label(box, text="ГДЕ ЖИВЁТ БАЗА", font=("", 10, "bold")).pack(anchor="w", pady=(14, 0))
        ttk.Label(box, text="Пусто = рядом с программой, в папке db\\. Можно указать другой диск:",
                  foreground="#555").pack(anchor="w")
        dline = ttk.Frame(box)
        dline.pack(fill="x", pady=(2, 0))
        self.e_db_dir = ttk.Entry(dline)
        self.e_db_dir.insert(0, settings.get("db_dir") or "")
        self.e_db_dir.pack(side="left", fill="x", expand=True)
        ttk.Button(dline, text="Выбрать…", width=10,
                   command=lambda: self._pick(self.e_db_dir)).pack(side="left", padx=4)
        ttk.Label(box, text="Зеркала базы (другая машина/диск): свежая база копируется туда. "
                            "Пусто = не дублировать:",
                  foreground="#555").pack(anchor="w", pady=(8, 0))
        self.sec_mir = self._section(box, "db_mirror")
        mrow = ttk.Frame(box)
        mrow.pack(fill="x", pady=(4, 0))
        ttk.Label(mrow, text="хранить свежих баз в зеркале:").pack(side="left")
        self.sp_mkeep = ttk.Spinbox(mrow, from_=1, to=50, width=4)
        self.sp_mkeep.set(str(settings.get("mirror_keep") or 3))
        self.sp_mkeep.pack(side="left", padx=(4, 14))
        self.var_mfull = tk.BooleanVar(value=bool(settings.get("mirror_full_only", True)))
        ttk.Checkbutton(mrow, text="зеркалить только после ПОЛНОГО скана",
                        variable=self.var_mfull).pack(side="left")
        self.mir_now = ttk.Button(box, text="Скопировать базу в зеркала ПРЯМО СЕЙЧАС",
                                  command=self.copy_now)
        self.mir_now.pack(anchor="w", pady=(6, 0))
        foot = ttk.Frame(box)
        foot.pack(fill="x", pady=(12, 0))
        ttk.Button(foot, text="Сохранить", command=self.save).pack(side="left")
        ttk.Button(foot, text="Закрыть", command=self.win.destroy).pack(side="left", padx=6)
        self.msg = ttk.Label(foot, text="", foreground="#555")
        self.msg.pack(side="left", padx=10)
        p_folders = settings.get("folders") or []
        for p in p_folders:
            self.add_row("folders", p)
        for p in (settings.get("exclude") or []):
            self.add_row("exclude", p)
        for p in (settings.get("template_folders") or []):
            self.add_row("template_folders", p)
        for p in (settings.get("db_mirror") or []):
            self.add_row("db_mirror", p)
        if not self.rows["folders"]:
            self.add_row("folders", "")
        if not self.rows["exclude"]:
            self.add_row("exclude", "")
        if not self.rows["template_folders"]:
            self.add_row("template_folders", "")
        if not self.rows["db_mirror"]:
            self.add_row("db_mirror", "")

    def _section(self, parent, key):
        fr = self.ttk.Frame(parent)
        fr.pack(fill="x", pady=(4, 0))
        self.ttk.Button(fr, text="＋ папка", width=12,
                        command=lambda: self.add_row(key, "")).pack(anchor="w", pady=(0, 2))
        holder = self.ttk.Frame(fr)
        holder.pack(fill="x")
        return holder

    def add_row(self, key, path):
        holder = {"folders": self.sec_scan, "exclude": self.sec_exc,
                  "template_folders": self.sec_tpl,
                  "db_mirror": self.sec_mir}.get(key, self.sec_scan)
        line = self.ttk.Frame(holder)
        line.pack(fill="x", pady=1)
        ent = self.ttk.Entry(line)
        ent.insert(0, path or "")
        ent.pack(side="left", fill="x", expand=True)
        self.ttk.Button(line, text="Выбрать…", width=10,
                        command=lambda e=ent: self._pick(e)).pack(side="left", padx=4)
        self.ttk.Button(line, text="−", width=3,
                        command=lambda l=line, k=key: self.del_row(k, l)).pack(side="left")
        self.rows[key].append((line, ent))

    def del_row(self, key, line):
        self.rows[key] = [(l, e) for (l, e) in self.rows[key] if l is not line]
        line.destroy()

    def _pick(self, ent):
        d = self.filedialog.askdirectory(initialdir=ent.get() or os.path.expanduser("~"))
        if d:
            ent.delete(0, "end")
            ent.insert(0, d.replace("/", "\\"))

    def collect(self):
        """Списки путей: пустые строки и дубли (без учёта регистра) отбрасываются."""
        out = {}
        for key in ("folders", "exclude", "template_folders", "db_mirror"):
            seen, vals = set(), []
            for _line, ent in self.rows[key]:
                v = norm_path(ent.get())
                if v and v.lower() not in seen:
                    seen.add(v.lower())
                    vals.append(v)
            out[key] = vals
        return out

    def copy_now(self):
        """Прогнать зеркалирование без скана: копия свежей базы — по кнопке."""
        import engine as _e
        self.save()                                  # сначала сохранить пути, что введены
        src = _e.active_db()
        if not os.path.isfile(src):
            self.msg.config(text="нечего копировать: базы ещё нет (нажми Сканировать)")
            return
        try:
            done = _e.mirror_published(src)
        except Exception as ex:
            self.msg.config(text="не удалось: %s" % ex)
            return
        if done:
            self.msg.config(text="скопировано в зеркал: %d (%s)" % (len(done), os.path.basename(src)))
        else:
            self.msg.config(text="зеркала не заданы или совпадают с рабочей папкой")

    def save(self):
        d = self.collect()
        old_dir = (self.settings.get("db_dir") or "").strip()
        self.settings["folders"] = d["folders"]
        self.settings["exclude"] = d["exclude"]
        self.settings["template_folders"] = d["template_folders"]
        self.settings["db_dir"] = norm_path(self.e_db_dir.get())
        self.settings["db_mirror"] = d["db_mirror"]
        try:
            self.settings["mirror_keep"] = max(1, min(50, int(self.sp_mkeep.get() or 3)))
        except Exception:
            self.settings["mirror_keep"] = 3
        self.settings["mirror_full_only"] = bool(self.var_mfull.get())
        save_settings_file(self.settings)
        try:
            import engine as _e
            _e.reset_service_cache()          # папки шаблонов изменились — сбросить кэш служебных
        except Exception:
            pass
        tail = ""
        new_dir = self.settings["db_dir"]
        if new_dir != old_dir:
            # папка базы поменялась — предупреждаем честно: подхватка только при перезапуске окна
            tail = " · база переедет на %s — ПЕРЕЗАПУСТИ окно" % (new_dir or "папку db\\")
        self.msg.config(text="сохранено: папок %d, исключений %d, шаблонов %d, зеркал %d%s"
                             % (len(d["folders"]), len(d["exclude"]), len(d["template_folders"]),
                                len(d["db_mirror"]), tail))
        if self.on_save:
            try:
                self.on_save()
            except Exception:
                pass


def _settings_migrations():
    """Цепочка миграций: {версия_назначения: функция(данные) -> данные}.
    Добавляй сюда шаг при КАЖДОМ структурном изменении (переименование/смена типа/смысла)."""
    def v1_to_v2(d):
        # v1: отдельные folder/folder2 -> v2: единый список folders
        if not d.get("folders"):
            legacy = []
            if d.get("folder"):
                legacy.append(d["folder"])
            if d.get("folder2") and d["folder2"] not in legacy:
                legacy.append(d["folder2"])
            if legacy:
                d["folders"] = legacy
        d.pop("folder", None)
        d.pop("folder2", None)
        return d
    def v2_to_v3(d):
        # v2 -> v3: путь рабочей папки базы (db_dir) и список зеркал (db_mirror).
        # Чужие/битые значения не роняют окно: приводим к строкам, мусор выбрасываем.
        d["db_dir"] = (d.get("db_dir") or "").strip() if isinstance(d.get("db_dir"), str) else ""
        raw = d.get("db_mirror")
        if isinstance(raw, str):
            raw = [x.strip() for x in raw.split(";")] if ";" in raw else [raw]
        if not isinstance(raw, list):
            raw = []
        out, seen = [], set()
        for p in raw:
            if isinstance(p, str) and p.strip():
                v = norm_path(p.strip())
                if v.lower() not in seen:
                    seen.add(v.lower())
                    out.append(v)
        d["db_mirror"] = out
        return d

    return {2: v1_to_v2, 3: v2_to_v3}


def _validate_settings(out):
    """Мягкая проверка типов: что не число — умолчание + строка в лог (битый файл не роняет окно)."""
    def _num(key, caster, fallback):
        try:
            out[key] = caster(out.get(key, fallback))
        except Exception:
            out[key] = fallback
            log_line("settings: ключ «%s» не число — беру умолчание" % key)
    _num("max_size_mb", float, 24)
    _num("show_limit", int, 50000)
    _num("depth", int, 0)
    _num("purge_keep", int, 2)
    return out


def _rotate_settings_backups(keep=5):
    """Оставить последние `keep` файлов в settings\\backup_settings; старые удалить."""
    try:
        bak_dir = os.path.join(SETTINGS_DIR, "backup_settings")
        if not os.path.isdir(bak_dir):
            return 0
        files = sorted(f for f in os.listdir(bak_dir) if f.endswith(".json"))
        removed = 0
        for old in files[:max(0, len(files) - keep)]:
            try:
                os.remove(os.path.join(bak_dir, old))
                removed += 1
            except Exception:
                pass
        return removed
    except Exception:
        return 0


def _archive_old_settings(src):
    """Старый файл настроек убираем в settings\\backup_settings\\ (не плодим файлы в корне)."""
    try:
        import shutil
        bak_dir = os.path.join(SETTINGS_DIR, "backup_settings")
        os.makedirs(bak_dir, exist_ok=True)
        where = "root" if os.path.dirname(os.path.abspath(src)) == os.path.dirname(os.path.abspath(__file__)) else "db"
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = os.path.join(bak_dir, "settings_from_%s_%s.json" % (where, stamp))
        shutil.move(src, dst)          # ПЕРЕНОС, а не копия
        _rotate_settings_backups()     # окно последних 5 (не копим бесконечно)
        log_line("settings: старый файл убран в %s" % dst)
        return dst
    except Exception as e:
        log_line("settings: не удалось убрать старый файл (%s): %s" % (src, e))
        return ""


def load_settings_file(path=None):
    r"""Настройки окна (файл в settings\). Битый файл не роняет окно — берём умолчания.
    Ищет по старшинству: settings\settings.json -> db\settings.json -> settings.json рядом;
    прогоняет цепочку миграций; старый файл убирает в settings\backup_settings\."""
    path = path or SETTINGS_FILE
    src, is_old = "", False
    candidates = [path]
    if path == SETTINGS_FILE:
        candidates.append(os.path.join(DATA_DIR, "settings.json"))
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json"))
    for c in candidates:
        if os.path.isfile(c):
            src = c
            is_old = (os.path.abspath(c) != os.path.abspath(SETTINGS_FILE))
            break
    out = dict(DEFAULT_SETTINGS)
    try:
        if src:
            with open(src, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                out.update(data)
    except Exception as e:
        log_line("settings: чтение не удалось (%s) — работаю на умолчаниях" % e)

    # Миграция структуры: от версии файла к текущей
    try:
        v = int(out.get("settings_version", 1))
    except Exception:
        v = 1
    migs = _settings_migrations()
    while v < CURRENT_SETTINGS_VERSION:
        v += 1
        if v in migs:
            out = migs[v](out)
            log_line("settings: миграция до версии %d (источник %s)" % (v, src or "умолчания"))
    out["settings_version"] = CURRENT_SETTINGS_VERSION
    out = _validate_settings(out)

    # Перенос из старого места: сохраняем в settings\
    if is_old and src:
        save_settings_file(out)
    # Подчистка: ЛЮБОЙ старый файл (кроме текущего settings\settings.json) уезжает в backup_settings\
    for c in candidates:
        if os.path.isfile(c) and os.path.abspath(c) != os.path.abspath(SETTINGS_FILE):
            _archive_old_settings(c)
    return out


def save_settings_file(settings, path=None):
    """Запись настроек: сначала во временный файл, потом замена (файл не бьётся при сбое).
    Ошибка пишется в лог, а не глотается молча."""
    path = path or SETTINGS_FILE
    tmp = path + ".tmp"
    try:
        out = dict(settings)
        out.pop("folder", None)      # единый источник — folders
        out.pop("folder2", None)
        out["settings_version"] = CURRENT_SETTINGS_VERSION
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        return True
    except Exception as e:
        log_line("settings: НЕ СОХРАНЕНО (%s): %s" % (path, e))
        try:
            if os.path.isfile(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return False




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


if __name__ == "__main__":
    main()

