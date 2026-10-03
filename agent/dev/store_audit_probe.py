# -*- coding: utf-8 -*-
"""Аудит хранилища агента (data/): целостность баз, счётчики, ТЯЖЁЛОЕ — ЗАМЕРОМ."""
import os, sqlite3, time, sys

BASE = r"D:\AI\tools\agent\data"
DBS = ["agent.sqlite", "harvest.db", "harvest.db.bak",
       os.path.join("backups", "agent_261003_0000.sqlite"),
       os.path.join("backup", "2026-09-23_2006_pre_plm_schema_agent.sqlite")]

for rel in DBS:
    p = os.path.join(BASE, rel)
    if not os.path.exists(p):
        print("== %s: НЕТ ФАЙЛА" % rel); sys.stdout.flush(); continue
    mb = os.path.getsize(p) / 1048576
    head = open(p, "rb").read(16)
    print("== %s  %.1f МБ  %s" % (rel, mb, time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(p)))))
    print("   magic=%r" % head[:15])
    try:
        t0 = time.time()
        c = sqlite3.connect("file:%s?mode=ro" % p.replace("\\", "/"), uri=True)
        chk = c.execute("PRAGMA quick_check").fetchone()[0]
        print("   quick_check=%s  (%.2f с)" % (chk, time.time() - t0))
        tabs = [r[0] for r in c.execute("select name from sqlite_master where type='table' order by name")]
        for tb in tabs:
            t0 = time.time()
            try:
                n = c.execute('select count(*) from "%s"' % tb).fetchone()[0]
                dt = time.time() - t0
                print("   %-22s %9d  %6.2f с%s" % (tb, n, dt, "   <== ТЯЖЁЛЫЙ ЗАМЕР" if dt > 3 else ""))
            except Exception as e:
                print("   %-22s ошибка: %s" % (tb, e))
        c.close()
    except Exception as e:
        print("   НЕ БАЗА:", e)
    sys.stdout.flush()