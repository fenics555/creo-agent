# -*- coding: utf-8 -*-
"""Регресс-тест V217: скан читает ВСЕ итерации Creo и добирает файлы хвостовым проходом.

Ловит два живых дефекта:
  (A) `do_scan` при `latest_only=True` отсекал `_filter_latest` ВСЕ итерации, кроме старшей
      (замер 17.11.2026: 1 309 файлов из 60 749). Правка в `.prt.6` при существующем `.prt.7`
      не видна НИКОГДА. Теперь `latest_only` — только фильтр показа в окне, скан читает всё.
  (B) Файл, сохранённый конструктором ПРЯМО ВО ВРЕМЯ скана (mtime >= t0 - 2.0), не попадал
      в список обхода и терялся. Теперь после основного цикла есть хвостовой проход.

Сканирует ВРЕМЕННУЮ папку во ВРЕМЕННУЮ базу (не на Z:, не боевую).
Шару Z: не трогает. Выход: 0 — ок, 1 — провал.
"""
import os
import sqlite3
import sys
import tempfile

HERE = r"D:\AI\tools\agent\plm_reader"
sys.path.insert(0, HERE)
os.chdir(HERE)
import engine as E          # noqa: E402

fails = []
tmp = tempfile.mkdtemp(prefix="v217_scan_")
db = os.path.join(tmp, "v217.db")


def _mk(name, data=b"V217 dummy Creo payload\n" * 20):
    p = os.path.join(tmp, name)
    with open(p, "wb") as f:
        f.write(data)
    return p


# Две итерации одного изделия — обе ДОЛЖНЫ попасть в базу при latest_only=True.
p1 = _mk("part.prt.1")
p2 = _mk("part.prt.2")

c = sqlite3.connect(db)
c.executescript(E.SCHEMA)
c.commit()
c.close()

# V217-B: файл, «сохранённый во время скана». Создаём его ПОСЛЕ сбора списка файлов,
# но ДО основного цикла — ровно та гонка, от которой защищает хвостовой проход.
_orig_collect = E.collect_stat
p_late = os.path.join(tmp, "late.prt.1")


def _collect_and_inject(*a, **kw):
    out = _orig_collect(*a, **kw)
    with open(p_late, "wb") as f:
        f.write(b"V217 late save during scan\n" * 20)
    return out


E.collect_stat = _collect_and_inject
try:
    res = E.do_scan([tmp], 24, 60, db=db, full=False, remember=False, latest_only=True)
except Exception as e:                        # noqa: BLE001
    print("do_scan ошибка: %s" % e)
    res = {}
finally:
    E.collect_stat = _orig_collect

c = sqlite3.connect(db)
paths = {r[0] for r in c.execute("SELECT path FROM snapshots")}
c.close()
print("snapshots:", sorted(os.path.basename(p) for p in paths))
print("итог do_scan:", {k: res.get(k) for k in ("new", "new_iter", "mod", "skipped")})

# 1) A: ОБЕ итерации прочитаны, хотя latest_only=True
if p1 not in paths:
    fails.append("A: part.prt.1 не прочитан при latest_only=True — _filter_latest вернулся в обход")
if p2 not in paths:
    fails.append("A: part.prt.2 не прочитан при latest_only=True")
if len(paths) < 2:
    fails.append("A: в snapshots меньше 2 итераций одного изделия")

# 2) B: хвостовой проход подхватил файл, созданный во время скана
if p_late not in paths:
    fails.append("B: файл, сохранённый во время скана (mtime >= t0-2), потерян — хвостовой проход не сработал")

# 3) D: сводка возвращает счётчики итераций и «отсечено 0»
for k in ("new", "new_iter", "iter_pruned", "iter_total"):
    if k not in res:
        fails.append("D: в итоге do_scan нет ключа %r" % k)
if res.get("iter_pruned") != 0:
    fails.append("D: iter_pruned должен быть 0 (итерации больше не отсекаются)")

# 4) E: единый допуск mtime в plm_scanner.is_changed (1e-3)
import plm_scanner as SC      # noqa: E402
import inspect
_src = inspect.getsource(SC.is_changed)
if "1e-3" not in _src:
    fails.append("E: plm_scanner.is_changed не использует допуск 1e-3")

for suf in ("", "-wal", "-shm", "-journal"):
    try:
        os.remove(db + suf)
    except OSError:
        pass
for p in (p1, p2, p_late):
    try:
        os.remove(p)
    except OSError:
        pass
try:
    os.rmdir(tmp)
except OSError:
    pass

print("")
print("ИТОГ: " + ("ОК — скан читает все итерации + хвостовой проход ловит файлы, сохранённые во время скана"
                  if not fails else "ПРОВАЛЫ: " + "; ".join(fails)))
sys.exit(1 if fails else 0)
