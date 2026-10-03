# -*- coding: utf-8 -*-
"""Что внутри бэкапа 6,38 ГБ (pre_kbclean) и покрыто ли это текущей базой.
Цель — доказательство ДО удаления, а не после. Файл целиком не читаем."""
import os, sqlite3, time

OLD = r"D:\AI\tools\agent\data\backup\pre_kbclean_20260923_agent.sqlite"
NEW = r"D:\AI\tools\agent\data\agent.sqlite"

def probe(p, label):
    print("== %s  %.2f ГБ" % (label, os.path.getsize(p) / 1073741824))
    c = sqlite3.connect("file:%s?mode=ro" % p.replace("\\", "/"), uri=True)
    tabs = [r[0] for r in c.execute(
        "select name from sqlite_master where type='table' and name not like 'fts_%' order by name")]
    for tb in tabs:
        t0 = time.time()
        try:
            n = c.execute('select count(*) from "%s"' % tb).fetchone()[0]
            print("   %-20s %10d  %6.2f с" % (tb, n, time.time() - t0))
        except Exception as e:
            print("   %-20s ошибка %s" % (tb, e))
    c.close()

probe(OLD, "СТАРЫЙ (pre_kbclean)")
print()
probe(NEW, "ТЕКУЩИЙ (agent.sqlite)")