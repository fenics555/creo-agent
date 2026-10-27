# -*- coding: utf-8 -*-
"""plm_dbview.py — вынесено из plm_reader.py распилом (см. СПЕКА_РАСПИЛА_PLM_READER.md)."""
from plm_reader import (
    CACHE_FILE,
    DATA_DIR,
    DB_FILE,
    LOG_DIR,
    datetime,
    json,
    os,
    re,
)


def path_under(*a, **k):
    """Ленивый шим: dbview НЕ тянет plm_scan на импорте (разрыв цикла dbview↔scan)."""
    from plm_scan import path_under as _pu
    return _pu(*a, **k)


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
def _vol_str(v):
    """Объём в мм³ по-человечески: мелкий — мм³, крупный — ещё и м³.

    V114: ОТСЕВ МУСОРА (как в V106 для таблицы): битый double (`1e+100`) — это случайные
    8 байт, попавшие на шаблон. Правдоподобный объём детали — 0…1e9 мм³ (1 м³).
    """
    try:
        v = float(v)
    except Exception:
        return "?"
    if not (v == v) or v <= 0 or v > 1e9:          # NaN / <=0 / больше 1 м³ — мусор
        return "—"
    if v >= 1e9:
        return "%.2f м³ (%.0f мм³)" % (v / 1e9, v)
    return "%.0f мм³" % v
def orphan_models(limit=5000):
    """V114: ДЕТАЛИ-ОДИНОЧКИ — модели, которые НИГДЕ не используются.

    Файл в базе есть, но модель не входит ни в одну сборку (ни как родитель, ни как ребёнок).
    Это готовый список кандидатов на архив/чистку склада. Возвращает [(модель, путь, объём, ревизия)].
    """
    try:
        c = db_conn()
        rows = c.execute("""SELECT s.model, s.path, s.volume, s.rev
                            FROM snapshots s
                            WHERE NOT EXISTS (SELECT 1 FROM links l WHERE l.child=s.model)
                              AND NOT EXISTS (SELECT 1 FROM links l WHERE l.parent=s.model)
                            ORDER BY s.model LIMIT ?""", (int(limit),)).fetchall()
        c.close()
        return [tuple(r) for r in rows]
    except Exception:
        return []


def db_facts():
    """«Интересные факты» по активной базе: размер, крайние связи, что ест место.

    V114: добавлены факты, которые ПОДСКАЗЫВАЮТ ДЕЙСТВИЕ — детали-одиночки (кандидаты на архив),
    материал без нормы, распределение по годам/авторам/версиям Creo. Список одиночек открывается
    кнопкой в окне «Дополнительно» (см. `orphan_models`).

    Возвращает (lines, warn): lines — [(подпись, значение)], warn — предупреждение о росте."""
    lines, warn = [], ""
    try:
        p = _active_db_file()
        size = os.path.getsize(p)
        lines.append(("Файл базы", "%s  ·  %.1f МБ" % (os.path.basename(p), size / 1e6)))
        c = db_conn()

        def one(q):
            try:
                return c.execute(q).fetchone()
            except Exception:
                return None

        def qrows(q):
            """V114: несколько строк (для «интересных фактов»: топы, распределения)."""
            try:
                return c.execute(q).fetchall()
            except Exception:
                return []

        r = one("SELECT COUNT(*), COUNT(DISTINCT model) FROM snapshots")
        lines.append(("Паспортов (строк)", "%s  ·  изделий: %s" % (r[0], r[1]) if r else "—"))
        lines.append(("Связей (состав)", str((one("SELECT COUNT(*) FROM links") or (0,))[0])))
        lines.append(("Происхождений", str((one("SELECT COUNT(*) FROM derived") or (0,))[0])))
        dn = one("SELECT COUNT(DISTINCT child) FROM derived") or (0,)
        lines.append(("Пересохранено из других", "%d изделий (заготовка/отливка)" % dn[0]))
        ch = one("SELECT COUNT(*) FROM changes") or (0,)
        ar = one("SELECT COUNT(*) FROM changes WHERE kind='архив'") or (0,)
        lines.append(("Изменений (журнал)", "%d  ·  архивных: %d" % (ch[0], ar[0])))
        au = one("SELECT author, COUNT(*) FROM snapshots WHERE COALESCE(author,'')<>'' "
                 "GROUP BY author ORDER BY COUNT(*) DESC LIMIT 1")
        if au:
            lines.append(("Самый активный автор", "%s — %d файлов" % (au[0], au[1])))
        f = one("SELECT parent, COUNT(*) FROM links GROUP BY parent ORDER BY COUNT(*) DESC LIMIT 1")
        if f:
            lines.append(("Самая большая сборка", "%s — %d деталей" % (f[0], f[1])))
        f = one("SELECT child, COUNT(*) FROM links GROUP BY child ORDER BY COUNT(*) DESC LIMIT 1")
        if f:
            lines.append(("Самая ходовая деталь", "%s — входит в %d сборок" % (f[0], f[1])))
        f = one("SELECT model, volume FROM snapshots WHERE volume>0 AND volume<=1e9 "
                "ORDER BY volume DESC LIMIT 1")
        if f:
            lines.append(("Самый большой объём", "%s — %s" % (f[0], _vol_str(f[1]))))
        f = one("SELECT model, size FROM snapshots ORDER BY size DESC LIMIT 1")
        if f:
            lines.append(("Самый крупный файл", "%s — %.1f МБ" % (f[0], (f[1] or 0) / 1e6)))
        f = one("SELECT model, created FROM snapshots WHERE created IS NOT NULL ORDER BY created ASC LIMIT 1")
        if f and f[1]:
            lines.append(("Старейший файл", "%s — %s" % (f[0], _fs_date(f[1]))))
        f = one("SELECT model, created FROM snapshots WHERE created IS NOT NULL ORDER BY created DESC LIMIT 1")
        if f and f[1]:
            lines.append(("Новейший файл", "%s — %s" % (f[0], _fs_date(f[1]))))
        f = one("SELECT MIN(ts), MAX(ts) FROM changes")
        if f:
            lines.append(("История изменений", "%s  …  %s" % (f[0] or "?", f[1] or "?")))
        heavy = []
        for (t,) in c.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            if t == "sqlite_sequence":
                continue
            rr = one("SELECT COUNT(*) FROM %s" % t)
            heavy.append((rr[0] if rr else 0, t))
        heavy.sort(reverse=True)
        lines.append(("Что ест место (строк)", ", ".join("%s: %s" % (t, n) for n, t in heavy[:6])))

        # ═══════════════ V114: ИНТЕРЕСНЫЕ ФАКТЫ, КОТОРЫЕ ПОМОГАЮТ В РАБОТЕ ═══════════════
        # Владелец: «нужно каждый раз что-то интересное добавить». Здесь не «цифры ради цифр»,
        # а то, что реально подсказывает действие: что можно убрать, что надо привести в порядок.
        try:
            # 1. ДЕТАЛИ-ОДИНОЧКИ: файл есть, но НИ в одной сборке не участвует (ни как родитель,
            #    ни как ребёнок). Это готовый список «кандидатов на архив/чистку склада».
            orph = one("""SELECT COUNT(*) FROM snapshots s
                          WHERE NOT EXISTS (SELECT 1 FROM links l WHERE l.child=s.model)
                            AND NOT EXISTS (SELECT 1 FROM links l WHERE l.parent=s.model)""")
            if orph:
                lines.append(("🔍 Детали-одиночки (нигде не используются)",
                              "%d моделей — кандидаты на архив (кнопка «Проверить» → фильтр)" % orph[0]))
            # 2. МАТЕРИАЛ без нормы: пусто или системное значение PTC_* — паспорт не заполнен.
            mbad = one("""SELECT COUNT(*) FROM snapshots
                          WHERE COALESCE(material,'')='' OR material LIKE 'PTC_%'""")
            if mbad:
                lines.append(("⚠ Материал без нормы (пусто/PTC_*)",
                              "%d моделей — паспорт не заполнен" % mbad[0]))
            # 3. ДУБЛИ МАТЕРИАЛОВ по смыслу: одно и то же записано по-разному
            #    (STEEL_40X / «Сталь 45 ГОСТ…» / STEEL_45) — повод договориться о едином виде.
            mat = qrows("""SELECT COALESCE(NULLIF(material,''),'(пусто)') m, COUNT(*) n
                       FROM snapshots GROUP BY m ORDER BY n DESC LIMIT 12""")
            if mat:
                lines.append(("📋 Материалы (топ-6)",
                              ", ".join("%s: %s" % (m, n) for m, n in mat[:6])))
            # 4. ГОДЫ СОЗДАНИЯ — сразу видно «свежесть» склада.
            yr = qrows("""SELECT strftime('%Y', datetime(created,'unixepoch','localtime')) y, COUNT(*) n
                      FROM snapshots WHERE created>0 GROUP BY y ORDER BY y DESC LIMIT 4""")
            if yr:
                lines.append(("🗓 По годам создания",
                              ", ".join("%s: %s" % (y, n) for y, n in yr)))
            # 5. ТОП АВТОРОВ (кто наполнял склад).
            au2 = qrows("""SELECT COALESCE(NULLIF(author,''),'(пусто)') a, COUNT(*) n
                       FROM snapshots GROUP BY a ORDER BY n DESC LIMIT 5""")
            if au2:
                lines.append(("👤 Авторы (топ-5)",
                              ", ".join("%s: %s" % (a, n) for a, n in au2)))
            # 6. ВЕРСИИ CREO — видно, на чём работают (и где «зоопарк» версий).
            cr = qrows("""SELECT COALESCE(NULLIF(creo,''),'(нет)') c, COUNT(*) n
                      FROM snapshots GROUP BY c ORDER BY n DESC LIMIT 6""")
            if cr:
                lines.append(("🧩 Версии Creo (топ-6)",
                              ", ".join("%s: %s" % (c, n) for c, n in cr)))
        except Exception:
            pass
        c.close()
        # след на диске: ВСЕ версии базы + бэкапы — это и есть «рост» (главный вопрос владельца)
        tot, cnt = 0, 0
        try:
            for _root, _dirs, _fs in os.walk(DATA_DIR):
                for _fn in _fs:
                    if _fn.lower().endswith(".db"):
                        tot += os.path.getsize(os.path.join(_root, _fn))
                        cnt += 1
        except Exception:
            pass
        lines.append(("След на диске (все базы+бэкапы)", "%.2f ГБ  ·  файлов: %d" % (tot / 1e9, cnt)))
        if size > 1.5e9:
            warn = ("⚠ База %.1f ГБ и растёт. Сейчас хранятся 3 версии базы (ротация сверх этого) — "
                    "нужен retention: чистить старые архивные срезы и/или историю, иначе будет расти вечно."
                    % (size / 1e9))
    except Exception as e:
        lines.append(("Ошибка", str(e)))
    return lines, warn
def _ver(p):
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
                "Объём, мм³": _vol_text(volume), "Габарит, мм": "",   # V106: отсев мусора
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
    """ПОИСК ПО ВСЕЙ БАЗЕ (фильтр делает SQL, не Python): каждое слово — в ЛЮБОМ видимом поле.

    V103 (24.10.2026): раньше читалась ВСЯ таблица `snapshots` в Python и фильтровалась там —
    на 40k+ строк это заметно тормозило (владелец: «фильтр долго думает»). Теперь фильтр и
    LIMIT делает SQLite; в Python попадает только результат.

    V122 (жалоба владельца «фильтр очень сильно подвешивает в верхнем окне, а в HTML плавно»):
    при КАЖДОМ нажатии клавиши гонялись ДВА полных запроса — `COUNT(*)` по 12 колонкам LIKE
    (полный проход по 47k строк) и следом выборка. Теперь:
      * КЕШ результатов по (слова, лимит, ревизия базы) — повтор «того же фильтра» мгновенный;
      * при непустом «И» счётчик НЕ считаем отдельно — берём длину выборки (LIMIT+1: «есть ли ещё»);
      * счётчик `total` — это «найдено (не больше лимита)», его и показываем.

    Сначала «ВСЕ слова» (И); если так пусто — «ЛЮБОЕ слово» (ИЛИ), режим видно в строке состояния.
    Возвращает (строки, найдено_всего, режим).
    """
    ws = [w for w in (words or []) if w]
    if not ws:
        rows = db_rows(None, limit)
        return rows, len(rows), ""
    # --- кеш: тот же фильтр + та же ревизия базы → отдаём готовое (фильтр «не думает») ---
    try:
        key = ("|".join(ws), int(limit), _active_db_file(), _db_stamp())
    except Exception:
        key = None
    if key is not None:
        hit = _SEARCH_CACHE.get(key)
        if hit is not None:
            return hit
    cols = eng_file_search_cols()
    try:
        c = db_conn()
        has = any(r[1] == "created" for r in c.execute("PRAGMA table_info(snapshots)"))
        sel = ("SELECT path,model,volume,material,name,designation,rev,author,revdate,role,hist,creo,"
               "mtime%s FROM snapshots" % (",created" if has else ""))

        def where_for(join, arr):
            # V106: ищем ТОЛЬКО по текстовым полям. Числа (объём/записей/даты) в подстрочный
            # поиск НЕ берём — иначе «170» находил записи по цифрам внутри объёма.
            conds, params = [], []
            for w in arr:
                like = "%" + w + "%"
                conds.append("(" + " OR ".join(cols) + ")")
                params += [like] * len(cols)
            return join.join(conds), params

        w_and, p_and = where_for(" AND ", ws)
        # V122: НЕ считаем COUNT отдельно — берём выборку на (limit+1), чтобы знать «есть ли ещё»
        # и не гонять второй полный проход по 47k строк (это и «подвешивало» окно).
        _sel = sel + " WHERE " + w_and + " ORDER BY model, path LIMIT ?"
        _lim = int(limit) + 1
        data = [tuple(r) + ((None,) if not has else ()) for r in c.execute(_sel, p_and + [_lim])]
        mode = "И"
        if not data and len(ws) > 1:                  # «И» пусто → «ЛЮБОЕ слово» (ИЛИ)
            w_or, p_or = where_for(" OR ", ws)
            data = [tuple(r) + ((None,) if not has else ())
                    for r in c.execute(sel + " WHERE " + w_or + " ORDER BY model, path LIMIT ?",
                                       p_or + [_lim])]
            mode = "ИЛИ"
        total = len(data)
        if total > int(limit):                        # «есть ещё» — показываем «>limit»
            data = data[:int(limit)]
        vers = dict(c.execute("SELECT model, COUNT(*) FROM snapshots GROUP BY model"))
        c.close()
    except Exception:
        return [], 0, ""
    out = [_row_from_db(t, vers) for t in data]
    _search_cache_put(key, (out, total, mode))
    return out, total, mode


def _vol_text(v):
    """Объём по-человечески, с отсевом МУСОРА (V106).

    В старых базах есть «объёмы» из сотен цифр (битый double 1e+290) — их показывать нельзя
    (владелец видел простыню цифр в столбце). Правдоподобно: 0 … 1e9 мм³ (1000 м³).
    """
    try:
        f = float(v or 0)
    except (TypeError, ValueError):
        return ""
    if f != f or f <= 0 or f > 1e9:
        return ""
    return "%.0f" % f


def _row_from_db(t, vers=None):
    """Кортеж паспорта → словарь строки окна (единый вид с engine._row_dict)."""
    (p, model, volume, material, name, desig, rev, author, revdate, role, hist, creo,
     mtime, created) = (list(t) + [None] * 14)[:14]
    return {
        "Файл": os.path.basename(p or ""), "Тип": "", "Обозначение": desig or "",
        "Наименование": name or "", "Материал": material or "",
        "Объём, мм³": _vol_text(volume), "Габарит, мм": "",
        "Роль": role or "", "Родитель": "", "Ревизия": rev or "",
        "Дата": revdate or "", "Пользователь": author or "",
        "Создан": _fs_date(created), "_created_ts": float(created or 0),
        "Изменён": _fs_date(mtime), "_mtime_ts": float(mtime or 0),
        "Записей": str(hist or ""), "Версий": (vers or {}).get(model, 0),
        "Версия Creo": creo or "", "_path": p or "", "_model": model or "",
    }


# ── V122: КЕШ ПОИСКА. Фильтр в верхнем окне гонял `COUNT(*)` + выборку по 12 колонкам LIKE при
# КАЖДОМ нажатии клавиши (владелец: «очень сильно подвешивает»). Кеш по ключу (слова, лимит,
# файл базы, время правки базы) отдаёт повтор мгновенно; при смене базы ключ меняется сам.
_SEARCH_CACHE = {}
_SEARCH_CACHE_MAX = 64
_db_stamp_cache = [None, None]          # [путь, отпечаток]


def _db_stamp():
    """Отпечаток активной базы (путь + время правки + размер) — чтобы кеш поиска не «залипал»."""
    try:
        p = _active_db_file()
        st = os.stat(p)
        return (int(st.st_mtime), st.st_size)
    except Exception:
        return None


def _search_cache_put(key, val):
    """Положить результат в кеш (с простой ротацией: не даём словарю расти без предела)."""
    if key is None:
        return
    try:
        if len(_SEARCH_CACHE) >= _SEARCH_CACHE_MAX:
            _SEARCH_CACHE.clear()
        _SEARCH_CACHE[key] = val
    except Exception:
        pass


def eng_file_search_cols():
    """Колонки поиска из движка (единый источник: текстовые LIKE). Лениво — без цикла импортов."""
    try:
        import engine as _e
        return ["%s LIKE ?" % c for c in _e.FILE_COLS]
    except Exception:
        return ["path LIKE ?", "designation LIKE ?", "name LIKE ?", "material LIKE ?",
                "rev LIKE ?", "role LIKE ?", "model LIKE ?", "author LIKE ?", "creo LIKE ?",
                "folder LIKE ?", "revdate LIKE ?", "pdata LIKE ?"]
def log_line(text):
    """Одна строка в общий лог инструмента: D:\\AI\\log\\plm_reader\\plm_reader.log."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "plm_reader.log"), "a", encoding="utf-8") as f:
            f.write("%s  %s\n" % (datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"), text))
    except Exception:
        pass
