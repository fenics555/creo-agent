# -*- coding: utf-8 -*-
"""Что внутри тяжёлых бэкапов: ТОЛЬКО метаданные (страницы sqlite_master), без чтения данных.
6.5 ГБ целиком не читаем — открываем ro и спрашиваем схему."""
import os, sqlite3, time

FILES = [
    r"D:\AI\tools\agent\data\backup\pre_kbclean_20260923_agent.sqlite",
    r"D:\AI\tools\agent\data\backup\2026-09-23_2006_pre_plm_schema_agent.sqlite",
    r"D:\AI\tools\agent\data\agent.sqlite",
]

for p in FILES:
    gb = os.path.getsize(p) / 1073741824
    print("== %s  %.2f ГБ" % (os.path.basename(p), gb))
    t = time.time()
    try:
        c = sqlite3.connect("file:%s?mode=ro" % p.replace("\\", "/"), uri=True)
        rows = c.execute("select type,name from sqlite_master order by type,name").fetchall()
        print("   объектов: %d  (%.2f с на схему — файл НЕ читался целиком)" % (len(rows), time.time() - t))
        tabs = [r[1] for r in rows if r[0] == "table"]
        for tb in tabs:
            # page_count*page_size = реальный размер; считаем по базе, без обхода строк
            pass
        pc = c.execute("PRAGMA page_count").fetchone()[0]
        ps = c.execute("PRAGMA page_size").fetchone()[0]
        fl = c.execute("PRAGMA freelist_count").fetchone()[0]
        print("   страниц: %d x %d Б = %.2f ГБ, свободных страниц: %d (%.2f ГБ)" % (
            pc, ps, pc * ps / 1073741824, fl, fl * ps / 1073741824))
        print("   таблиц: %d" % len(tabs))
        c.close()
    except Exception as e:
        print("   ОШИБКА: %s" % e)
    sys_flush = None
    print()