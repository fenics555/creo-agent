# -*- coding: utf-8 -*-
r"""plm_tree V1 — ПЛМ «в лоб»: паспорт изделий, дерево производства, входимость и ИЗМЕНЕНИЯ.

Creo не нужен. Своя база лежит РЯДОМ с инструментом (`plm_tree.db`) — легко перенести на другую машину.

CLI:
  python plm_tree.py scan [--roots П1 П2] [--limit СЕК]
  python plm_tree.py where МОДЕЛЬ        (в каких сборках и сколько раз)
  python plm_tree.py changes [--n 40]    (журнал изменений: кто/когда/что)
"""
import argparse
import datetime
import json
import os
import re
import sqlite3
import struct
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))     # общая библиотека дома (creo_read)
DB = os.environ.get("PLM_DB") or os.path.join(HERE, "plm_reader.db")   # своя база: PLM_DB=путь\другая.db
LOG = r"D:\AI\log\plm_reader\engine.log"
DEFAULT_ROOTS = [r"Z:\PTC\Work"]
MODEL = re.compile(r"\.(prt|asm|drw)\.\d+$", re.IGNORECASE)
VERSION = "V1"


def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("%s  %s\n" % (datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"), msg))
    except Exception:
        pass


def stem(name):
    n = name.upper()
    for ext in (".PRT", ".ASM", ".DRW", ".NEU", ".SEC", ".M_P", ".PRT.", ".ASM."):
        if ext in n:
            n = n.split(ext)[0]
            break
    return re.sub(r"\.\d+$", "", n)


def parse_toc(raw):
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


def real(raw, key):
    m = re.search(rb"\xe0\x02" + key.encode() + rb"\x00\xed", raw)
    if not m or m.end() + 8 > len(raw):
        return None
    try:
        return struct.unpack(">d", raw[m.end():m.end() + 8])[0]
    except Exception:
        return None


def params(raw, toc):
    out = {}
    if "NeuPrtSld" not in toc:
        return out
    off, ln = toc["NeuPrtSld"][0], toc["NeuPrtSld"][1]
    for m in re.finditer(rb"([\x20-\xff]{3,32})\x00\xe2\x33(.{0,60}?)\x00", raw[off:off + ln], re.S):
        t = re.search(r"[\w]+$", m.group(1).decode("utf-8", "replace"))
        try:
            v = m.group(2).decode("utf-8")
        except UnicodeDecodeError:
            continue
        if t and v and "\x00" not in v:
            out.setdefault(t.group(0), " ".join(v.split()))
    return out


def role(raw):
    if b"MERGE_BASE_PART" in raw:
        m = re.search(rb"MERGE_BASE_PART.{0,80}?([A-Za-z0-9_\-]{5,40})\x00", raw, re.S)
        return "nasled." + (m.group(1).decode("latin-1") if m else "?")
    for m in re.finditer(rb"ref_part_tab\x00", raw):
        nm = re.search(rb"name\x00([A-Za-z0-9_\-\.]{4,47})\x00", raw[m.end():m.end() + 200])
        if nm:
            return "proizv." + nm.group(1).decode("latin-1")
    return ""


TAIL = re.compile(rb"\xf7(.)\xe3([0-9]{1,7})\x00\x00(.{0,220}?)\x00((?:Creo )?[0-9][0-9.]*)\x00", re.S)
STAMP = re.compile(rb"\xf7\x14([\x20-\x7e\xc0-\xff]{1,24}?)\x00\xe2(.)(.)(.)(.)(.)(.)", re.S)
NAME_B = re.compile(rb"[\x00-\x1f\x80-\xff]([A-Za-z0-9][A-Za-z0-9_\-\.]{3,47}\.(?:PRT|ASM))",
                    re.IGNORECASE)


def user_time(raw):
    out = []
    for m in STAMP.finditer(raw):
        s, mi, h, d, mo, y = (b[0] for b in m.groups()[1:])
        try:
            dt = datetime.datetime(1900 + y, mo + 1, d, h, mi, s)
        except ValueError:
            continue
        if 1990 <= dt.year <= 2030:
            try:
                who = m.group(1).decode("utf-8")
            except UnicodeDecodeError:
                who = m.group(1).decode("cp1251", "replace")
            out.append((m.start(), who, dt))
    return sorted(set(out))


def last_hist(raw):
    st, last = user_time(raw), None
    for t in TAIL.finditer(raw):
        prev = [s for s in st if s[0] < t.start()]
        last = (t.group(2).decode(), prev[-1][1] if prev else "",
                prev[-1][2].strftime("%d.%m.%y %H:%M") if prev else "")
    return last


def names(raw):
    """Имена моделей внутри файла (расширение срезано) и сколько раз встречаются."""
    c = Counter()
    for m in NAME_B.finditer(raw):
        c[stem(m.group(1).decode("latin-1"))] += 1
    return c


def collect(roots, max_mb, max_depth=None):
    """ВСЕ файлы моделей рекурсивно (ключ — путь). max_depth — предел вложенности (None = без предела)."""
    files = []
    for root in roots:
        root = os.path.abspath(root)
        if not os.path.isdir(root):
            continue
        for dp, dirs, fs in os.walk(root):
            rel = os.path.relpath(dp, root)
            d = 0 if rel == "." else rel.count(os.sep) + 1
            if max_depth is not None and d > max_depth:
                dirs[:] = []
                continue
            try:
                for f in sorted(fs):
                    if MODEL.search(f):
                        p = os.path.join(dp, f)
                        if os.path.getsize(p) <= max_mb * 1_000_000:
                            files.append(p)
            except Exception:
                pass
    return files


def scan_item(s, path, stems, fstems=frozenset()):
    raw = open(path, "rb").read()
    pr = params(raw, parse_toc(raw))
    vol = real(raw, "volume") or real(raw, "mtrl_volume")
    nm = names(raw)
    refs = {c: nm[c] for c in nm if c != s and c in stems and len(c) >= 5}
    h = last_hist(raw) or ("", "", "")
    return {"model": s, "path": path, "size": len(raw), "mtime": os.path.getmtime(path),
            "volume": vol or 0.0, "material": pr.get("PTC_MASTER_MATERIAL") or "",
            "name": pr.get("\u041d\u0410\u0418\u041c\u0415\u041d\u041e\u0412\u0410\u041d\u0418\u0415") or "",
            "designation": pr.get("\u041e\u0411\u041e\u0417\u041d\u0410\u0427\u0415\u041d\u0418\u0415") or "",
            "rev": h[0], "author": h[1], "revdate": h[2], "role": role(raw, fstems, s), "refs": refs}


# --- ЕДИНЫЙ ЧИТАТЕЛЬ из общей библиотеки дома (локальные копии выше — к удалению) ---
import creo_read as _CR  # noqa: E402

stem = _CR.stem
parse_toc = _CR.parse_toc
real = _CR.real
params = _CR.params
role = _CR.role
user_time = _CR.user_time
last_hist = _CR.last_hist
names = _CR.names

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
  path TEXT PRIMARY KEY, model TEXT, folder TEXT, size INTEGER, mtime REAL, volume REAL,
  material TEXT, name TEXT, designation TEXT, rev TEXT, author TEXT, revdate TEXT,
  role TEXT, seen TEXT);
CREATE TABLE IF NOT EXISTS changes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, rev TEXT, kind TEXT, descr TEXT,
  who TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS links (parent TEXT, child TEXT, qty INTEGER, source TEXT);
CREATE INDEX IF NOT EXISTS ix_links_child ON links(child);
CREATE TABLE IF NOT EXISTS folders (path TEXT PRIMARY KEY, parent TEXT, depth INTEGER,
  models INTEGER, files INTEGER, seen TEXT);
"""


def connect():
    con = sqlite3.connect(DB, timeout=30)
    # миграция 25.09.2026: старый ключ (model) → ключ по ПУТИ; старые snapshots/links пересоздаём
    try:
        cols = [r[1] for r in con.execute("PRAGMA table_info(snapshots)")]
        if cols and "folder" not in cols:
            con.execute("DROP TABLE snapshots")
            con.execute("DROP TABLE links")
            con.commit()
    except Exception:
        pass
    con.executescript(SCHEMA)
    con.commit()
    return con


def inventory(roots, max_mb=8, store=True, max_depth=None):
    """СТРОЕНИЕ СКЛАДА (быстро, секунды): папки/подпапки, файлы, модели — и сразу в базу `folders`."""
    t0 = time.time()
    rows, folders, files, models = [], 0, 0, 0
    for root in roots:
        root = os.path.abspath(root)
        if not os.path.isdir(root):
            continue
        for dp, dirs, fs in os.walk(root):
            rel0 = os.path.relpath(dp, root)
            d0 = 0 if rel0 == "." else rel0.count(os.sep) + 1
            if max_depth is not None and d0 > max_depth:
                dirs[:] = []
                continue
            folders += 1
            rel = os.path.relpath(dp, root)
            depth = 0 if rel == "." else rel.count(os.sep) + 1
            m = sum(1 for f in fs if MODEL.search(f))
            models += m
            files += len(fs)
            rows.append((dp, os.path.dirname(dp), depth, m, len(fs)))
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if store:
        con = connect()
        con.execute("DELETE FROM folders")
        con.executemany("INSERT INTO folders (path,parent,depth,models,files,seen) VALUES (?,?,?,?,?,?)",
                        [(r[0], r[1], r[2], r[3], r[4], now) for r in rows])
        con.commit()
        con.close()
    print("строение: папок %d, файлов %d, моделей %d (за %.1f с)%s"
          % (folders, files, models, time.time() - t0, " → в базу folders" if store else ""),
          flush=True)
    return folders, files


def do_scan(roots, max_mb, limit, depth=None, progress_cb=None, stop_cb=None):
    t0 = time.time()
    files = collect(roots, max_mb, depth)
    total = len(files)
    codes = {stem(os.path.basename(p)) for p in files}
    fstems = defaultdict(set)
    for p in files:
        fstems[os.path.dirname(p)].add(stem(os.path.basename(p)))
    con = connect()
    prev = {r[0]: r for r in con.execute(
        "SELECT path,volume,material,name,designation,rev,author,revdate,role,size,mtime FROM snapshots")}
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    done = new = mod = skipped = 0
    seen = set()
    n = 0
    stopped = False
    for path in sorted(files):
        if time.time() - t0 > limit:
            break
        if stop_cb and stop_cb():
            stopped = True
            break
        n += 1
        s = stem(os.path.basename(path))
        try:
            st = os.stat(path)
        except OSError:
            continue
        old = prev.get(path)
        if old and int(old[9] or 0) == st.st_size and abs(float(old[10] or 0) - st.st_mtime) < 1.0:
            skipped += 1                     # НЕ изменился (размер+время) — НЕ читаем и не трогаем
            if progress_cb and n % 25 == 0:
                progress_cb(n, total)
            continue
        try:
            it = scan_item(s, path, codes, fstems.get(os.path.dirname(path), set()))
        except Exception as e:
            log("ERROR %s: %s" % (path, e))
            continue
        diffs = []
        if old:
            if abs(float(old[1] or 0) - float(it["volume"] or 0)) >= 0.5:
                diffs.append("объём %d→%d" % (old[1] or 0, it["volume"] or 0))
            for key, idx in (("material", 2), ("name", 3), ("designation", 4),
                             ("rev", 5), ("author", 6), ("revdate", 7), ("role", 8)):
                a, b = old[idx] or "", it[key]
                if str(a) != str(b):
                    diffs.append("%s: %s→%s" % (key, a or "-", b or "-"))
            if diffs:
                con.execute("INSERT INTO changes (item,rev,kind,descr,who,ts) VALUES (?,?,?,?,?,?)",
                            (path, it["rev"], "modify", "; ".join(diffs), it["author"], now))
                mod += 1
        else:
            con.execute("INSERT INTO changes (item,rev,kind,descr,who,ts) VALUES (?,?,?,?,?,?)",
                        (path, it["rev"], "new", "первая запись паспорта", it["author"], now))
            new += 1
        con.execute("INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (it["path"], it["model"], os.path.dirname(path), it["size"], it["mtime"],
                     it["volume"], it["material"], it["name"], it["designation"], it["rev"],
                     it["author"], it["revdate"], it["role"], now))
        if s not in seen:                       # связи код-родителя чистим ОДИН раз
            con.execute("DELETE FROM links WHERE parent=? AND source='plm_tree'", (s,))
            seen.add(s)
        for child, qty in it["refs"].items():
            if (s, child) in seen:
                continue
            seen.add((s, child))
            con.execute("INSERT INTO links VALUES (?,?,?,?)", (s, child, qty, "plm_tree"))
        done += 1
        if progress_cb and n % 25 == 0:
            progress_cb(n, total)
        if n % 500 == 0:
            con.commit()            # частичный коммит: база не заперта на весь прогон
            _p = "progress: %d/%d (%.0f%%), %.1f s, изменённых %d" % (
                n, total, 100.0 * n / max(total, 1), time.time() - t0, mod)
            print(_p, flush=True)
            log(_p)
    try:                        # корни скана — чтобы «проверка актуальности» знала, что обходить
        con.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
        con.execute("INSERT OR REPLACE INTO meta VALUES ('roots', ?)", (json.dumps(roots),))
    except Exception:
        pass
    con.commit()
    con.close()
    dt = time.time() - t0
    log("scan: файлов %d, новых %d, изменённых %d, пропущено %d, за %.1f с"
        % (done, new, mod, skipped, dt))
    print("scan: обработано %d из %d | новых %d | изменённых %d | пропущено (без изменений) %d | за %.1f с%s | база %s"
          % (done, total, new, mod, skipped, dt, " | ОСТАНОВЛЕНО" if stopped else "", DB))


def summary():
    """Сколько чего в базе (для окна при старте)."""
    out = {}
    try:
        con = connect()
        for t in ("snapshots", "links", "folders", "changes"):
            try:
                out[t] = con.execute("SELECT COUNT(*) FROM " + t).fetchone()[0]
            except Exception:
                out[t] = 0
        try:
            out["models"] = con.execute("SELECT COUNT(DISTINCT model) FROM snapshots").fetchone()[0]
        except Exception:
            out["models"] = 0
        con.close()
    except Exception:
        out = {}
    return out


def meta_set(k, v):
    con = connect()
    con.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
    con.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (k, v))
    con.commit()
    con.close()


def meta_get(k, default=None):
    try:
        con = connect()
        r = con.execute("SELECT v FROM meta WHERE k=?", (k,)).fetchone()
        con.close()
        return r[0] if r else default
    except Exception:
        return default


def do_check(roots=None, max_mb=8.0, depth=None):
    """БЫСТРАЯ проверка актуальности базы: обход + stat, БЕЗ чтения файлов.

    Отвечает на вопрос владельца «актуально / нужен скан?».
    """
    t0 = time.time()
    if not roots:
        try:
            roots = json.loads(meta_get("roots") or "null") or DEFAULT_ROOTS
        except Exception:
            roots = DEFAULT_ROOTS
    files = collect(roots, max_mb, depth)
    con = connect()
    prev = {r[0]: (r[1], r[2]) for r in con.execute("SELECT path,size,mtime FROM snapshots")}
    con.close()
    found, new, changed, same = set(), 0, 0, 0
    for p in files:
        found.add(p)
        try:
            st = os.stat(p)
        except OSError:
            continue
        old = prev.get(p)
        if old is None:
            new += 1
        elif int(old[0] or 0) == st.st_size and abs(float(old[1] or 0) - st.st_mtime) < 1.0:
            same += 1
        else:
            changed += 1
    gone = len(set(prev) - found)
    need = bool(new or changed or gone)
    verdict = ("НУЖЕН СКАН: новых %d, изменённых %d, пропало %d" % (new, changed, gone)) if need \
        else "АКТУАЛЬНО (скан не нужен)"
    res = {"total": len(files), "same": same, "new": new, "changed": changed, "gone": gone,
           "need": need, "verdict": verdict, "secs": round(time.time() - t0, 1)}
    msg = ("проверка: файлов %d | без изменений %d | новых %d | изменённых %d | пропало %d"
           " | за %.1f с → %s" % (res["total"], same, new, changed, gone, res["secs"], verdict))
    print(msg, flush=True)
    log(msg)
    return res


def do_where(model):
    con = connect()
    rows = con.execute("SELECT parent, qty FROM links WHERE child=? ORDER BY qty DESC",
                       (stem(model),)).fetchall()
    con.close()
    print("«%s» входит в %d сборок:" % (stem(model), len(rows)))
    for par, qty in rows:
        print("   %-42s x%d" % (par, qty))


def do_changes(n):
    con = connect()
    rows = con.execute("SELECT ts, item, rev, kind, descr, who FROM changes ORDER BY id DESC LIMIT ?",
                       (n,)).fetchall()
    con.close()
    print("последние изменения (%d):" % len(rows))
    for ts, item, rev, kind, descr, who in rows:
        print("   %s  %-30s rev%-8s %-7s %s" % (ts, item, rev, kind, descr[:70]))


def do_tree(model, depth):
    con = connect()
    kids, parents = defaultdict(list), set()
    for par, ch, qty in con.execute("SELECT parent, child, qty FROM links"):
        kids[par].append((ch, qty))
        parents.add(ch)
    snap = {r[0]: r for r in con.execute("SELECT model, name, volume, rev FROM snapshots")}
    con.close()

    def lab(m):
        r = snap.get(m)
        if not r:
            return m
        nm = ("  «%s»" % r[1]) if r[1] else ""
        vol = ("  %.0f мм³" % r[2]) if r[2] else ""
        rv = ("  rev%s" % r[3]) if r[3] else ""
        return "%s%s%s%s" % (m, nm, vol, rv)

    tops = [stem(model)] if model else sorted(m for m in snap if m not in parents)
    print("ДЕРЕВО ПРОИЗВОДСТВА: моделей %d, связей %d%s"
          % (len(snap), sum(len(v) for v in kids.values()),
             ("  (корень: %s)" % stem(model)) if model else ""))
    seen = set()

    def walk(m, pref, last, d):
        if d > depth:
            return
        print("%s%s%s" % (pref, "└─ " if last else "├─ ", lab(m)))
        if m in seen:
            print("%s   ⋯ (уже показано выше)" % pref)
            return
        seen.add(m)
        ch = kids.get(m, [])
        for i, (c, q) in enumerate(ch):
            walk(c, pref + ("   " if last else "│  "), i == len(ch) - 1, d + 1)

    shown = tops[:60]
    for i, t in enumerate(shown):
        walk(t, "", i == len(shown) - 1, 1)
        print()


def do_rename_plan(old, new):
    """СУХОЙ ПРОГОН переименования: модель + чертёж + все сборки-владельцы + порядок сохранения."""
    o = stem(old)
    n = stem(new) if new else ""
    con = connect()
    snap = {r[0] for r in con.execute("SELECT model FROM snapshots")}
    parents = defaultdict(set)
    for par, ch in con.execute("SELECT parent, child FROM links"):
        parents[ch].add(par)
    con.close()
    if not n:
        print("нужно: rename-plan СТАРОЕ_ИМЯ НОВОЕ_ИМЯ")
        return
    seen, order, stack = set(), [], list(parents.get(o, ()))
    while stack:
        p = stack.pop()
        if p in seen:
            continue
        seen.add(p)
        order.append(p)
        stack.extend(parents.get(p, ()))
    print("ПЛАН ПЕРЕИМЕНОВАНИЯ (сухой прогон, Creo не нужен) — по скиллу creoson_rename_mechanism")
    print("  было : %s  (модель/деталь или сборка)" % o)
    print("  станет: %s" % n)
    print("  чертёж: %s.drw  (%s)" % (o, "есть в базе" if o in snap else "в базе не виден"))
    print("  сборок-владельцев: %d" % len(order))
    for i, p in enumerate(order, 1):
        print("    %2d. %s" % (i, p))
    print("  ПОРЯДОК:")
    print("   1) загрузить (display:false): модель, её чертёж, ВСЕ сборки-владельцы;")
    print("   2) file:rename {file: %s, new_name: %s, onlysession:true}   (модель)" % (o, n))
    print("   3) file:rename {file: %s.drw, new_name: %s.drw, onlysession:true} + drawing:regenerate" % (o, n))
    print("   4) save СНИЗУ ВВЕРХ: модель → сборки-владельцы → ЧЕРТЁЖ ПОСЛЕДНИМ;")
    print("   5) старые версии %s.* — в backup (не удалять); 6) file:erase всех загруженных." % o)
    print("  ИСПОЛНЕНИЕ — только при запущенном Creo (CREO-START) + CREOSON, под щитом согласования.")


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="plm_tree " + VERSION)
    ap.add_argument("cmd", choices=["scan", "check", "count", "where", "changes", "tree", "rename-plan"])
    ap.add_argument("model", nargs="?")
    ap.add_argument("new", nargs="?")
    ap.add_argument("--roots", nargs="+", default=DEFAULT_ROOTS)
    ap.add_argument("--limit", type=float, default=120.0)
    ap.add_argument("--max-mb", type=float, default=8.0)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--depth", type=int, default=4)
    ap.add_argument("--max-depth", type=int, default=0)
    a = ap.parse_args()
    if a.cmd == "scan":
        do_scan(a.roots, a.max_mb, a.limit, (a.max_depth or None))
    elif a.cmd == "check":
        do_check(a.roots if a.roots != DEFAULT_ROOTS else None, a.max_mb, (a.max_depth or None))
    elif a.cmd == "count":
        inventory(a.roots, a.max_mb, max_depth=(a.max_depth or None))
    elif a.cmd == "where":
        do_where(a.model or "")
    elif a.cmd == "tree":
        do_tree(a.model, a.depth)
    elif a.cmd == "rename-plan":
        do_rename_plan(a.model or "", a.new or "")
    else:
        do_changes(a.n)


if __name__ == "__main__":
    main()


