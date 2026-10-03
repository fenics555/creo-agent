# -*- coding: utf-8 -*-
"""Д13: index_repo.py пишет в chunks БЕЗ очистки -> каждый запуск дублирует индекс.
Проверяем на старом бэкапе: уникальных path против общего числа чанков."""
import sqlite3, time

OLD = r"D:\AI\tools\agent\data\backup\pre_kbclean_20260923_agent.sqlite"
c = sqlite3.connect("file:%s?mode=ro" % OLD.replace("\\", "/"), uri=True)

t0 = time.time()
total = c.execute("select count(*) from chunks").fetchone()[0]
uniq = c.execute("select count(distinct path) from chunks").fetchone()[0]
print("чанков всего: %d, уникальных файлов: %d  (%.1f с)" % (total, uniq, time.time() - t0))
if uniq:
    print("среднее копий на файл: %.1f" % (total / uniq))

print("\nтоп-5 файлов по числу копий:")
for row in c.execute("select path, count(*) n from chunks group by path order by n desc limit 5"):
    print("   %6d копий  %s" % (row[1], str(row[0])[:90]))

print("\nодин и тот же текст дублируется? (2 выборки одного path):")
row = c.execute("select path from chunks group by path having count(*)>1 limit 1").fetchone()
if row:
    p = row[0]
    texts = c.execute("select text from chunks where path=? limit 2", (p,)).fetchall()
    print("   path: %s" % str(p)[:80])
    if len(texts) == 2:
        print("   тексты идентичны: %s" % (texts[0][0] == texts[1][0]))
c.close()