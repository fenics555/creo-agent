# -*- coding: utf-8 -*-
"""Регресс-тест V214: `auto_maintain` — бесшовный автопилот БД (тихий проход).

Проверяем на ВРЕМЕННОЙ базе: «грязь» (само-связь + дубль пары + длинный дамп) вычищается
автоматически; итог — СТРОКА для строки состояния; схема подтянута; VACUUM при фрагментации
> AUTO_VACUUM_PCT делается НЕ чаще 1 раза в сутки (маркер `<база>.automaint.json`).
Шару Z: не трогает. Выход: 0 — ок, 1 — провал.
"""
import os
import shutil
import sqlite3
import sys
import tempfile

HERE = r"D:\AI\tools\agent\plm_reader"
sys.path.insert(0, HERE)
os.chdir(HERE)
import engine as E             # noqa: E402
import plm_database as DB      # noqa: E402

fails = []
tmp = tempfile.mkdtemp(prefix="v214_auto_")
db = os.path.join(tmp, "plm_reader.db")

con = sqlite3.connect(db)
con.executescript(E.SCHEMA)
con.execute("INSERT INTO snapshots(model,path) VALUES('AA','/a')")
# «грязь»: само-связь + дубль пары + длинный дамп unknown_fields
con.execute("INSERT INTO links(parent,child,qty,source) VALUES('AA','AA',1,'dwg')")
con.execute("INSERT INTO links(parent,child,qty,source) VALUES('B','C',1,'dwg')")
con.execute("INSERT INTO links(parent,child,qty,source) VALUES('B','C',2,'dwg')")
con.execute("INSERT INTO unknown_fields(path,model,name,count) VALUES('/a',?,'__ALL__',1)",
            ("x" * 3000,))
# фрагментация: наполняем «балласт» и УДАЛЯЕМ таблицу → страницы уходят в freelist_count
con.execute("CREATE TABLE _ballast(x TEXT)")
con.executemany("INSERT INTO _ballast(x) VALUES(?)", [("z" * 4000,) for _ in range(1500)])
con.commit()
con.execute("DROP TABLE _ballast")
con.commit()
free_pct = 0.0
try:
    _free = con.execute("PRAGMA freelist_count").fetchone()[0]
    _pc = con.execute("PRAGMA page_count").fetchone()[0]
    free_pct = (100.0 * _free / _pc) if _pc else 0.0
except sqlite3.Error:
    pass
con.close()
DB.set_schema_version(DB.SCHEMA_VERSION, db)
print("freelist до авто-обслуживания: %.1f%% (порог %.1f%%)" % (free_pct, DB.AUTO_VACUUM_PCT))

# ── сам авто-проход ──────────────────────────────────────────────────────────
txt = DB.auto_maintain(db)
print("итог auto_maintain:", repr(txt))
if not isinstance(txt, str) or not txt:
    fails.append("auto_maintain не вернул строку-итог")

con = sqlite3.connect(db)
self_l = con.execute("SELECT COUNT(*) FROM links WHERE lower(parent)=lower(child)").fetchone()[0]
dup = con.execute("SELECT COUNT(*) FROM (SELECT parent,child,source,kind FROM links "
                  "GROUP BY parent,child,source,kind HAVING COUNT(*) > 1)").fetchone()[0]
mx = con.execute("SELECT MAX(LENGTH(model)) FROM unknown_fields").fetchone()[0] or 0
ver = con.execute("SELECT v FROM meta WHERE k='schema_version'").fetchone()
con.close()
if self_l:
    fails.append("остались само-связи links: %d" % self_l)
if dup:
    fails.append("остались дубли links: %d" % dup)
if mx > DB.UF_VALUE_MAX + 40:
    fails.append("длинный дамп не обрезан: %d" % mx)
if not ver or int(ver[0]) != DB.SCHEMA_VERSION:
    fails.append("schema_version не выставлена: %r" % (ver,))

# ── суточный лимит VACUUM: маркер создан, повтор НЕ считает «оптимизирована» ──
marker = db + ".automaint.json"
if free_pct > DB.AUTO_VACUUM_PCT and not os.path.isfile(marker):
    fails.append("VACUUM прошёл, но маркер суточного лимита не создан")
second = DB.auto_maintain(db)
print("повторный auto_maintain:", repr(second))
if "оптимизирована" in second:
    fails.append("VACUUM выполнен повторно в тот же день")

shutil.rmtree(tmp, ignore_errors=True)
print("")
print("ИТОГ: " + ("ОК — автообслуживание бесшовно" if not fails
                  else "ПРОВАЛЫ: " + "; ".join(fails)))
sys.exit(1 if fails else 0)
