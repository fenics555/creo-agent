# -*- coding: utf-8 -*-
"""plm_history.py — вынесено из plm_reader.py распилом (см. СПЕКА_РАСПИЛА_PLM_READER.md)."""
from plm_reader import (
    DEFAULT_SETTINGS,
    MODELFILE,
    VERSION_FIELDS,
    VER_COLUMNS,
    changes_line,
    clean_computer,
    clean_name,
    csv,
    datetime,
    db_conn,
    eng,
    json,
    kind,
    log_line,
    os,
    parse_changes,
    queue,
    re,
    read_bytes,
    scan_file,
    sibling_versions,
    threading,
    time,
)


_WINS = {}                    # открытые окна историй: одно окно на название
def archive_dims(model):
    """(dims, hist) из боевой базы (таблицы arch_dims/arch_dim_ch из архива).

    dims — {dNN: мм} по свежайшей дате архива; hist — [(date, dim, old, new, kind)].
    Таблиц нет (старая база) → (None, None). Только чтение."""
    model = (model or "").strip()
    if not model:
        return None, None
    try:
        con = db_conn(ro=True)
    except Exception:
        return None, None
    try:
        tabs = {r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        dims, hist = None, []
        if "arch_dims" in tabs:
            row = con.execute("SELECT dims FROM arch_dims WHERE UPPER(model)=UPPER(?) "
                              "ORDER BY arch_date DESC LIMIT 1", (model,)).fetchone()
            if row and row[0]:
                try:
                    dims = json.loads(row[0])
                except Exception:
                    dims = None
        if "arch_dim_ch" in tabs:
            hist = [tuple(r) for r in con.execute(
                "SELECT arch_date, dim, old_val, new_val, kind FROM arch_dim_ch "
                "WHERE UPPER(model)=UPPER(?) ORDER BY arch_date", (model,))]
        return dims, hist
    except Exception:
        return None, None
    finally:
        try:
            con.close()
        except Exception:
            pass
def archive_history(model, max_dates=40, max_changes=80):
    """ИСТОРИЯ изделия из АРХИВА: срезы + правки.

    Возвращает (snaps, chgs):
      snaps — [(arch_date, файлов, макс.объём, ревизия, автор, Creo)] по датам срезов (`arch_snapshots`);
      chgs  — [(ts, descr)] правок `kind='архив'` из `changes`.
    Нет архива в базе → ([], []). Только чтение."""
    model = (model or "").strip()
    if not model:
        return [], []
    try:
        con = db_conn(ro=True)
    except Exception:
        return [], []
    snaps, chgs = [], []
    try:
        tabs = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "arch_snapshots" in tabs:
            for r in con.execute(
                    "SELECT arch_date, COUNT(*), MAX(volume), MAX(rev), MAX(author), MAX(creo) "
                    "FROM arch_snapshots WHERE UPPER(model)=UPPER(?) GROUP BY arch_date "
                    "ORDER BY arch_date LIMIT ?", (model, max_dates)):
                snaps.append(tuple(r))
        if "changes" in tabs:
            for r in con.execute(
                    "SELECT ts, descr FROM changes WHERE UPPER(item)=UPPER(?) AND kind='архив' "
                    "ORDER BY ts LIMIT ?", (model, max_changes)):
                chgs.append(tuple(r))
    except Exception:
        pass
    finally:
        try:
            con.close()
        except Exception:
            pass
    return snaps, chgs
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
def _model_paths(mstem, folder):
    """Файлы изделия по имени модели: сначала из базы, иначе — одноимённые рядом в папке."""
    try:
        con = eng.connect()
        paths = [r[0] for r in con.execute("SELECT path FROM snapshots WHERE model=?", (mstem,))]
        con.close()
        if paths:
            return paths
    except Exception:
        pass
    try:
        return [os.path.join(folder, f) for f in os.listdir(folder)
                if MODELFILE.search(f) and eng.stem(f) == mstem]
    except Exception:
        return []
def copy_source_keys(src_paths, settings):
    """Ключи (ревизия, дата, пользователь) по истории файлов ИСТОЧНИКА.

    Ключи берём ровно теми же строками, что печатает `history_rows`, — тогда сравнение
    записей копии с источником идёт один-в-один, без расхождений формата даты.
    """
    keys = set()
    for sp in src_paths:
        try:
            for r in history_rows(sp, settings):
                keys.add((r.get("Ревизия", ""), r.get("Дата", ""), r.get("Пользователь", "")))
        except Exception:
            pass
    return keys
def copy_source_of(paths, settings):
    """Источник копии по файлам изделия: (stem, src_paths, keys, found).

    «Модель скопирована от» лежит в самом файле (`from_mdl_name` → `to_mdl_name`). Источник
    выбираем по большинству голосов среди файлов изделия (у `.drw` имя в блоке бывает иным,
    поэтому голос чертежа не решает). Источник не найден/не прочитан → `found=False`, и записи
    НЕ помечаем (ничего не выдумываем).
    """
    self_stem = eng.stem(os.path.basename(paths[0])) if paths else ""
    by_type = {"model": {}, "drw": {}}
    for p in paths:
        mn = re.search(r"\.(prt|asm|drw)\.\d+$", os.path.basename(p), re.I)
        if not mn:
            continue
        try:
            raw = read_bytes(p, settings.get("max_size_mb", 0))
            if not raw:
                with open(p, "rb") as f:
                    raw = f.read(2_000_000)      # блок копии лежит в шапке файла
            cf = eng.copy_from_of(raw or b"")
        except Exception:
            cf = ""
        if not cf:
            continue
        st = eng.stem(cf)
        if not st or st == self_stem:
            continue                     # «скопирована от себя» — это НЕ копия (Creo пишет и такое)
        bucket = "model" if mn.group(1).lower() in ("prt", "asm") else "drw"
        by_type[bucket][st] = by_type[bucket].get(st, 0) + 1
    votes = by_type["model"]                          # решают ТОЛЬКО prt/asm: у чертежа имя копии бывает чужим
    if not votes:
        return "", [], set(), False
    src = max(votes, key=votes.get)
    folder = os.path.dirname(paths[0]) if paths else ""
    src_paths = _model_paths(src, folder)
    keys = copy_source_keys(src_paths, settings)
    return src, src_paths, keys, bool(keys)
def history_rows_copy_aware(path, settings):
    """`history_rows` + честная разметка копии: унаследованные записи получают имя ИСХОДНОГО файла.

    Нужна окну «История файла» (старое окно), чтобы оно не расходилось с вкладкой.
    """
    rows = history_rows(path, settings)
    if not rows:
        return rows
    base = os.path.basename(path)
    mstem = eng.stem(base)
    src, _sp, keys, found = copy_source_of(_model_paths(mstem, os.path.dirname(path)), settings)
    if not found:
        return rows
    own_suffix = base[len(mstem):] if base.upper().startswith(mstem) else ""
    src_name = (src + own_suffix) if own_suffix else base
    for r in rows:
        if (r.get("Ревизия", ""), r.get("Дата", ""), r.get("Пользователь", "")) in keys:
            r["Файл"] = src_name
    return rows
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
