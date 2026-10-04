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

# ПЕРЕВОД НА КАРКАС 04.10.2026: общий каркас окон дома лежит уровнем выше (tools\agent).
# Импорт делаем с sys.path, а не предполагая текущую папку: окно запускается и батом, и агентом.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import ui_common as U  # noqa: E402

APP_VERSION = "V38"
APP_TITLE = "PLM Reader " + APP_VERSION          # версия ОДНА: заголовок берёт её из константы
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db")          # данные — в подпапке db\
SETTINGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings")  # настройки — в подпапке settings\
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")                          # (не затираются при обновлении кода)
CACHE_FILE = os.path.join(DATA_DIR, "scan_cache.json")
CURRENT_SETTINGS_VERSION = 3   # увеличивать при КАЖДОМ структурном изменении настроек (см. _settings_migrations)


def load_cache():
    """Кэш прочитанных паспортов: путь -> {size, mtime, row}. Пустое/битое = {}."""
    try:
        if os.path.getsize(CACHE_FILE) > 500 * 1024 * 1024:
            return {}
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache):
    """Атомарная запись кэша (через .tmp + os.replace)."""
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        tmp = CACHE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
        os.replace(tmp, CACHE_FILE)
    except Exception:
        pass


DB_FILE = os.path.join(DATA_DIR, "plm_reader.db")


def _active_db_file():
    """Свежайшая опубликованная база plm_reader_ГГГГММДД_ЧЧММСС.db, иначе legacy plm_reader.db."""
    try:
        cand = sorted(f for f in os.listdir(DATA_DIR)
                      if re.match(r"^plm_reader_\d{8}_\d{6}\.db$", f))
        if cand:
            return os.path.join(DATA_DIR, cand[-1])
    except Exception:
        pass
    return DB_FILE


def db_conn(ro=True):
    """Соединение с базой для ПРОСМОТРА: только чтение (PRAGMA query_only), ничего не пишет."""
    import sqlite3
    path = _active_db_file()
    if ro and not os.path.isfile(path):
        raise FileNotFoundError(path)          # не создаём пустую базу при просмотре
    c = sqlite3.connect(path, timeout=15)
    if ro:
        try:
            c.execute("PRAGMA query_only=ON")
        except Exception:
            pass
    return c


def db_summary():
    """Сколько чего в базе: файлов, моделей, связей, папок, изменений."""
    try:
        c = db_conn()
        q = lambda s: c.execute(s).fetchone()[0]            # noqa: E731
        out = {"files": q("SELECT COUNT(*) FROM snapshots"),
               "models": q("SELECT COUNT(DISTINCT model) FROM snapshots"),
               "links": q("SELECT COUNT(*) FROM links"),
               "folders": q("SELECT COUNT(*) FROM folders"),
               "changes": q("SELECT COUNT(*) FROM changes")}
        c.close()
        return out
    except Exception:
        return {}


def db_total(folder=None):
    """Сколько строк паспортов (folder — путь ИЛИ список путей: основная + «Папка2»)."""
    roots = [f for f in ([folder] if isinstance(folder, str) else list(folder or [])) if f]
    try:
        c = db_conn()
        if roots:
            n = c.execute("SELECT COUNT(*) FROM snapshots WHERE "
                          + " OR ".join(["folder LIKE ?"] * len(roots)),
                          tuple(r.rstrip("\\") + "%" for r in roots)).fetchone()[0]
            if not n:                        # регистр/слэши не совпали — считаем в питоне
                n = sum(1 for (p,) in c.execute("SELECT path FROM snapshots")
                        if path_under(p, roots))
        else:
            n = c.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
        c.close()
        return n
    except Exception:
        return 0


def _ver(p):
    try:
        return int(p.rsplit(".", 1)[1])
    except Exception:
        return 0


_WINS = {}                    # открытые окна историй: одно окно на название


def _fs_date(ts):
    """Время файла (epoch) -> 'дд.мм.гггг чч:мм' (или пусто)."""
    try:
        return datetime.datetime.fromtimestamp(float(ts)).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return ""


def db_rows_map(folder=None, latest_only=False):
    """Единая база: путь -> (size, mtime, строка). Подсчёт версий и, если надо, только последняя.
    `folder` — путь ИЛИ СПИСОК путей (основная + «Папка2»); фильтр без учёта регистра."""
    roots = [f for f in ([folder] if isinstance(folder, str) else list(folder or [])) if f]
    try:
        c = db_conn()
        has = any(r[1] == "created" for r in c.execute("PRAGMA table_info(snapshots)"))
        sql = ("SELECT path,model,size,mtime,volume,material,name,designation,rev,author,revdate,"
               "role,hist,creo%s FROM snapshots %%s" % (",created" if has else ""))
        if roots:
            cur = c.execute(sql % ("WHERE " + " OR ".join(["folder LIKE ?"] * len(roots))),
                            tuple(r.rstrip("\\") + "%" for r in roots))
            data = [tuple(r) + ((None,) if not has else ()) for r in cur]
            if not data:                    # регистр/слэши не совпали — фильтруем в питоне
                data = [tuple(r) + ((None,) if not has else ()) for r in c.execute(sql % "")]
                data = [d for d in data if path_under(d[0], roots)]
        else:
            data = [tuple(r) + ((None,) if not has else ()) for r in c.execute(sql % "")]
        c.close()
    except Exception:
        return {}
    vers = {}
    for d in data:
        vers[d[1]] = vers.get(d[1], 0) + 1
    out, best = {}, {}
    for (p, model, size, mtime, volume, material, name, desig, rev, author, revdate,
         role, hist, creo, created) in data:
        v = _ver(p)
        if latest_only:
            if model in best and v < best[model]:
                continue
            best[model] = v
        out[p] = (size, mtime, {
            "Файл": os.path.basename(p), "Тип": "", "Обозначение": desig or "",
            "Наименование": name or "", "Материал": material or "",
            "Объём, мм³": ("%.0f" % volume) if volume else "", "Габарит, мм": "",
            "Роль": role or "", "Родитель": "", "Ревизия": rev or "",
            "Дата": revdate or "", "Пользователь": author or "",
            "Создан": _fs_date(created), "_created_ts": float(created or 0),
            "Изменён": _fs_date(mtime), "_mtime_ts": float(mtime or 0),
            "Записей": str(hist or ""), "Версий": vers.get(model, 0),
            "Версия Creo": creo or "", "_path": p,
        })
    return out


def db_rows(folder=None, limit=2000, latest_only=False):
    """Строки паспортов ИЗ БАЗЫ (файлы не читаются).
    `folder` — путь ИЛИ СПИСОК путей (основная + «Папка2»)."""
    roots = [f for f in ([folder] if isinstance(folder, str) else list(folder or [])) if f]
    try:
        c = db_conn()
        has = any(r[1] == "created" for r in c.execute("PRAGMA table_info(snapshots)"))
        sql = ("SELECT path,model,volume,material,name,designation,rev,author,revdate,role,hist,creo,"
               "mtime%s FROM snapshots %%s ORDER BY model, path LIMIT ?" % (",created" if has else ""))
        if roots:
            cond = "WHERE " + " OR ".join(["folder LIKE ?"] * len(roots))
            args = tuple(r.rstrip("\\") + "%" for r in roots)
            data = [tuple(r) + ((None,) if not has else ())
                    for r in c.execute(sql % cond, args + (limit,))]
            vers = dict(c.execute("SELECT model, COUNT(*) FROM snapshots " + cond +
                                  " GROUP BY model", args))
            if not data:                  # регистр/слэши не совпали — фильтруем в питоне
                allr = [tuple(r) + ((None,) if not has else ())
                        for r in c.execute(sql % "", (10 ** 9,))]
                data = [d for d in allr if path_under(d[0], roots)][:limit]
                vers = dict(c.execute("SELECT model, COUNT(*) FROM snapshots GROUP BY model"))
        else:
            data = [tuple(r) + ((None,) if not has else ())
                    for r in c.execute(sql % "", (limit,))]
            vers = dict(c.execute("SELECT model, COUNT(*) FROM snapshots GROUP BY model"))
        rows = []
        for (p, model, volume, material, name, desig, rev, author, revdate, role, hist, creo,
             mtime, created) in data:
            rows.append({
                "Файл": os.path.basename(p), "Тип": "", "Обозначение": desig or "",
                "Наименование": name or "", "Материал": material or "",
                "Объём, мм³": ("%.0f" % volume) if volume else "", "Габарит, мм": "",
                "Роль": role or "", "Родитель": "", "Ревизия": rev or "",
                "Дата": revdate or "", "Пользователь": author or "",
                "Создан": _fs_date(created), "_created_ts": float(created or 0),
                "Изменён": _fs_date(mtime), "_mtime_ts": float(mtime or 0),
                "Записей": str(hist or ""), "Версий": vers.get(model, 0), "Версия Creo": creo or "", "_path": p,
            })
        c.close()
        return rows
    except Exception:
        return []


def db_search_rows(words=None, limit=5000):
    """ПОИСК ПО ВСЕЙ БАЗЕ (а не по загруженной странице): наименование/обозначение/материал/путь/ревизия/роль.
    Сначала «ВСЕ слова» (И); если так пусто — «ЛЮБОЕ слово» (ИЛИ) и это видно в строке состояния.
    Возвращает (строки, найдено_всего, режим)."""
    ws = [w.casefold() for w in (words or []) if w]
    try:
        c = db_conn()
        has = any(r[1] == "created" for r in c.execute("PRAGMA table_info(snapshots)"))
        sql = ("SELECT path,model,volume,material,name,designation,rev,author,revdate,role,hist,creo,"
               "mtime%s FROM snapshots" % (",created" if has else ""))
        data = [tuple(r) + ((None,) if not has else ()) for r in c.execute(sql)]
        vers = dict(c.execute("SELECT model, COUNT(*) FROM snapshots GROUP BY model"))
        c.close()
    except Exception:
        return [], 0, ""
    cache = {}

    def blob(d):
        b = cache.get(d[0])
        if b is None:
            b = " ".join(str(x or "") for x in (d[3], d[4], d[5], d[6], d[7], d[8], d[0])).casefold()
            cache[d[0]] = b
        return b

    mode = "И"
    hits = [d for d in data if all(w in blob(d) for w in ws)] if ws else list(data)
    if ws and not hits:
        hits = [d for d in data if any(w in blob(d) for w in ws)]
        mode = "ИЛИ"
    out = []
    for (p, model, volume, material, name, desig, rev, author, revdate, role, hist, creo,
         mtime, created) in hits[:limit]:
        out.append({
            "Файл": os.path.basename(p), "Тип": "", "Обозначение": desig or "",
            "Наименование": name or "", "Материал": material or "",
            "Объём, мм³": ("%.0f" % volume) if volume else "", "Габарит, мм": "",
            "Роль": role or "", "Родитель": "", "Ревизия": rev or "",
            "Дата": revdate or "", "Пользователь": author or "",
            "Создан": _fs_date(created), "_created_ts": float(created or 0),
            "Изменён": _fs_date(mtime), "_mtime_ts": float(mtime or 0),
            "Записей": str(hist or ""), "Версий": vers.get(model, 0),
            "Версия Creo": creo or "", "_path": p,
        })
    return out, len(hits), mode
# Логи: дома — в общий D:\AI\log, на чужой машине — рядом с инструментом (переносимость)
LOG_DIR = os.environ.get("PLM_LOG") or (
    r"D:\AI\log\plm_reader" if os.path.isdir(r"D:\AI\log")
    else os.path.join(os.path.dirname(os.path.abspath(__file__)), "log"))
REPORTS_DIR = os.path.join(os.path.dirname(LOG_DIR), "reports")


def log_line(text):
    """Одна строка в общий лог инструмента: D:\\AI\\log\\plm_reader\\plm_reader.log."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "plm_reader.log"), "a", encoding="utf-8") as f:
            f.write("%s  %s\n" % (datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"), text))
    except Exception:
        pass

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
    "show_limit": 50000,    # сколько строк показывать за раз (крутилка на главной панели)
    "history_columns": ["Файл", "Путь", "Тип", "Ревизия", "Дата",
                        "Пользователь", "Компьютер", "Версия Creo", "Что изменено"],
}

MODELFILE = re.compile(r"\.([a-z_]{2,4})\.\d+$", re.IGNORECASE)


def read_bytes(path, limit_mb):
    if limit_mb and os.path.getsize(path) > limit_mb * 1_000_000:
        return None
    with open(path, "rb") as f:
        return f.read()


def sections(raw):
    """Внутреннее оглавление файла: {имя: (offset, length)}."""
    out, pos = {}, raw.find(b"#UGC_TOC")
    for _ in range(20):
        if pos < 0:
            break
        p = raw.find(b"\n", pos)
        nxt = -1
        while True:
            e = raw.find(b"\n", p + 1)
            if e < 0:
                break
            line = raw[p + 1:e].decode("ascii", "replace").strip()
            p = e
            if line.startswith("NEXT_TOC_ENTRY"):
                nxt = int(line.split()[1], 16)
                break
            m = re.match(r"^([A-Za-z_][A-Za-z0-9_:]{1,40}) ([0-9a-f]{2,8}) ([0-9a-f]{2,8})"
                         r"(?: ([0-9a-f]{2,8}))?(.*)$", line)
            if m and (not m.group(5).strip() or m.group(5).strip()[0] in "0123456789-"):
                ln = int(m.group(4), 16) if m.group(4) else int(m.group(3), 16)
                out[m.group(1)] = (int(m.group(2), 16), max(ln, 1))
        if nxt < 0 or nxt >= len(raw):
            break
        pos = nxt
    return out


def real_value(raw, key):
    """Числовое поле изделия (объём, масса …). None, если не найдено."""
    m = re.search(rb"\xe0\x02" + re.escape(key.encode()) + rb"\x00\xed", raw)
    if not m or m.end() + 8 > len(raw):
        return None
    try:
        return struct.unpack(">d", raw[m.end():m.end() + 8])[0]
    except Exception:
        return None


def packed_at(raw, i):
    """Компактное число: (длина, значение) или None."""
    if i >= len(raw):
        return None
    b0 = raw[i]
    if b0 == 0x2D and i + 7 < len(raw):
        frac = raw[i + 3:i + 8]
        if all(0x20 <= x < 0x7F for x in frac):
            return None
        b1, b2 = raw[i + 1], raw[i + 2]
        E, F = b1 >> 4, ((b1 & 0x0F) << 8) | b2
        if E > 15:
            return None
        base = (2 ** (E + 1)) * (1 + F / 4096.0)
        step = (2 ** (E + 1)) / 4096.0
        return 8, base + (int.from_bytes(frac, "big") / float(1 << 40)) * step
    if b0 in (0x2F, 0x48) and i + 2 < len(raw):
        b1, b2 = raw[i + 1], raw[i + 2]
        E, F = b1 >> 4, ((b1 & 0x0F) << 8) | b2
        v = (2 ** (E + 1)) * (1 + F / 4096.0)
        return 3, (-v if b0 == 0x48 else v)
    if b0 == 0x2A and i + 2 < len(raw):
        b1, b2 = raw[i + 1], raw[i + 2]
        E, F = b1 >> 4, ((b1 & 0x0F) << 8) | b2
        return 3, (2 ** (E - 15)) * (1 + F / 4096.0)
    return None


def clean_name(s):
    return re.sub(r"[\x00-\x1f]+", " ", s).strip()



def parameters(raw, sec):
    """Параметры изделия: {имя: значение} (обозначение, наименование, материал …)."""
    out = {}
    for name in ("NeuPrtSld", "LargeText"):
        if name not in sec:
            continue
        off, ln = sec[name]
        chunk = raw[off:off + ln]
        for m in re.finditer(rb"([\x20-\xff]{3,32})\x00\xe2([\x32\x33])(.{0,60}?)\x00", chunk, re.S):
            t = re.search(r"[\w]+$", m.group(1).decode("utf-8", "replace"))
            if not t:
                continue
            key = t.group(0)
            if m.group(2)[0] == 0x33:
                try:
                    val = clean_name(m.group(3).decode("utf-8"))
                except UnicodeDecodeError:
                    continue
                if val:
                    out.setdefault(key, val)
            else:
                r = packed_at(m.group(3), 0) if m.group(3) else None
                if r:
                    out.setdefault(key, r[1])
    return out


def outline_mm(raw, sec):
    """Габарит изделия, мм."""
    for name in ("FullMData", "BasicText"):
        if name not in sec:
            continue
        off, ln = sec[name]
        chunk = raw[off:off + ln]
        m = re.search(rb"outline\x00", chunk)
        if not m:
            continue
        seg = chunk[m.end():m.end() + 12]
        vals = []
        for k in (4, 8):
            try:
                vals.append(abs(struct.unpack_from("<f", seg, k)[0]) / 1000.0)
            except Exception:
                pass
        vals = [v for v in vals if 0.001 <= v <= 100000.0]   # отсеять мусорные значения
        if vals:
            return vals
    return []


# --- 04.10.2026: связь чертёж → модель (`model_names\0 \xf8 <байт> <ИМЯ>\0`) -------------
# ГРАБЛИ, учтённые здесь (проверены на байтах, давали 0 % / 49 % разбора):
#   1) поле — `model_names` (с S), не `model_name`;
#   2) кириллица в UTF-8 = D0 9A, а 0x9A не входит в [\x20-\x7e] → нужен \x80-\xff;
#   3) байт после \xf8 не всегда 0x01 (бывают 0x08, 0x09, 0x0B).
DRW_MODEL_RE = re.compile(rb"model_names\x00\xf8[\x01-\x0f]([\x20-\x7e\x80-\xff]{3,160}?)\x00",
                          re.S)
MDL_NAME_RE = re.compile(r"^[A-Za-z0-9А-Яа-яЁё_\-.? ]{4,80}\.(?:prt|asm|PRT|ASM)$")


def dwg_models(raw):
    """Из чёртежа (.drw): модели (детали/сборки), которые он показывает.

    Возвращает список имён файлов, напр. ['A887-94-1500-01.PRT'].
    В 75 % имён часть символов нечитаема ('?') — это потеря данных в самом файле Creo,
    последний компонент пути берётся как есть."""
    out = []
    if not raw or b"model_names" not in raw:
        return out
    for m in DRW_MODEL_RE.finditer(raw):
        try:
            nm = m.group(1).decode("utf-8")
        except UnicodeDecodeError:
            continue
        nm = nm.replace("/", "\\").split("\\")[-1]
        nm = " ".join(nm.split()).strip()
        if len(nm) < 4 or nm.endswith("?") or not MDL_NAME_RE.match(nm):
            continue
        if nm not in out:
            out.append(nm)
        if len(out) >= 8:
            break
    return out


# --- 04.10.2026: техтребования и ЧИСЛОВЫЕ параметры из тела файла --------------------
# Штатный parameters() даёт 3 параметра там, где из файла читается 9: он ищет только
# в секциях NeuPrtSld/LargeText и по другому шаблону. Ниже — проверенный разбор.
TEXT_VALUE_RE = re.compile(rb"text_value\x00([^\x00]{2,600}?)\x00", re.S)
PARAM_NUM_RE = re.compile(rb"\xe3([\x20-\x7e\xc0-\xff]{2,48}?)\x00\xe2\x32", re.S)
# служебные имена в техтребованиях: DTM1, A_1, RIGHT, ASM_DEF_CSYS …
_NOTES_JUNK = re.compile(r"^(DTM\d*|A_?\d+|D\d+|PRT|ASM|MFG)\b|"
                         r"^(RIGHT|LEFT|TOP|BOTTOM|FRONT|BACK|DEFAULT|USER_DEF|"
                         r"DEF_CSYS|CSYS|HOLDER|TIP|SHEET)\b", re.IGNORECASE)


def tech_notes(raw, limit=8):
    """Технические требования из секции Notes (`text_value\\0<текст>\\0`).

    Отсекаются служебные подписи (`RIGHT`, `PRT_CSYS_DEF`, `DTM1`, `\\поле\\`)
    — без этого в вывод идёт больше мусора, чем текста."""
    out = []
    if not raw or b"text_value" not in raw:
        return out
    for m in TEXT_VALUE_RE.finditer(raw):
        try:
            s = " ".join(m.group(1).decode("utf-8").split())
        except UnicodeDecodeError:
            continue                      # нечитаемый хвост — пропускаем
        if not (2 < len(s) < 500):
            continue
        if s.startswith("\\") or s.endswith("\\"):
            continue
        if _NOTES_JUNK.match(s):
            continue
        if not any(ch.isdigit() for ch in s):
            continue                      # слово без цифр — служебное имя вида
        if s not in out:
            out.append(s)
        if len(out) >= limit:
            break
    return out


def _dec_num(t):
    """Число после метки e2 32: 1 байт / 3 байта / 8 байт. None — не угадываем."""
    if not t:
        return None
    if t[0] == 0xF7:                     # служебный префикс
        t = t[1:]
        if not t:
            return None
    v = {0x18: 0.0, 0x07: 0.001, 0x0D: 0.25, 0x0E: 0.5, 0x0F: 1.0}.get(t[0])
    if v is not None:
        return v
    if len(t) >= 3 and t[0] in (0x2F, 0x48):
        # ⚠️ знак байта 0x2F на живых файлах означает «плюс» (THREAD_DIAMETER=+12 при М12),
        # поэтому знак выбираем по «круглости»: без минуса целое или кратное 0.5 → берём плюс
        E, F = (t[1] >> 4) & 0x0F, ((t[1] & 0x0F) << 8) | (t[2] & 0xFF)
        mag = (2.0 ** (E + 1)) * (1.0 + F / 4096.0)
        if abs(mag - round(mag)) < 1e-9 or abs(mag * 2 - round(mag * 2)) < 1e-9:
            return mag
        return -mag if t[0] == 0x2F else mag
    if len(t) >= 8 and t[0] == 0x2D:
        sign = -1 if t[1] & 0x80 else 1
        E, F = (t[1] >> 4) & 0x0F, t[1] & 0x0F
        frac = int.from_bytes(t[2:7], "big")
        return sign * (2.0 ** (E + 1)) * (1.0 + (F + frac / 2.0 ** 40) / 4096.0)
    if t[0] == 0xED and len(t) >= 9:      # прямой double за маркером
        try:
            v = struct.unpack(">d", t[1:9])[0]
            return v if 1e-9 < abs(v) < 1e9 else None
        except Exception:
            return None
    return None


def numeric_params(raw, limit=60):
    """Числовые параметры детали: {имя: число}.

    Имя = `\\xe3<ИМЯ>\\0\\xe2\\x32`, значение — за ним. Значения за служебными байтами
    не угадываются (лучше пусто, чем мусор в выводе)."""
    out = {}
    if not raw or b"\xe2\x32" not in raw:
        return out
    for m in PARAM_NUM_RE.finditer(raw):
        try:
            nm = m.group(1).decode("utf-8").strip()
        except UnicodeDecodeError:
            continue
        if not nm or not all(ch.isprintable() for ch in nm):
            continue
        v = _dec_num(raw[m.end():m.end() + 20])
        if v is not None and abs(v) < 1e7:
            out.setdefault(nm, round(v, 6))
        if len(out) >= limit:
            break
    return out


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


def history(raw):
    """Записи истории: (ревизия, дата, пользователь, компьютер, версия)."""
    stamps = []
    for m in re.finditer(rb"\xf7\x14([\x20-\x7e\xc0-\xff]{1,24}?)\x00\xe2(.)(.)(.)(.)(.)(.)", raw, re.S):
        s, mi, h, d, mo, y = (b[0] for b in m.groups()[1:])
        try:
            dt = datetime.datetime(1900 + y, mo + 1, d, h, mi, s)
        except ValueError:
            continue
        stamps.append((m.start(), m.group(1).decode("utf-8", "replace"), dt))
    for m in re.finditer(rb"([A-Za-z0-9_.\-]{2,24})\x00\xe2(.)(.)(.)(.)(.)(.)", raw, re.S):
        s, mi, h, d, mo, y = (b[0] for b in m.groups()[1:])
        try:
            dt = datetime.datetime(1900 + y, mo + 1, d, h, mi, s)
        except ValueError:
            continue
        stamps.append((m.start(), m.group(1).decode("ascii", "replace"), dt))
    stamps.sort()
    out = []
    for t in re.finditer(rb"\xf7(.)\xe3([0-9]{1,7})\x00\x00(.{0,220}?)\x00((?:Creo )?[0-9][0-9.]*)\x00", raw, re.S):
        prev = [s for s in stamps if s[0] < t.start()]
        user = prev[-1][1] if prev else ""
        dt = prev[-1][2] if prev else None
        try:
            com = t.group(3).decode("utf-8")
        except UnicodeDecodeError:
            com = t.group(3).decode("cp1251", "replace")
        out.append((t.group(2).decode(), dt, user, clean_name(com), t.group(4).decode()))
    return out


def parent_file(nm, is_part):
    """Имя файла родителя (с расширением): base -> base.prt / base.asm."""
    nm = (nm or "").strip()
    if not nm:
        return ""
    if nm.lower().endswith((".prt", ".asm", ".drw")):
        return nm
    return nm + (".prt" if is_part else ".asm")


def provenance(raw, is_part):
    """Роль изделия и родитель (заготовка / отражение / наследование)."""
    if b"MERGE_BASE_PART" in raw:
        m = re.search(rb"MERGE_BASE_PART.{0,80}?([A-Za-z0-9_\-]{5,40})\x00", raw, re.S)
        return "наследование", parent_file(m.group(1).decode("latin-1") if m else "", True)
    if is_part:
        for m in re.finditer(rb"ref_part_tab\x00", raw):
            nm = re.search(rb"name\x00([A-Za-z0-9_\-\.]{4,47})\x00", raw[m.end():m.end() + 200])
            if nm:
                return "производная", parent_file(nm.group(1).decode("latin-1"), True)
    return "", ""


COLS_WIDTH = {"Обозначение": 130, "Наименование": 210, "Материал": 110, "Объём, мм³": 100,
              "Роль": 110, "Родитель": 140, "Ревизия": 80, "Записей": 80, "Версий": 70, "Дата": 120,
              "Создан": 125, "Изменён": 125, "Пользователь": 100, "Версия Creo": 110, "Файл": 215}


def clean_computer(text):
    """Имя компьютера из служебной строки записи.
    Пример: "Наименование компьютера: 'frezer-4'" -> "frezer-4"."""
    m = re.search(r"'([^']+)'", text or "")
    if m:
        return m.group(1).strip()
    return (text or "").strip().split(":")[-1].strip().strip("'")


def parse_changes(raw):
    """ЧТО МЕНЯЛОСЬ в модели (из внутренних записей изменения Creo).

    Возвращает {ревизия: {"dims": [...], "params": [...]}}: изменение привязано к ближайшей
    предшествующей записи истории (маркер `f7 ?? e3 <rev> 00 00`).
    Размеры — `typed_data(MTTyped_ModifyData)` -> имена `d*`; параметры — `chg_param_arr`/`param_typed_data`.
    ВАЖНО: числовые «было→стало» по размеру Creo в записи НЕ хранит (old_val/new_val пусты) —
    видно ИМЯ изменённого размера, а не значения.
    """
    marks = [(m.start(), m.group(2).decode()) for m in
             re.finditer(rb"\xf7(.)\xe3([0-9]{1,7})\x00\x00", raw)]

    def rev_at(off):
        prev = [r for r in marks if r[0] < off]
        return prev[-1][1] if prev else ""

    out = {}

    def add(rev, key, val):
        if not val:
            return
        d = out.setdefault(rev, {"dims": [], "params": []})
        if val not in d[key]:
            d[key].append(val)

    for m in re.finditer(rb"MTTyped_ModifyData", raw):
        seg = raw[m.start():m.start() + 600]
        for d in re.findall(rb"(?<![A-Za-z0-9_])(d[0-9]{1,6})(?![A-Za-z0-9_])", seg):
            add(rev_at(m.start()), "dims", d.decode("latin-1"))
    for m in re.finditer(rb"chg_param_arr", raw):
        seg = raw[m.start():m.start() + 400]
        n = re.search(rb"name\x00([^\x00]{1,40})\x00", seg)
        if n:
            add(rev_at(m.start()), "params", n.group(1).decode("utf-8", "replace"))
    for m in re.finditer(rb"param_typed_data", raw):
        seg = raw[m.start() + 16:m.start() + 160]
        t = re.search(rb"((?:\xd0[\x80-\xbf]|\xd1[\x80-\xbf])[^\x00]{1,40})\x00", seg)
        if t:
            try:
                add(rev_at(m.start()), "params", t.group(1).decode("utf-8"))
            except UnicodeDecodeError:
                pass
    return out


def changes_line(chg):
    """Короткая строка «что изменено» из словаря изменений одной записи."""
    if not chg:
        return ""
    parts = []
    if chg.get("dims"):
        parts.append("размеры: " + ", ".join(chg["dims"]))
    if chg.get("params"):
        parts.append("параметры: " + ", ".join(chg["params"]))
    return "; ".join(parts)


def sibling_versions(path):
    """Все версии того же изделия в папке: [(номер, путь), ...] по возрастанию."""
    folder = os.path.dirname(path)
    m = re.match(r"^(.*)\.([A-Za-z_]{2,4})\.(\d+)$", os.path.basename(path))
    if not m:
        return []
    stem, ext = m.group(1).lower(), m.group(2).lower()
    out = []
    try:
        for n in os.listdir(folder):
            mm = re.match(r"^(.*)\.([A-Za-z_]{2,4})\.(\d+)$", n)
            if mm and mm.group(1).lower() == stem and mm.group(2).lower() == ext:
                out.append((int(mm.group(3)), os.path.join(folder, n)))
    except OSError:
        return []
    out.sort()
    return out


def version_change(path, settings):
    """Коротко: что изменилось в ЭТОЙ версии относительно предыдущей (по читаемым полям)."""
    vers = sibling_versions(path)
    if len(vers) < 2:
        return ""
    idx = [i for i, (n, p) in enumerate(vers) if os.path.normcase(p) == os.path.normcase(path)]
    if not idx or idx[0] == 0:
        return ""
    cur = scan_file(path, settings) or {}
    prev = scan_file(vers[idx[0] - 1][1], settings) or {}
    parts = []
    if prev.get("Ревизия") != cur.get("Ревизия"):
        parts.append("ревизия %s→%s" % (prev.get("Ревизия"), cur.get("Ревизия")))
    for f in ("Объём, мм³", "Габарит, мм"):
        a, b = str(prev.get(f, "")), str(cur.get(f, ""))
        if a and b and a != b:
            parts.append("%s %s→%s" % (f.split(",")[0], a, b))
    return "; ".join(parts)


VERSION_FIELDS = ("Ревизия", "Дата", "Пользователь", "Версия Creo", "Объём, мм³", "Габарит, мм")
VER_COLUMNS = ("Версия", "Ревизия", "Дата", "Пользователь", "Версия Creo", "Объём, мм³",
               "Габарит, мм", "Изменение")


def version_diff(path, settings):
    """Было→стало между версиями одного изделия (.1 .2 .3 …).

    Числа (объём, габарит) сравниваются, когда оба значения правдоподобны; ревизия — всегда.
    Плюс к каждой версии — что менялось по её внутренним записям (размеры/параметры).
    """
    vers = sibling_versions(path)
    if len(vers) < 2:
        return []
    parsed = []
    for num, p in vers:
        raw = read_bytes(p, settings.get("max_size_mb", 0))
        if raw is None:
            parsed.append((num, {}, {}))
            continue
        try:
            r = scan_file(p, settings)
        except Exception:
            r = {}
        parsed.append((num, r, parse_changes(raw)))
    rows = []
    for i, (num, r, chg) in enumerate(parsed):
        d = {f: (r.get(f, "") if r else "") for f in VERSION_FIELDS}
        d["Версия"] = str(num)
        changes = []
        if i:
            pr = parsed[i - 1][1]
            if pr and r:
                if pr.get("Ревизия") != r.get("Ревизия"):
                    changes.append("ревизия %s→%s" % (pr.get("Ревизия"), r.get("Ревизия")))
                for f in ("Объём, мм³", "Габарит, мм"):
                    a, b = str(pr.get(f, "")), str(r.get(f, ""))
                    if a and b and a != b:
                        changes.append("%s %s→%s" % (f.split(",")[0], a, b))
            else:
                changes.append("нет данных предыдущей версии")
        for rev, c in sorted(chg.items()):
            line = changes_line(c)
            if line:
                changes.append("rev %s: %s" % (rev, line))
        d["Изменение"] = "; ".join(changes)
        rows.append(d)
    return rows


def versions_window(parent, tk, ttk, filedialog, title, rows):
    """Окно сравнения версий одного изделия (.1 .2 .3 …)."""
    win = tk.Toplevel(parent)
    win.title(title)
    win.geometry("1100x440")
    W = {"Версия": 70, "Ревизия": 70, "Дата": 145, "Пользователь": 100, "Версия Creo": 100,
         "Объём, мм³": 100, "Габарит, мм": 130, "Изменение": 340}
    tv = ttk.Treeview(win, columns=VER_COLUMNS, show="headings")
    for c in VER_COLUMNS:
        tv.heading(c, text=c)
        tv.column(c, width=W.get(c, 120), anchor="w")
    tv.pack(fill="both", expand=True, padx=6, pady=6)

    def exp():
        p = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="versions.csv",
                                         filetypes=[("CSV", "*.csv")])
        if p:
            save_csv(rows, p)

    ttk.Button(win, text="Выгрузить в CSV", command=exp).pack(anchor="w", padx=6, pady=(0, 6))
    for r in rows:
        tv.insert("", "end", values=[r.get(c, "") for c in VER_COLUMNS])
    return win


def history_rows(path, settings):
    """Полная история файла: список записей (ревизия, дата, кто, компьютер, версия, что изменено)."""
    raw = read_bytes(path, settings.get("max_size_mb", 0))
    if raw is None:
        return []
    chg = parse_changes(raw)
    typ = kind(raw)
    base = os.path.basename(path)
    folder = os.path.dirname(path)
    out = []
    for rev, dt, who, comp, ver in history(raw):
        d = dt.replace(tzinfo=datetime.timezone.utc).astimezone() if dt else None
        out.append({"Файл": base, "Путь": folder, "Тип": typ,
                    "Ревизия": rev, "Дата": d.strftime("%d.%m.%Y %H:%M:%S") if d else "",
                    "Пользователь": who, "Компьютер": clean_computer(comp), "Версия Creo": ver,
                    "Что изменено": changes_line(chg.get(rev)),
                    "_dt": d.isoformat() if d else ""})
    if out:
        vc = version_change(path, settings)
        if vc:
            base = out[-1].get("Что изменено", "")
            out[-1]["Что изменено"] = (base + "; " + vc) if base else vc
    return out


def history_folder(folder, settings, progress=None):
    """Сводная история изменений всех моделей папки (по дате, затем по файлу)."""
    paths = []
    if settings.get("recurse", True):
        for dp, _, files in os.walk(folder):
            for f in files:
                if MODELFILE.search(f):
                    paths.append(os.path.join(dp, f))
    else:
        for f in os.listdir(folder):
            if MODELFILE.search(f):
                paths.append(os.path.join(folder, f))
    rows = []
    for n, p in enumerate(sorted(paths), 1):
        if progress:
            progress(n, len(paths), p)
        try:
            rows += history_rows(p, settings)
        except Exception:
            pass
    rows.sort(key=lambda r: (r.get("_dt", "") == "", r.get("_dt", ""), r.get("Файл", "")))
    return rows


def parse_dt(s):
    """Разобрать «дд.мм.гггг» / «дд.мм.гггг чч:мм[:сс]»; None — если пусто или не разобрано."""
    s = (s or "").strip()
    if not s:
        return None
    for fmt in ("%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d.%m.%Y", "%d.%m.%y", "%d.%m"):
        try:
            d = datetime.datetime.strptime(s, fmt)
            if fmt == "%d.%m":
                d = d.replace(year=datetime.date.today().year)
            return d
        except ValueError:
            continue
    return None


def filter_history(rows, s_from, s_to):
    """Записи истории в границах «с»/«по» (строки вида дд.мм.гггг; пусто — без границы)."""
    f, t = parse_dt(s_from), parse_dt(s_to)
    if t and (t.hour, t.minute) == (0, 0):
        t = t + datetime.timedelta(days=1) - datetime.timedelta(seconds=1)
    out = []
    for r in rows:
        d = None
        if r.get("_dt"):
            try:
                d = datetime.datetime.fromisoformat(r["_dt"]).replace(tzinfo=None)
            except ValueError:
                d = None
        if f and (d is None or d < f):
            continue
        if t and (d is None or d > t):
            continue
        out.append(r)
    return out


def kind(raw):
    head = raw[:40].decode("cp1251", "replace")
    m = re.match(r"#UGC:2\s+([A-Z_/]+)", head)
    return m.group(1) if m else "?"


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
        self.rows = {"folders": [], "exclude": [], "db_mirror": []}
        box = ttk.Frame(self.win, padding=10)
        box.pack(fill="both", expand=True)
        ttk.Label(box, text="Папки сканирования (одна строка = один путь):",
                  font=("", 10, "bold")).pack(anchor="w")
        self.sec_scan = self._section(box, "folders")
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
        ttk.Label(box, text="Зеркала базы — после КАЖДОГО скана свежая база копируется и туда "
                            "(другая машина/диск). Пусто = не дублировать:",
                  foreground="#555").pack(anchor="w", pady=(8, 0))
        self.sec_mir = self._section(box, "db_mirror")
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
        for p in (settings.get("db_mirror") or []):
            self.add_row("db_mirror", p)
        if not self.rows["folders"]:
            self.add_row("folders", "")
        if not self.rows["exclude"]:
            self.add_row("exclude", "")
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
        for key in ("folders", "exclude", "db_mirror"):
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
        self.settings["db_dir"] = norm_path(self.e_db_dir.get())
        self.settings["db_mirror"] = d["db_mirror"]
        save_settings_file(self.settings)
        tail = ""
        new_dir = self.settings["db_dir"]
        if new_dir != old_dir:
            # папка базы поменялась — предупреждаем честно: подхватка только при перезапуске окна
            tail = " · база переедет на %s — ПЕРЕЗАПУСТИ окно" % (new_dir or "папку db\\")
        self.msg.config(text="сохранено: папок %d, исключений %d, зеркал %d%s"
                             % (len(d["folders"]), len(d["exclude"]), len(d["db_mirror"]), tail))
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


def save_csv(rows, path):
    if not rows:
        return
    # столбцы — объединение неслужебных ключей всех строк (служебные начинаются с "_")
    seen = []
    for r in rows:
        for k in r:
            if not k.startswith("_") and k not in seen:
                seen.append(k)
    cols = [c for c in DEFAULT_SETTINGS["columns"] if c in seen] + \
           [c for c in seen if c not in DEFAULT_SETTINGS["columns"]]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ------------------------------------------------------------------ окно истории
HIST_ALL = ["Файл", "Путь", "Тип", "Ревизия", "Дата", "Пользователь", "Компьютер",
            "Версия Creo", "Что изменено"]
HIST_DEFAULT = ["Файл", "Ревизия", "Дата", "Пользователь", "Компьютер", "Версия Creo",
                "Что изменено"]
HIST_WIDTH = {"Файл": 200, "Путь": 220, "Тип": 90, "Ревизия": 70, "Дата": 145,
              "Пользователь": 100, "Компьютер": 110, "Версия Creo": 100, "Что изменено": 360}


def history_window(parent, tk, ttk, filedialog, title, load, columns=None,
                   settings=None, save_settings=None, status=""):
    """Окно истории изменений: load() -> список записей.

    Столбцы выбираются кнопкой «Столбцы…» (сохраняются в настройках), сортировка — по клику заголовка.
    Файлы читаются один раз (в отдельном потоке), фильтр по датам мгновенный.
    """
    settings = settings if settings is not None else {}
    cols = [c for c in (settings.get("history_columns") or columns or HIST_DEFAULT) if c in HIST_ALL]
    if "Файл" in cols:
        cols = ["Файл"] + [c for c in cols if c != "Файл"]
    if not cols:
        cols = list(HIST_DEFAULT)

    w = _WINS.get(title)                      # одно окно на название: повторный клик не плодит окна
    if w is not None and w.winfo_exists():
        w.deiconify()
        w.lift()
        w.focus_force()
        return w
    win = tk.Toplevel(parent)
    _WINS[title] = win
    win.title(title)
    win.geometry("1160x560")
    h0 = time.time()
    bar = ttk.Frame(win, padding=6)
    bar.pack(fill="x")
    ttk.Label(bar, text="с:").pack(side="left")
    e_from = ttk.Entry(bar, width=12)
    e_from.pack(side="left", padx=(2, 8))
    ttk.Label(bar, text="по:").pack(side="left")
    e_to = ttk.Entry(bar, width=12)
    e_to.pack(side="left", padx=(2, 8))
    ttk.Label(bar, text="дд.мм.гггг (пусто — без границы)").pack(side="left")
    lbl = ttk.Label(bar, text="…")
    lbl.pack(side="right")

    body = ttk.Frame(win)
    body.pack(fill="both", expand=True, padx=6, pady=6)
    body.rowconfigure(0, weight=1)
    body.columnconfigure(0, weight=1)

    cache, shown = [], []
    sort_state = {"col": "Дата", "desc": True}

    def hkey(r, col):
        v = r.get(col, "")
        if col == "Ревизия":
            try:
                return (0, int(v))
            except (TypeError, ValueError):
                return (1, 0)
        if col == "Дата":
            d = parse_dt(v)
            return (0, d.timestamp()) if d else (1, 0)
        return (0, str(v).lower())

    def make_tree():
        tv = ttk.Treeview(body, columns=cols, show="headings", height=18)
        for c in cols:
            tv.heading(c, text=c, command=lambda c=c: set_sort(c))
            tv.column(c, width=HIST_WIDTH.get(c, 140), anchor="w")
        return tv

    tree = make_tree()
    vsb = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
    hsb = ttk.Scrollbar(body, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")

    def set_sort(col):
        if sort_state["col"] == col:
            sort_state["desc"] = not sort_state["desc"]
        else:
            sort_state["col"], sort_state["desc"] = col, False
        render()

    def rebuild_tree():
        nonlocal tree
        tree.destroy()
        tree = make_tree()
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.configure(command=tree.yview)
        hsb.configure(command=tree.xview)
        tree.grid(row=0, column=0, sticky="nsew")
        render()

    def render(*_):
        rows = filter_history(cache, e_from.get(), e_to.get())
        rows.sort(key=lambda r: hkey(r, sort_state["col"]), reverse=sort_state["desc"])
        shown[:] = rows
        tree.delete(*tree.get_children())
        for r in rows:
            tree.insert("", "end", values=[r.get(c, "") for c in cols])
        for c in cols:
            mark = "  ▼" if (sort_state["col"] == c and sort_state["desc"]) else \
                   ("  ▲" if sort_state["col"] == c else "")
            tree.heading(c, text=c + mark)
        lbl.config(text="записей: %d из %d" % (len(rows), len(cache)))

    def loaded(rows):
        cache[:] = rows
        render()
        _secs = time.time() - h0
        log_line("history: %s -> записей %d за %.1f с" % (status or title, len(rows), _secs))
        if not rows:
            lbl.config(text="записей нет" + (" (%s)" % status if status else ""))
        else:
            lbl.config(text="записей: %d за %.1f с" % (len(rows), _secs))

    def work():
        try:
            q.put(("ok", load()))
        except Exception as e:
            q.put(("err", str(e)))

    def poll():
        try:
            tag, payload = q.get_nowait()
        except queue.Empty:
            win.after(150, poll)
            return
        if tag == "ok":
            loaded(payload)
        else:
            lbl.config(text="ошибка чтения: %s" % payload)

    def exp():
        if not shown:
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="history.csv",
                                         filetypes=[("CSV", "*.csv")])
        if p:
            save_csv(shown, p)
            lbl.config(text="выгружено: %s" % os.path.basename(p))

    def choose_cols():
        ch = tk.Toplevel(win)
        ch.title("Столбцы истории — сохраняются в настройках")
        ch.geometry("480x340")
        ttk.Label(ch, text="Какие столбцы показывать в истории («Файл» — всегда первый):").pack(
            anchor="w", padx=8, pady=(8, 2))
        box = ttk.Frame(ch, padding=8)
        box.pack(fill="x")
        vars_ = {}
        for f in HIST_ALL:
            vars_[f] = tk.BooleanVar(value=f in cols)
            cb = ttk.Checkbutton(box, text=f, variable=vars_[f])
            cb.pack(anchor="w")
            if f == "Файл":
                cb.state(["disabled"])

        def apply():
            cols[:] = ["Файл"] + [f for f in HIST_ALL if f != "Файл" and vars_[f].get()]
            settings["history_columns"] = list(cols)
            if save_settings:
                save_settings()
            rebuild_tree()
            ch.destroy()

        ttk.Button(ch, text="Применить и сохранить", command=apply).pack(anchor="w", padx=8, pady=(0, 10))

    def show_versions():
        if not cache:
            return
        p = os.path.join(cache[0].get("Путь", ""), cache[0].get("Файл", ""))
        try:
            rows_v = version_diff(p, settings)
        except Exception:
            rows_v = []
        versions_window(win, tk, ttk, filedialog,
                        "Версии — %s" % os.path.basename(p), rows_v)

    ttk.Button(bar, text="Показать", command=render).pack(side="left", padx=8)
    ttk.Button(bar, text="Столбцы…", command=choose_cols).pack(side="left", padx=4)
    ttk.Button(bar, text="Версии…", command=show_versions).pack(side="left", padx=4)
    ttk.Button(bar, text="Выгрузить в CSV", command=exp).pack(side="left", padx=4)
    e_from.bind("<Return>", render)
    e_to.bind("<Return>", render)
    q = queue.Queue()
    win._plm_hist = {"render": render, "tree": lambda: tree}   # для самопроверки
    threading.Thread(target=work, daemon=True).start()
    win.after(150, poll)
    return win


# ------------------------------------------------------------------ окно
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

    # ПЕРЕВОД НА КАРКАС 04.10.2026: было три строки вручную (tk.Tk + title + geometry + minsize).
    # Теперь каркас даёт то же самое разом (make_root: заголовок с версией, размеры, minsize,
    # общий фон и тема vista). Всё остальное (группы кнопок, вкладки, три уровня) — своё
    # и остаётся: это и есть смысл инструмента.
    root = U.make_root(APP_TITLE, "1560x820", minsize=(760, 420))

    top = ttk.Frame(root, padding=6)
    top.pack(fill="x", padx=6, pady=(6, 4))
    row1 = ttk.Frame(top)                  # строка групп 1: ПАПКИ · СКАН · ПОКАЗ
    row1.pack(fill="x")
    row2 = ttk.Frame(top)                  # строка групп 2: ПУРГЕ · СКАНИРОВАНИЕ · ИНСТРУМЕНТЫ
    row2.pack(fill="x", pady=(6, 0))
    grp_paths = ttk.LabelFrame(row1, text=" ПАПКИ ", padding=8)
    grp_paths.pack(side="left", fill="both")
    grp_scan = ttk.LabelFrame(row1, text=" СКАН ", padding=8)
    grp_scan.pack(side="left", fill="both", padx=(8, 0))
    grp_show = ttk.LabelFrame(row1, text=" ПОКАЗ ", padding=8)
    grp_show.pack(side="left", fill="both", padx=(8, 0))
    grp_purge = ttk.LabelFrame(row2, text=" ПУРГЕ — старые версии в бэкап, удаления нет ", padding=8)
    grp_purge.pack(side="left", fill="both")
    grp_do = ttk.LabelFrame(row2, text=" СКАНИРОВАНИЕ ", padding=8)
    grp_do.pack(side="left", fill="both", padx=(8, 0))
    grp_tools = ttk.LabelFrame(row2, text=" ИНСТРУМЕНТЫ ", padding=8)
    grp_tools.pack(side="left", fill="both", padx=(8, 0))
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
    lbl_p = ttk.Label(spath, text="", foreground="#666", justify="left", wraplength=300)
    lbl_p.grid(row=1, column=0, sticky="w", pady=(4, 0))
    lbl_e = ttk.Label(spath, text="", foreground="#666", justify="left", wraplength=300)
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
    b_purge_plan = ttk.Button(grp_purge, text="ПУРГЕ: ПЛАН", width=20,
                              command=lambda: purge_show())
    b_purge_plan.pack(anchor="w", pady=1)
    b_purge_run = ttk.Button(grp_purge, text="ПУРГЕ: в бэкап…", width=20,
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

    def _vgrid(parent, items, per_col=4, width=20):
        """Кнопки ВЕРТИКАЛЬНО: не больше per_col в столбик, дальше — следующий столбец правее."""
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
                _upd_status("обновлено до %s — перезапустите программу" % remote)
                root.after(0, lambda: messagebox.showinfo(
                    "Обновление",
                    "Обновлено до %s.\nФайлов: %d, устаревших убрано: %d.\n\n"
                    "Перезапустите программу." % (remote, len(res.get("updated", [])),
                                                  len(res.get("obsolete", [])))))
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



    data = ttk.Frame(root, padding=6)
    data.pack(fill="x", padx=6, pady=(0, 4))

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
    lpane = ttk.Frame(root)
    lpane.pack(side="bottom", fill="x", padx=6, pady=(0, 6))

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

    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True, padx=6, pady=(0, 6))
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
                for name, how in eng.mfg_models(b, 30):
                    tree_widget.insert(dn0, "end", text="оснастка: %s  (%s)" % (name, how),
                                       values=("оснастка", name, "", "", "", "", "", "", ""))
        if mfg:
            mn = tree_widget.insert(node, "end", open=True, text="модельная оснастка (MFG):")
            for name, how in mfg[:60]:
                tree_widget.insert(mn, "end", text="%s  (%s)" % (name, how),
                                   values=("оснастка", name, "", "", "", "", "", "", ""))
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
        return len(der), sum(len(v) for v in up.values()), len(kids)

    def _model_values(m):
        i = eng.models_info([m]).get(m, ("", "", "", 0, "", "", 0, 0))
        return _vals9(m, i)

    def _kind(k):
        return {"наследование": "заготовка", "производная": "отливка",
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
    tview.bind("<Double-1>", lambda ev: open_detail())      # двойной щёлчок — карточка изделия

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
        head = ("ПУРГЕ-план: лишних версий %d · освободится %.1f МБ · папка %s"
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
        _text_window("ПУРГЕ: ПЛАН (файлы не трогаются)", head, txt,
                     "отчёт: %s" % (os.path.basename(rep) if rep else "не сохранён"))

    def purge_run():
        """Перенос лишних версий в БЭКАП — встроенным движком ПЛМ (внешний purge_versions не нужен)."""
        from tkinter import messagebox as mb
        folder = purge_folder()
        plan = eng.purge_plan(folder or None, int(e_keep.get() or 2))
        if not plan["count"]:
            lbl.config(text="ПУРГЕ: чистить нечего — лишних версий нет")
            return
        if not folder or not os.path.isdir(folder):
            lbl.config(text="ПУРГЕ: выбери существующую папку (кнопка «Пути и исключения…»)")
            return
        keep = int(e_keep.get() or 2)
        bdir = os.path.join(folder, "_purge_backup")
        if not mb.askyesno("ПУРГЕ",
                           "Перенести в БЭКАП %d лишних версий (%.1f МБ)?\n%s\n\n"
                           "Удаления нет: файлы уедут в %s"
                           % (plan["count"], plan["bytes"] / 1048576.0, folder, bdir)):
            lbl.config(text="ПУРГЕ: отменено")
            return

        def work():
            try:
                rep = eng.purge_execute(folder, keep, None)
                out = ("перенесено %d версий, освобождено %.1f МБ, за %.1f с\nбэкап: %s"
                       % (len(rep["перенесено"]), rep["освобождено_байт"] / 1048576.0,
                          rep["seconds"], bdir))
                if rep["пропущено_с_причиной"]:
                    out += "\nпропущено: " + "; ".join(rep["пропущено_с_причиной"][:20])
            except Exception as e:
                out = "ОШИБКА: %s" % e
            log_line("purge execute: %s -> %s" % (folder, out.split("\n")[0]))

            def done():
                head = "ПУРГЕ: %s" % out.split("\n")[0]
                lbl.config(text=head)
                _text_window("ПУРГЕ: перенос в бэкап — результат", head, out, bdir)

            try:
                root.after(0, done)
            except Exception:
                pass

        threading.Thread(target=work, daemon=True).start()
        lbl.config(text="ПУРГЕ: переношу лишние версии в бэкап…")

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
                           lambda: history_rows(r[0], {"max_size_mb": float(e_max.get() or 0)}),
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
    lnb = ttk.Notebook(lpane)                  # НИЖНЕЕ окно — ноутбук со своими режимами-вкладками
    lnb.pack(fill="both", expand=True)
    liv = ttk.Frame(lnb, padding=4)
    lnb.add(liv, text=" Дерево производства ")
    lsum = ttk.Label(liv, text="выбери что-либо в ЛЮБОЙ вкладке сверху — дерево построится само")
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
    lout = tk.Text(llinks, height=4, font=("Consolas", 9), bg="#fbfbfb")   # вывод кнопок (перенесено из «Дерева»)
    lout.pack(fill="x")
    # ==== 04.10.2026: вкладка «Свойства детали» — площадь, техтребования, параметры, чертежи ====
    lprop = ttk.Frame(lnb, padding=4)
    lnb.add(lprop, text=" Свойства детали ")
    lpsum = ttk.Label(lprop, text="выбери изделие — покажу площадь, техтребования, "
                                   "числовые параметры и связанные чертежи")
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
                               "числовые параметры и связанные чертежи")
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
        dwg = dwg_models(raw)
        add("Показывает модели (если это чертёж)", ", ".join(dwg) if dwg else "— не чертёж")
        lpsum.config(text="%s — свойства из ФАЙЛА модели (площадь, ТТ, параметры, чертежи)"
                      % model)


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
        der, ups, dn = _branch_updown(rn, model)
        try:
            ltv.yview_moveto(0)                 # показать начало дерева
            ltv.see(rn)
        except Exception:
            pass
        lsum.config(text="онлайн: %s — состав %d · входит в сборок %d (все уровни) · заготовок/отливок %d"
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

        # ▼ вниз — СОСТАВ (ленивая загрузка уровней)
        dn = ltv2.insert(rn, "end", open=False, text="▼ состав (вниз)")
        if not kids:
            ltv2.insert(dn, "end", text="— в базе нет состава")
        for c, q in kids:
            nn = ltv2.insert(dn, "end", text="%s  x%d" % (c, q), values=iv(c, "x%d" % q))
            _LLINKS[nn] = (c, "down")
            ltv2.insert(nn, "end", text="загрузка…")

        # ▼ вниз — ОТРАЖЕНИЯ (кто сделан ИЗ этой модели)
        ref = ltv2.insert(rn, "end", open=bool(refl), text="▼ отражения (сделано из неё): %d" % len(refl))
        if not refl:
            ltv2.insert(ref, "end", text="— обратных связей нет")
        for c, k in refl:
            kd = {"наследование": "заготовка", "производная": "отливка"}.get(k, "заготовка/отливка")
            ltv2.insert(ref, "end", text="%s: %s" % (kd, c), values=("отражение", c, "", "", ""))

        # ▼ вниз — НАСЛЕДОВАННАЯ ГЕОМЕТРИЯ (заготовки/отливки этой модели)
        inh = ltv2.insert(rn, "end", open=bool(bases),
                          text="▼ наследованная геометрия (заготовки/отливки): %d" % len(bases))
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
        lsum2.config(text="связи: %s — состав %d · отражений %d · заготовок/отливок %d · сборок вверх %d"
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

    def _bottom_render():
        """Наполнить АКТИВНУЮ вкладку нижнего окна выбранной моделью (или автосводкой)."""
        model = _last["model"]
        try:
            active = lnb.index(lnb.select())
        except Exception:
            active = 0
        if active == 2:
            # 04.10.2026: «Свойства детали» — площадь, ТТ, параметры, чертежи
            try:
                _prop_show(model)
            except Exception as e:      # вкладка не должна ронять всё окно
                ptv.delete(*ptv.get_children())
                ptv.insert("", "end", values=("Ошибка разбора",
                                               "%s: %s" % (type(e).__name__, e)))
                lpsum.config(text="не удалось показать свойства: %s" % e)
            return
        if not model:
            if active == 1:
                ltv2.delete(*ltv2.get_children())
                _LLINKS.clear()
                lsum2.config(text="выбери что-либо в ЛЮБОЙ вкладке сверху — связи построятся сами")
            else:
                live_auto()
            return
        if active == 1:
            _links_show(model)
        else:
            _prod_show(model)

    def _bottom_show(model):
        """Показать в НИЖНЕМ окне связи модели. Зовут все вкладки. Вид решает активная вкладка низа."""
        model = eng.stem(model or "")
        _last["model"] = model
        _bottom_render()

    lnb.bind("<<NotebookTabChanged>>", lambda ev: _bottom_render())

    def live_tree(event=None):
        """ОНЛАЙН по выбранной строке ТАБЛИЦЫ: состав ВНИЗ и ВСЕ сборки ВВЕРХ."""
        sel = tree.selection()
        row = _ROWS.get(sel[0]) if sel else None
        if not row:
            live_auto()
            return
        p = row.get("_path") or ""
        _bottom_show(eng.stem(os.path.basename(p)) if p else "")

    tree.bind("<<TreeviewSelect>>", live_tree)

    def expl_live(event=None):
        """Выбор в ПРОВОДНИКЕ → нижнее окно (выбран файл → связи его модели)."""
        p = _EFILE.get(eview.focus())
        if p:
            _bottom_show(eng.stem(os.path.basename(p)))

    eview.bind("<<TreeviewSelect>>", expl_live)

    def tree_live(event=None):
        """Выбор в ДЕРЕВЕ → нижнее окно (узел → связи его модели)."""
        sel = tview.focus()
        if not sel:
            return
        txt = (tview.item(sel, "text") or "").strip()
        m = eng.stem(txt.split()[0]) if txt else ""
        if m:
            _bottom_show(m)

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
        _tail = ("  ·  старые версии после ПУРГЕ: %d — норма" % _p) if _p else ""
        if r.get("need"):
            lbl.config(text="НУЖЕН СКАН: новых %d · изменённых %d · пропало %d (%.1f с)%s"
                       % (r["new"], r["mod"], r["gone"], r["secs"], _tail))
        else:
            lbl.config(text="БАЗА АКТУАЛЬНА: изделий %d (файлов на диске %d, с копиями версий), изменений нет (%.1f с)%s"
                       % (r.get("models", r["total"]), r["total"], r["secs"], _tail))
        log_line("check: %s" % r.get("verdict", ""))

    def load_base(limit=2000):
        """Показать базу БЕЗ чтения файлов: строки паспортов из plm_reader.db."""
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
                                  ("ПУРГЕ-ПЛАН", b_purge_plan), ("ПУРГЕ-бэкап", b_purge_run)):
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
                       lambda: history_rows(path, hist_settings()),
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
                        rows = db_rows(roots_now or None, 5000)
                        total = db_total(roots_now or None)
                        rows_all.clear()
                        tree.delete(*tree.get_children())
                        rows_all.extend(rows)
                        redraw()
                        lbl.config(text="скан базы за %.1f с: новых %d · изменённых %d · "
                                        "пропущено (уже в базе) %d · в базе %d, показано %d · исключено папок %d%s"
                                   % (_secs, st.get("new", 0), st.get("mod", 0), st.get("skipped", 0),
                                      total, len(rows), len(exclude_list(settings.get("exclude"))),
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
                w.event_generate(seq)          # Treeview и прочие без своего обработчика
        except Exception:
            pass
        return "break"

    def _on_copy(ev=None):
        w = _foc()
        try:
            if isinstance(w, ttk.Treeview):
                txt = "\n".join("\t".join(str(x) for x in w.item(i, "values")) for i in w.selection())
                root.clipboard_clear()
                root.clipboard_append(txt)
                return "break"
        except Exception:
            pass
        return _clip_ev("<<Copy>>")

    def _sel_all(ev=None):
        w = _foc()
        try:
            if isinstance(w, tk.Text):
                w.tag_add("sel", "1.0", "end-1c")
            elif w is not None:
                w.selection_range(0, "end")
                w.icursor("end")
        except Exception:
            pass
        return "break"

    def _menu_pop(ev):
        w = ev.widget
        m = tk.Menu(root, tearoff=0)
        try:
            if isinstance(w, ttk.Treeview):
                m.add_command(label="Копировать строку(и)", command=_on_copy)
            else:
                m.add_command(label="Вырезать", command=lambda: w.event_generate("<<Cut>>"))
                m.add_command(label="Копировать", command=lambda: w.event_generate("<<Copy>>"))
                m.add_command(label="Вставить", command=lambda: w.event_generate("<<Paste>>"))
                m.add_separator()
                m.add_command(label="Выделить всё", command=lambda: _sel_all())
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

    root.bind_all("<Control-c>", _on_copy)
    root.bind_all("<Control-v>", lambda e: _clip_ev("<<Paste>>"))
    root.bind_all("<Control-x>", lambda e: _clip_ev("<<Cut>>"))
    root.bind_all("<Control-a>", _sel_all)
    root.bind_all("<Control-Insert>", _on_copy)
    root.bind_all("<Shift-Insert>", lambda e: _clip_ev("<<Paste>>"))
    root.after(700, _bind_clip_all)                 # ПКМ-меню в существующих полях

    btn.config(command=go)
    _bs = db_summary()
    log_line("base: изделий %d, файлов с копиями версий %d, связей %d, папок %d, изменений %d"
             % (_bs.get("models", 0), _bs.get("files", 0), _bs.get("links", 0),
                _bs.get("folders", 0), _bs.get("changes", 0)))
    if _bs.get("files"):
        # V35: цифры по-человечески — главная = ИЗДЕЛИЯ (без дублей .1/.2), рядом файлы с копиями версий
        lbl.config(text="база: изделий %d (файлов с копиями версий %d) · изменений %d — читаю из базы…"
                   % (_bs.get("models", 0), _bs.get("files", 0), _bs.get("changes", 0)))
        load_base()
        root._plm_db_stamp = _active_stamp()
        check_base()
        root.after(500, live_auto)         # нижнее дерево ПЛМ строится само при открытии

    root.after(15000, watch_db)            # автообновление: если базу обновил другой ПК

    # Порядок сверху вниз: Папка+Выбрать → Глубина и ПУРГЕ → кнопки (Сканировать и пр.) → ОКНО → данные
    try:
        for _w in (top, mid, data, nb):
            _w.pack_forget()
        data.pack(side="bottom", fill="x", padx=6, pady=(0, 6))    # самый низ — данные
        top.pack(side="top", fill="x", padx=6, pady=(6, 4))        # сверху — папка, глубина, ПУРГЕ
        mid.pack(side="top", fill="x", padx=6, pady=(0, 4))        # ниже — Сканировать и остальные
        nb.pack(side="top", fill="both", expand=True, padx=6, pady=(0, 0))   # окно — под кнопками
    except Exception:
        pass

    try:                                   # окно не «прыгает» при переключении вкладок
        root.update_idletasks()
        root.geometry("1560x820")          # шире и выше: верхняя панель вкладок видна сразу
    except Exception:
        pass
    try:                                   # тихая проверка обновлений при старте (есть — предложит)
        root.after(2500, lambda: check_updates_ui(False))
    except Exception:
        pass
    root.mainloop()


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
    run_gui()


if __name__ == "__main__":
    main()

