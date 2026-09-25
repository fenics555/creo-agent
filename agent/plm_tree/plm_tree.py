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
import os
import re
import sqlite3
import struct
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "plm_tree.db")
LOG = r"D:\AI\log\plm_tree\plm_tree.log"
DEFAULT_ROOTS = [r"Z:\PTC\Work\000_51 DF Держатели форм",
                 r"Z:\PTC\Work\000_03 401-LIT Литейное производство"]
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


def collect(roots, max_mb):
    paths = {}
    for root in roots:
        if not os.path.isdir(root):
            continue
        folders = [root] + [os.path.join(root, d) for d in sorted(os.listdir(root))
                            if os.path.isdir(os.path.join(root, d))]
        for folder in folders:
            try:
                for f in sorted(os.listdir(folder)):
                    if MODEL.search(f):
                        p = os.path.join(folder, f)
                        if os.path.getsize(p) <= max_mb * 1_000_000:
                            paths.setdefault(stem(f), p)
            except Exception:
                pass
    return paths


def scan_item(s, path, stems):
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
            "rev": h[0], "author": h[1], "revdate": h[2], "role": role(raw), "refs": refs}


SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
  model TEXT PRIMARY KEY, path TEXT, size INTEGER, mtime REAL, volume REAL,
  material TEXT, name TEXT, designation TEXT, rev TEXT, author TEXT, revdate TEXT,
  role TEXT, seen TEXT);
CREATE TABLE IF NOT EXISTS changes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, rev TEXT, kind TEXT, descr TEXT,
  who TEXT, ts TEXT);
CREATE TABLE IF NOT EXISTS links (parent TEXT, child TEXT, qty INTEGER, source TEXT);
CREATE INDEX IF NOT EXISTS ix_links_child ON links(child);
"""


def connect():
    con = sqlite3.connect(DB, timeout=30)
    con.executescript(SCHEMA)
    con.commit()
    return con


def do_scan(roots, max_mb, limit):
    t0 = time.time()
    paths = collect(roots, max_mb)
    stems = set(paths)
    con = connect()
    prev = {r[0]: r for r in con.execute(
        "SELECT model,volume,material,name,designation,rev,author,revdate,role,size FROM snapshots")}
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    done = new = mod = 0
    con.execute("DELETE FROM links WHERE source='plm_tree'")
    for s, p in sorted(paths.items()):
        if time.time() - t0 > limit:
            break
        try:
            it = scan_item(s, p, stems)
        except Exception as e:
            log("ERROR %s: %s" % (s, e))
            continue
        old = prev.get(s)
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
                            (s, it["rev"], "modify", "; ".join(diffs), it["author"], now))
                mod += 1
        else:
            con.execute("INSERT INTO changes (item,rev,kind,descr,who,ts) VALUES (?,?,?,?,?,?)",
                        (s, it["rev"], "new", "первая запись паспорта", it["author"], now))
            new += 1
        con.execute("INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (s, it["path"], it["size"], it["mtime"], it["volume"], it["material"],
                     it["name"], it["designation"], it["rev"], it["author"], it["revdate"],
                     it["role"], now))
        for child, qty in it["refs"].items():
            con.execute("INSERT INTO links VALUES (?,?,?,?)", (s, child, qty, "plm_tree"))
        done += 1
    con.commit()
    con.close()
    dt = time.time() - t0
    log("scan: моделей %d, новых %d, изменённых %d, за %.1f с" % (done, new, mod, dt))
    print("scan: обработано %d из %d | новых %d | изменённых %d | за %.1f с | база %s"
          % (done, len(paths), new, mod, dt, DB))


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


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="plm_tree " + VERSION)
    ap.add_argument("cmd", choices=["scan", "where", "changes", "tree"])
    ap.add_argument("model", nargs="?")
    ap.add_argument("--roots", nargs="+", default=DEFAULT_ROOTS)
    ap.add_argument("--limit", type=float, default=120.0)
    ap.add_argument("--max-mb", type=float, default=8.0)
    ap.add_argument("--n", type=int, default=40)
    ap.add_argument("--depth", type=int, default=4)
    a = ap.parse_args()
    if a.cmd == "scan":
        do_scan(a.roots, a.max_mb, a.limit)
    elif a.cmd == "where":
        do_where(a.model or "")
    elif a.cmd == "tree":
        do_tree(a.model, a.depth)
    else:
        do_changes(a.n)


if __name__ == "__main__":
    main()


