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
import subprocess
import sys
import threading
import time

APP_VERSION = "V2"
APP_TITLE = "PLM Reader V2"
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scan_cache.json")


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
        tmp = CACHE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
        os.replace(tmp, CACHE_FILE)
    except Exception:
        pass


DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "plm_reader.db")


def db_conn():
    import sqlite3
    return sqlite3.connect(DB_FILE, timeout=15)


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
    try:
        c = db_conn()
        if folder:
            n = c.execute("SELECT COUNT(*) FROM snapshots WHERE folder LIKE ?",
                          (folder.rstrip("\\") + "%",)).fetchone()[0]
        else:
            n = c.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0]
        c.close()
        return n
    except Exception:
        return 0


def db_rows(folder=None, limit=2000):
    """Строки паспортов ИЗ БАЗЫ (файлы не читаются)."""
    try:
        c = db_conn()
        sql = ("SELECT path,volume,material,name,designation,rev,author,revdate,role "
               "FROM snapshots %s ORDER BY model, path LIMIT ?")
        if folder:
            cur = c.execute(sql % "WHERE folder LIKE ?",
                            (folder.rstrip("\\") + "%", limit))
        else:
            cur = c.execute(sql % "", (limit,))
        rows = []
        for p, volume, material, name, desig, rev, author, revdate, role in cur:
            rows.append({
                "Файл": os.path.basename(p), "Тип": "", "Обозначение": desig or "",
                "Наименование": name or "", "Материал": material or "",
                "Объём, мм³": ("%.0f" % volume) if volume else "", "Габарит, мм": "",
                "Роль": role or "", "Родитель": "", "Ревизия": rev or "",
                "Дата": revdate or "", "Пользователь": author or "",
                "Записей": "", "Версий": "", "Версия Creo": "", "_path": p,
            })
        c.close()
        return rows
    except Exception:
        return []
LOG_DIR = r"D:\AI\log\plm_reader"


def log_line(text):
    """Одна строка в общий лог инструмента: D:\\AI\\log\\plm_reader\\plm_reader.log."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "plm_reader.log"), "a", encoding="utf-8") as f:
            f.write("%s  %s\n" % (datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"), text))
    except Exception:
        pass

DEFAULT_SETTINGS = {
    "folder": "",
    "max_size_mb": 24,
    "recurse": True,
    "columns": ["Файл", "Обозначение", "Наименование", "Материал", "Объём, мм³",
                "Роль", "Родитель", "Ревизия", "Записей", "Версий", "Дата",
                "Пользователь", "Версия Creo"],
    "param_designation": ["ОБОЗНАЧЕНИЕ", "OBOZNACHENIE", "DESIGNATION", "DESIGNATOR", "PART_NUMBER"],
    "param_name": ["НАИМЕНОВАНИЕ", "NAME", "PART_NAME", "DESCRIPTION", "TITLE"],
    "param_material": ["PTC_MASTER_MATERIAL", "MATERIAL", "МАТЕРИАЛ"],
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
              "Пользователь": 100, "Версия Creo": 110, "Файл": 215}


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
    """Подходит ли строка под фильтр: подстрока без учёта регистра по показанным столбцам."""
    pat = (pattern or "").strip().lower()
    if not pat:
        return True
    return pat in " ".join(str(row.get(c, "")) for c in cols).lower()


def first_param(par, keys):
    """Первое найденное значение из списка имён параметров (проверка без учёта регистра имени)."""
    for k in keys:
        if par.get(k):
            return par[k]
    upper = {str(k).upper(): v for k, v in par.items()}
    for k in keys:
        if upper.get(str(k).upper()):
            return upper[str(k).upper()]
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
    cache = load_cache()                      # ПОВТОРНЫЙ скан не читает неизменённое
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
            r = old.get("row")                # НЕ изменился — берём из кэша, файл НЕ читаем
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

    win = tk.Toplevel(parent)
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

    settings = dict(DEFAULT_SETTINGS)
    if os.path.isfile(SETTINGS_FILE):
        try:
            settings.update(json.load(open(SETTINGS_FILE, encoding="utf-8")))
        except Exception:
            pass

    root = tk.Tk()
    root.title(APP_TITLE)
    root.geometry("1330x660")
    root.minsize(760, 420)            # три уровня видны и в небольшом окне

    top = ttk.LabelFrame(root, text=" 1. НАСТРОЙКИ ", padding=6)
    top.pack(fill="x", padx=6, pady=(6, 4))
    ttk.Label(top, text="Папка:").pack(side="left")
    e_folder = ttk.Entry(top, width=68)
    e_folder.insert(0, settings.get("folder", ""))
    e_folder.pack(side="left", padx=4)

    def pick():
        d = filedialog.askdirectory(initialdir=e_folder.get() or os.path.expanduser("~"))
        if d:
            e_folder.delete(0, "end")
            e_folder.insert(0, d)

    ttk.Button(top, text="Выбрать…", command=pick).pack(side="left")

    ttk.Label(top, text="Пропускать > МБ:").pack(side="left", padx=(10, 2))
    e_max = ttk.Entry(top, width=5)
    e_max.insert(0, str(settings.get("max_size_mb", 24)))
    e_max.pack(side="left")
    var_rec = tk.BooleanVar(value=settings.get("recurse", True))
    ttk.Checkbutton(top, text="с подпапками", variable=var_rec).pack(side="left", padx=8)
    var_lat = tk.BooleanVar(value=settings.get("latest_only", True))
    ttk.Checkbutton(top, text="только последние версии", variable=var_lat).pack(side="left", padx=8)

    mid = ttk.LabelFrame(root, text=" 2. ИНСТРУМЕНТЫ ", padding=6)
    mid.pack(fill="x", padx=6, pady=(0, 4))
    btn = ttk.Button(mid, text="Сканировать")
    btn.pack(side="left")

    def stop_scan():
        root._plm_stop = True
        lbl.config(text="останавливаю…")

    b_stop = ttk.Button(mid, text="Стоп", command=stop_scan, state="disabled")
    b_stop.pack(side="left", padx=(8, 0))
    ttk.Button(mid, text="Актуально?", command=lambda: check_base()).pack(side="left", padx=(8, 0))
    ttk.Button(mid, text="README", command=lambda: show_readme()).pack(side="left", padx=(8, 0))
    ttk.Button(mid, text="Выгрузить в CSV", command=lambda: export()).pack(side="left", padx=8)
    ttk.Button(mid, text="Столбцы и параметры…", command=lambda: choose_columns()).pack(side="left", padx=(0, 8))
    ttk.Button(mid, text="История выбранного", command=lambda: show_history()).pack(side="left", padx=8)
    ttk.Button(mid, text="История по папке", command=lambda: show_folder_history()).pack(side="left", padx=8)
    def open_plm():
        import engine_gui as _eg
        _eg.App(tk.Toplevel(root))
    ttk.Button(mid, text="🌳 ПЛМ (дерево/входимость/изменения)", command=open_plm).pack(side="left", padx=8)

    data = ttk.LabelFrame(root, text=" 3. ДАННЫЕ ", padding=6)
    data.pack(fill="x", padx=6, pady=(0, 4))
    lbl = ttk.Label(data, text="готов", anchor="w", justify="left")
    lbl.pack(fill="x")

    def _wrap_data(event=None):
        try:
            lbl.config(wraplength=max(240, root.winfo_width() - 80))   # текст не пропадает в узком окне
        except Exception:
            pass

    root.bind("<Configure>", _wrap_data)

    flt = ttk.Frame(root, padding=(6, 4))
    flt.pack(fill="x")
    ttk.Label(flt, text="Фильтр:").pack(side="left")
    e_filter = ttk.Entry(flt, width=44)
    e_filter.pack(side="left", padx=4)
    ttk.Label(flt, text="часть текста; пусто — показать всё").pack(side="left")
    ttk.Button(flt, text="Сбросить", command=lambda: (e_filter.delete(0, "end"), redraw())).pack(side="left", padx=8)
    e_filter.bind("<KeyRelease>", lambda e: redraw())

    cols = list(settings.get("columns", DEFAULT_SETTINGS["columns"]))
    if "Версий" not in cols:
        cols.append("Версий")
    if "Файл" in cols:
        cols = ["Файл"] + [c for c in cols if c != "Файл"]
    sort_state = {"col": "Файл", "desc": False}
    rows_all, shown = [], []

    body = ttk.Frame(root)
    body.pack(fill="both", expand=True, padx=6, pady=(0, 6))
    body.rowconfigure(0, weight=1)
    body.columnconfigure(0, weight=1)

    def make_tree():
        tv = ttk.Treeview(body, columns=cols, show="headings", height=20)
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
        return (0, str(v).lower())

    def set_sort(col):
        if sort_state["col"] == col:
            sort_state["desc"] = not sort_state["desc"]
        else:
            sort_state["col"], sort_state["desc"] = col, False
        redraw()

    def redraw():
        pat = e_filter.get().strip().lower()
        rows = [r for r in rows_all if match_filter(r, cols, pat)]
        rows.sort(key=lambda r: sort_key(r, sort_state["col"]), reverse=sort_state["desc"])
        shown[:] = rows
        tree.delete(*tree.get_children())
        for r in rows:
            tree.insert("", "end", values=[r.get(c, "") for c in cols])
        for c in cols:
            mark = "  ▼" if (sort_state["col"] == c and sort_state["desc"]) else \
                   ("  ▲" if sort_state["col"] == c else "")
            tree.heading(c, text=c + mark)
        lbl.config(text="показано %d из %d" % (len(rows), len(rows_all)))

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

    root._plm = {"redraw": redraw, "rebuild": rebuild_tree, "tree": lambda: tree}   # для самопроверки

    def show_readme():
        try:
            with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "README.md"),
                      "r", encoding="utf-8") as f:
                text = f.read()
        except Exception as e:
            lbl.config(text="README не прочитан: %s" % e)
            return
        win = tk.Toplevel(root)
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
                r = eng.do_check()
            except Exception as e:
                root.after(0, lambda: lbl.config(text="проверка не удалась: %s" % e))
                return
            root.after(0, lambda: show_check(r))

        threading.Thread(target=work, daemon=True).start()

    def show_check(r):
        if r.get("need"):
            lbl.config(text="НУЖЕН СКАН: новых %d · изменённых %d · пропало %d (%.1f с)"
                       % (r["new"], r["changed"], r["gone"], r["secs"]))
        else:
            lbl.config(text="БАЗА АКТУАЛЬНА: файлов %d, изменений нет (%.1f с)"
                       % (r["total"], r["secs"]))
        log_line("check: %s" % r.get("verdict", ""))

    def load_base(limit=2000):
        """Показать базу БЕЗ чтения файлов: строки паспортов из plm_reader.db."""
        folder = norm_path(e_folder.get()) if e_folder.get().strip() else ""
        rows_all.clear()
        tree.delete(*tree.get_children())
        rows_all.extend(db_rows(folder or None, limit))
        redraw()
        tot = db_total(folder or None)
        lbl.config(text="из базы: показано %d из %d (папка %s)"
                   % (len(rows_all), tot, folder or "вся база"))
        log_line("base: показано %d из %d (папка %s)" % (len(rows_all), tot, folder or "вся база"))

    ALL_FIELDS = ["Файл", "Обозначение", "Наименование", "Материал", "Объём, мм³", "Тип",
                  "Роль", "Родитель", "Записей", "Версий", "Ревизия", "Дата", "Пользователь",
                  "Версия Creo", "Габарит, мм"]

    def save_settings():
        try:
            json.dump(settings, open(SETTINGS_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        except Exception:
            pass

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
        ttk.Label(win, text="Список проверяется по порядку — берётся первый найденный параметр. "
                            "Так подойдут любые имена, в т.ч. английские.").pack(anchor="w", padx=8, pady=(0, 8))

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
        row = rows_all[tree.index(items[0])]
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
                        tree.insert("", "end", values=[r.get(c, "") for c in cols])
                elif msg[0] == "walk":
                    _secs = time.time() - getattr(root, "_plm_t0", time.time())
                    lbl.config(text="ищу файлы: найдено %d%s (%.0f с)"
                               % (msg[1], " — обход готов, читаю изменённое…" if msg[2] else "", _secs))
                elif msg[0] == "prog":
                    _secs = time.time() - getattr(root, "_plm_t0", time.time())
                    lbl.config(text="%d / %d · прочитано %d, из кэша %d · %.0f с · %s"
                               % (msg[1], msg[2], msg[4], msg[5], _secs, msg[3][:40]))
                else:
                    redraw()
                    _secs = time.time() - getattr(root, "_plm_t0", time.time())
                    st = msg[2] if len(msg) > 2 else {}
                    lbl.config(text="готово: %d моделей за %.1f с (прочитано %d, из кэша %d)%s"
                               % (msg[1], _secs, st.get("read", 0), st.get("cache", 0),
                                  "; ОСТАНОВЛЕНО" if st.get("stopped") else ""))
                    log_line("scan: %s -> моделей %d за %.1f с (прочитано %d, из кэша %d)"
                             % (e_folder.get(), msg[1], _secs, st.get("read", 0), st.get("cache", 0)))
                    btn.config(state="normal")
                    b_stop.config(state="disabled")
                    return
        except queue.Empty:
            pass
        root.after(120, poll_scan)

    def worker(folder, opts):
        stats = {}

        def prog(i, total, p):
            q.put(("prog", i, total, os.path.basename(p),
                   stats.get("read", 0), stats.get("cache", 0)))

        rows = scan_folder(folder, opts, prog, lambda r: q.put(("row", r)),
                           stop_cb=lambda: getattr(root, "_plm_stop", False), stats=stats,
                           walk_cb=lambda n, done=False: q.put(("walk", n, done)))
        q.put(("done", len(rows), stats))

    def go():
        folder = norm_path(e_folder.get())
        if not os.path.isdir(folder):
            messagebox.showwarning(APP_TITLE, "Выберите папку.")
            return
        e_folder.delete(0, "end")
        e_folder.insert(0, folder)
        tree.delete(*tree.get_children())
        rows_all.clear()
        opts = {"max_size_mb": float(e_max.get() or 0), "recurse": var_rec.get(),
                "latest_only": var_lat.get()}
        btn.config(state="disabled")
        b_stop.config(state="normal")
        root._plm_stop = False
        root._plm_t0 = time.time()
        lbl.config(text="поиск файлов…")
        settings.update({"folder": folder, "max_size_mb": opts["max_size_mb"],
                         "recurse": opts["recurse"], "latest_only": opts["latest_only"]})
        save_settings()
        threading.Thread(target=worker, args=(folder, opts), daemon=True).start()
        root.after(120, poll_scan)

    def export():
        if not rows_all:
            return
        p = filedialog.asksaveasfilename(defaultextension=".csv", initialfile="plm_items.csv",
                                         filetypes=[("CSV", "*.csv")])
        if p:
            save_csv(shown or rows_all, p)
            lbl.config(text="выгружено: %s" % os.path.basename(p))

    btn.config(command=go)
    _bs = db_summary()
    log_line("base: файлов %d, моделей %d, связей %d, папок %d, изменений %d"
             % (_bs.get("files", 0), _bs.get("models", 0), _bs.get("links", 0),
                _bs.get("folders", 0), _bs.get("changes", 0)))
    if _bs.get("files"):
        lbl.config(text="база: файлов %d · моделей %d · изменений %d — читаю из базы…"
                   % (_bs.get("files", 0), _bs.get("models", 0), _bs.get("changes", 0)))
        load_base()
        check_base()
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

