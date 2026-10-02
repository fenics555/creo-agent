# -*- coding: utf-8 -*-
"""Живая проба аудита agent/data: две базы, целостность, кто чем пользуется."""
import os, sqlite3, time, json, hashlib
os.chdir(r"D:\AI\tools\agent")

for db in ("data/agent.sqlite", "data/harvest.db"):
    t = time.time()
    try:
        c = sqlite3.connect("file:%s?mode=ro" % db.replace("\\", "/"), uri=True)
        ic = c.execute("PRAGMA integrity_check").fetchone()[0]
        pc = c.execute("PRAGMA page_count").fetchone()[0]
        fr = c.execute("PRAGMA freelist_count").fetchone()[0]
        ts = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        print("==", db)
        print("   integrity:", ic, "| %.1fs" % (time.time() - t))
        print("   page_count=%d freelist=%d (свободно %.1f МБ)" % (pc, fr, fr * 4096 / 1e6))
        for t_ in ts:
            try:
                n = c.execute('SELECT count(*) FROM "%s"' % t_).fetchone()[0]
            except Exception as e:
                n = "ERR " + str(e)[:40]
            print("   %-22s %s" % (t_, n))
        c.close()
    except Exception as e:
        print("!!", db, e)

# harvest.db.bak — что это
print("\n== harvest.db.bak")
try:
    c = sqlite3.connect("file:data/harvest.db.bak?mode=ro", uri=True)
    print("   tables:", [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")])
    for t_ in [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]:
        print("   ", t_, c.execute('SELECT count(*) FROM "%s"' % t_).fetchone()[0])
    c.close()
except Exception as e:
    print("   не база:", e, open("data/harvest.db.bak", "rb").read(80))