# -*- coding: utf-8 -*-
"""Регресс-тест V215: Исторический декодер `rescue_legacy_data` (Purge-safe, идемпотентен).

Проверяем на ВРЕМЕННОЙ базе:
  • классификацию легаси-журнала `changes` (строки НЕ удаляются, даты не ломаются);
  • извлечение имён полей из `unknown_fields` (JSON-дамп) в `params` (INSERT OR IGNORE):
    1-й прогон переносит, 2-й — 0 (идемпотентность), свежие данные не затираются;
  • ТОП-30 неразобранных имён полей со счётчиком по моделям;
  • `auto_maintain` выполняет разбор ОДНОКРАТНО (маркер `rescue_done` в `<база>.automaint.json`).
Шару Z: не трогает. Выход: 0 — ок, 1 — провал.
"""
import json
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
tmp = tempfile.mkdtemp(prefix="v215_rescue_")
db = os.path.join(tmp, "plm_reader.db")

con = sqlite3.connect(db)
con.executescript(E.SCHEMA)
con.executemany(
    "INSERT INTO changes(item,rev,kind,descr,who,ts) VALUES(?,?,?,?,?,?)",
    [("X1", "", "архив", "архив: файл:  -> x1.prt.1", "", "02.02.2023 "),
     ("X2", "", "архив", "архив: кто правил: ADMIN -> USER", "", "02.02.2023 "),
     ("X3", "", "архив", "архив: версия Creo: Creo 8.0.1.0 -> Creo 9.0.1.0", "", "02.02.2023 "),
     ("M1", "1", "modify", "material: PTC_MASTER_MATERIAL→-", "", "2026-09-25 21:56:23"),
     ("M2", "1", "modify", "role: proizv.X→-", "", "2026-09-25 21:56:23"),
     ("N1", "", "new", "первая запись паспорта", "", "2026-09-25 16:50:27")])
con.executemany(
    "INSERT INTO unknown_fields(path,model,name,count) VALUES(?,?,?,?)",
    [("D:/sklad/AAA.prt.1",
      json.dumps({"WIDTH": 2, "HEIGHT": 3, "PTC_MASTER_MATERIAL": 1, "1BAD": 4}), "__ALL__", 4),
     ("D:/sklad/BBB.prt.1",
      json.dumps({"PTC_MASTER_MATERIAL": 1, "WIDTH": 1}), "__ALL__", 2)])
con.commit()
con.close()
DB.set_schema_version(DB.SCHEMA_VERSION, db)
ch0 = 6


def q1(sql):
    c = sqlite3.connect(db)
    try:
        return c.execute(sql).fetchone()[0]
    finally:
        c.close()


# ── 1. DRY-RUN: только отчёт, база не меняется ───────────────────────────────
dry = DB.rescue_legacy_data(db, dry_run=True, quiet=True)
print("dry-run:", dry["changes"], dry["unknown_fields"]["top30"])
if q1("SELECT COUNT(*) FROM params") != 0:
    fails.append("dry_run: в params появились строки (должно быть 0)")
if not dry.get("ok"):
    fails.append("rescue dry-run: ok != True")
if dry["changes"]["legacy"] != 3:
    fails.append("classify: легаси %s (ждали 3)" % dry["changes"]["legacy"])
lbc = dry["changes"]["legacy_by_category"]
if lbc != {"файл": 1, "автор": 1, "среда": 1}:
    fails.append("classify: разбивка легаси неверна: %r" % (lbc,))
top = dry["unknown_fields"]["top30"]
if not top or top[0] != ["PTC_MASTER_MATERIAL", 2]:
    fails.append("top30: ожидали PTC_MASTER_MATERIAL(2 модели), получили %r" % (top,))

# ── 2. APPLY: перенос распознанных имён в params ─────────────────────────────
app = DB.rescue_legacy_data(db, dry_run=False, quiet=True)
print("apply:", app["unknown_fields"])
if app["unknown_fields"]["inserted"] != 3:
    fails.append("apply: перенесено %s (ждали 3: WIDTH,HEIGHT,BBB.WIDTH)"
                 % app["unknown_fields"]["inserted"])
if q1("SELECT COUNT(*) FROM params WHERE model='AAA' AND name='WIDTH'") != 1:
    fails.append("apply: нет params(model=AAA,name=WIDTH)")
if q1("SELECT COUNT(*) FROM changes") != ch0:
    fails.append("apply: число строк changes изменилось (архив ломать нельзя)")

# ── 3. ИДЕМПОТЕНТНОСТЬ: второй прогон ничего не добавляет ────────────────────
app2 = DB.rescue_legacy_data(db, dry_run=False, quiet=True)
if app2["unknown_fields"]["inserted"] != 0:
    fails.append("идемпотентность: 2-й прогон перенёс %s (ждали 0)"
                 % app2["unknown_fields"]["inserted"])
if q1("SELECT COUNT(*) FROM params") != 3:
    fails.append("идемпотентность: в params %s строк (ждали 3)" % q1("SELECT COUNT(*) FROM params"))

# ── 4. auto_maintain: разбор ОДНОКРАТНО (маркер rescue_done) ─────────────────
DB.auto_maintain(db)
marker = db + ".automaint.json"
md = {}
if os.path.isfile(marker):
    with open(marker, encoding="utf-8") as f:
        md = json.load(f)
if not md.get("rescue_done"):
    fails.append("auto_maintain: маркер rescue_done не выставлен (%r)" % (md,))
# стираем params и зовём автопилот снова — маркер НЕ даст разбирать легаси повторно
c = sqlite3.connect(db)
c.execute("DELETE FROM params")
c.commit()
c.close()
DB.auto_maintain(db)
if q1("SELECT COUNT(*) FROM params") != 0:
    fails.append("auto_maintain: легаси разобран ПОВТОРНО (маркер не сработал)")

shutil.rmtree(tmp, ignore_errors=True)
print("")
print("ИТОГ: " + ("ОК — Исторический декодер идемпотентен и Purge-safe" if not fails
                  else "ПРОВАЛЫ: " + "; ".join(fails)))
sys.exit(1 if fails else 0)
