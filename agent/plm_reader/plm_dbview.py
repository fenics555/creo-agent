import os
import re
import sqlite3
import datetime
from plm_settings import (
    DATA_DIR, CACHE_FILE, DB_FILE, LOG_DIR, log_line, norm_path, path_under
)

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
        q = lambda s: c.execute(s).fetchone()[0]
        out = {"files": q("SELECT COUNT(*) FROM snapshots"),
               "models": q("SELECT COUNT(DISTINCT model) FROM snapshots"),
               "links": q("SELECT COUNT(*) FROM links"),
               "folders": q("SELECT COUNT(*) FROM folders"),
               "changes": q("SELECT COUNT(*) FROM changes")}
        c.close()
        return out
    except Exception:
        return {}

def _ver(p):
    """Версия изделия из пути к файлу (если есть в базе)."""
    try:
        return int(p.rsplit(".", 1)[1])
    except Exception:
        return 0

def _fs_date(ts):
    """Время файла (epoch) -> 'дд.мм.гггг чч:мм' (или пусто)."""
    try:
        return datetime.datetime.fromtimestamp(float(ts)).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return ""

def db_rows_map(folder=None, latest_only=False):
    """Карта строк: {path: {data}}."""
    rows = db_rows(folder, limit=10000, latest_only=latest_only)
    return {r["_path"]: r for r in rows}

def db_rows(folder=None, limit=2000, latest_only=False):
    """Строки паспортов ИЗ БАЗЫ (файлы не читаются).
    `folder` — путь ИЛИ СПИСОК путей (основная + «Папка2»)."""
    roots = [f for f in ([folder] if isinstance(folder, str) else list(folder or [])) if f]
    try:
        c = db_conn()
        has = any(r[1] == "created" for r in c.execute("PRAGMA table_info(snapshots)"))
        sql = ("SELECT path,model,volume,material,name,designation,rev,author,revdate,role,hist,creo,"
               "mtime%s FROM snapshots %%s ORDER BY model, path LIMIT ?") % (",created" if has else "")
        if roots:
            cond = "WHERE " + " OR ".join(["folder LIKE ?"] * len(roots))
            args = tuple(r.rstrip("\\") + "%" for r in roots)
            data = [tuple(r) + ((None,) if not has else ())
                    for r in c.execute(sql % cond, args + (limit,))]
            vers = dict(c.execute("SELECT model, COUNT(*) FROM snapshots " + cond +
                                  " GROUP BY model", args))
            if not data:                    # регистр/слэши не совпали — фильтруем в питоне
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

