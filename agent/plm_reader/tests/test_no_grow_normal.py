# -*- coding: utf-8 -*-
"""ГЛАВНЫЙ тест: обычный скан (full=False) 5 раз — база НЕ должна расти.
Это ЖИЗНЕННЫЙ режим (окно зовёт full=False)."""
import sys, os, sqlite3, tempfile
sys.path.insert(0, r"D:\AI\tools\agent\plm_reader")
os.chdir(r"D:\AI\tools\agent\plm_reader")
import engine as E

draft = os.path.join(tempfile.gettempdir(), "grow_nf.db")
for s in ("", "-wal", "-shm", "-journal"):
    if os.path.exists(draft + s):
        os.remove(draft + s)
con = sqlite3.connect(draft); con.executescript(E.SCHEMA); con.commit(); con.close()

ROOT = r"Z:\PTC\Work\001_15 ЦТКД Электон"
TABS = ("snapshots", "params", "history", "unknown_fields", "matrices",
        "bodies", "materials", "dim_all", "items", "links", "derived",
        "health", "family", "props", "changes")


def counts():
    c = sqlite3.connect(draft)
    d = {}
    for t in TABS:
        try:
            d[t] = c.execute("SELECT COUNT(*) FROM [%s]" % t).fetchone()[0]
        except Exception:
            d[t] = -1
    c.close()
    return d


out = []
series = []
for i in range(1, 6):
    E.do_scan([ROOT], 24, 30, db=draft, full=False, remember=False)
    series.append(counts())
    out.append("SCAN%d(full=False): size=%.1fMB changes=%d links=%d params=%d" % (
        i, os.path.getsize(draft) / 1048576,
        series[-1]["changes"], series[-1]["links"], series[-1]["params"]))

bad = []
out.append("")
for t in TABS:
    vals = [s[t] for s in series]
    if vals[0] == -1:
        continue
    ok = all(v == vals[0] for v in vals)
    if not ok:
        bad.append(t)
    out.append("%-16s %s  %s" % (t, " ".join("%7d" % v for v in vals),
                                 "OK" if ok else "GROWS"))

out.append("")
out.append("VERDICT(full=False): " + ("OK - base does NOT grow" if not bad
                                      else "FAIL - grows: " + ",".join(bad)))

with open(r"D:\AI\tmp\_grnf.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")

for s in ("", "-wal", "-shm", "-journal"):
    if os.path.exists(draft + s):
        os.remove(draft + s)
