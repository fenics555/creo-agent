# -*- coding: utf-8 -*-
"""Регресс-тест V209 (P2/P3): паритет DDL <-> эталон (31/31) + индексы после engine.connect().

1) Набор таблиц `plm_schema.SCHEMA` (CREATE TABLE) совпадает с ключами `plm_database.SCHEMA` — 31;
2) Свежая база, поднятая ТОЛЬКО через `engine.connect()`, содержит `meta` и индексы `ix_*`
   (раньше индексы создавались лишь миграциями/схемой черновика сканера).
Работает в %TEMP%, шару Z: не трогает. Выход: 0 — ок, 1 — провал.
"""
import os
import re
import shutil
import sys
import tempfile

HERE = r"D:\AI\tools\agent\plm_reader"
sys.path.insert(0, HERE)
os.chdir(HERE)
import engine as E             # noqa: E402
import plm_schema              # noqa: E402
import plm_database as DB      # noqa: E402

fails = []

ddl_tables = set(re.findall(r"CREATE TABLE IF NOT EXISTS\s+([A-Za-z_]+)", plm_schema.SCHEMA))
etalon_tables = set(DB.SCHEMA)
print("таблиц в DDL    :", len(ddl_tables))
print("таблиц в эталоне:", len(etalon_tables))
missing = sorted(etalon_tables - ddl_tables)
extra = sorted(ddl_tables - etalon_tables)
print("нет в DDL :", missing)
print("лишние    :", extra)
if missing or extra:
    fails.append("паритет таблиц: missing=%s extra=%s" % (missing, extra))
if len(ddl_tables) != 31:
    fails.append("в DDL %d таблиц, ждали 31" % len(ddl_tables))

# ── свежая база ТОЛЬКО через connect() ──────────────────────────────────────────
tmp = tempfile.mkdtemp(prefix="v209_schema_")
db = os.path.join(tmp, "plm_reader.db")
try:
    con = E.connect(db=db)
    ix = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND sql IS NOT NULL")]
    tbl = [r[0] for r in con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    con.close()
except Exception as e:                        # noqa: BLE001
    ix, tbl = [], []
    fails.append("connect() упал: %s" % e)

print("таблиц после connect():", len(tbl), "| индексов:", len(ix))
if "meta" not in tbl:
    fails.append("после connect() нет таблицы meta")
if not any(n.startswith("ix_snap_path") for n in ix):
    fails.append("после connect() нет индекса ix_snap_path (схема не создаёт индексы)")
if len(ix) < 20:
    fails.append("после connect() мало индексов: %d" % len(ix))

shutil.rmtree(tmp, ignore_errors=True)

print("")
print("ИТОГ: " + ("ОК — схема 31/31 и индексы на месте" if not fails
                  else "ПРОВАЛЫ: " + "; ".join(fails)))
sys.exit(1 if fails else 0)
