# -*- coding: utf-8 -*-
"""Регресс-тест V216: ТОЧНОЕ обнаружение изменённого файла в сканере (`engine._scan_unchanged`).

Ловит живой дефект (владелец: «сканер пропускает обновлённые на диске файлы»): признак
«файл не изменился» был `abs(old_mtime - mtime) < 1.0` — слепая зона ±1 с, при которой
перезаписанный файл с тем же размером молча пропускался; пустые поля не проверялись.
Теперь: `size` и `mtime` сверяются ТОЧНО (±1e-3), учитывается `created`, а пустые/нулевые
`size`/`mtime` ⇒ файл ОБЯЗАТЕЛЬНО перечитывается. Плюс — опция `scan_verify_hash` в реестре.

Шару Z: не трогает. Выход: 0 — ок, 1 — провал.
"""
import os
import sys

HERE = r"D:\AI\tools\agent\plm_reader"
sys.path.insert(0, HERE)
os.chdir(HERE)
import engine as E          # noqa: E402
import plm_settings as S    # noqa: E402

fails = []


def row(size, mtime, created):
    """Строка `snapshots` в порядке SELECT из `do_scan`:
    (path,volume,material,name,designation,rev,author,revdate,role,size,mtime,created)."""
    return ("X", 0, "", "", "", "", "", "", "", size, mtime, created)


# 1) Файл НЕ изменился: size+mtime+created совпадают точно
if not E._scan_unchanged(row(1000, 1700000000.0, 1690000000.0), 1000, 1700000000.0, 1690000000.0):
    fails.append("точное совпадение size+mtime+created должно давать «не изменён»")

# 2) ГЛАВНЫЙ РЕГРЕСС: mtime сдвинулся на 0.5 с (< прежней слепой зоны 1.0) — файл ИЗМЕНЁН
if E._scan_unchanged(row(1000, 1700000000.0, 1690000000.0), 1000, 1700000000.5, 1690000000.0):
    fails.append("mtime +0.5 с — файл ИЗМЕНЁН (старый тест <1.0 его пропускал)")

# 3) Изменился размер
if E._scan_unchanged(row(1000, 1700000000.0, 1690000000.0), 1001, 1700000000.0, 1690000000.0):
    fails.append("иной размер — файл ИЗМЕНЁН")

# 4) Изменился created (при совпадении size+mtime)
if E._scan_unchanged(row(1000, 1700000000.0, 1690000000.0), 1000, 1700000000.0, 1690000500.0):
    fails.append("иной created — файл ИЗМЕНЁН")

# 5) Пустые/нулевые size или mtime ⇒ ОБЯЗАТЕЛЬНО перечитать (не «не изменён»)
if E._scan_unchanged(row(0, 1700000000.0, 1690000000.0), 0, 1700000000.0, 1690000000.0):
    fails.append("size=0 в базе — нельзя считать «не изменён»")
if E._scan_unchanged(row(1000, 0, 1690000000.0), 1000, 1700000000.0, 1690000000.0):
    fails.append("mtime=0 в базе — нельзя считать «не изменён»")

# 6) Нет записи в базе — файл НОВЫЙ, читать
if E._scan_unchanged(None, 1000, 1700000000.0, 1690000000.0):
    fails.append("нет строки snapshots — файл НОВЫЙ, читать")

# 7) created отсутствует (легаси 0) — не мешает: сверяем только size+mtime
if not E._scan_unchanged(row(1000, 1700000000.0, 0), 1000, 1700000000.0, 1690000000.0):
    fails.append("created=0 (легаси) не должен мешать сверке size+mtime")

# 8) ОПЦИЯ `scan_verify_hash` есть в реестре настроек (bool, дефолт False)
spec = {e[1]: e for e in S.SETTINGS_SPEC}
if "scan_verify_hash" not in spec:
    fails.append("нет ключа scan_verify_hash в SETTINGS_SPEC")
elif spec["scan_verify_hash"][3] != "bool":
    fails.append("scan_verify_hash должен быть bool в SETTINGS_SPEC")
if S.DEFAULT_SETTINGS.get("scan_verify_hash") is not False:
    fails.append("дефолт scan_verify_hash должен быть False")

print("")
print("ИТОГ: " + ("ОК — точное обнаружение изменений (size/mtime/created) + опция сверки содержимого"
                  if not fails else "ПРОВАЛЫ: " + "; ".join(fails)))
sys.exit(1 if fails else 0)
