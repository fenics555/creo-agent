# -*- coding: utf-8 -*-
"""Регресс-тест V212: метрика «Реки» не «врёт нулём» + стартовые river-настройки в реестре.

Ловит два живых дефекта панели «Река» (план S3):
  (1) показ `int(100.0 * top_sum / rows)` давал на боевой базе ровно «0%»
      (замер 17.11.2026: топ-10 = 215 событий из 72241 = 0.30%); целочисленное усечение врало;
  (2) окно держало свои зашитые значения (неделя/0/10/выкл) и НЕ читало настройки.

Шару Z: не трогает. Выход: 0 — ок, 1 — провал.
"""
import os
import sys

HERE = r"D:\AI\tools\agent\plm_reader"
sys.path.insert(0, HERE)
os.chdir(HERE)
import plm_settings as s      # noqa: E402
import plm_toolwin as tw      # noqa: E402

fails = []

# 1) ФОРМАТ на боевом замере: 215 / 72241 должно печататься «0.3%», а не «0%».
pct = tw.river_share_pct(215, 72241)
print("river_share_pct(215, 72241) = %r -> %.1f%%" % (pct, pct))
if ("%.1f%%" % pct) != "0.3%":
    fails.append("топ-10 боевой базы должен печататься 0.3%%, получено %.1f%%" % pct)

# 2) ГРАНИЦЫ функции
if tw.river_share_pct(0, 0) != 0.0:
    fails.append("пустой журнал (0/0) должен давать 0.0")
if abs(tw.river_share_pct(5, 10) - 50.0) > 1e-9:
    fails.append("5 из 10 должно быть 50.0")
if abs(tw.river_share_pct(1, 3) - 33.3333) > 0.01:
    fails.append("1 из 3 должно быть ~33.33")

# 3) river-настройки ЕСТЬ в реестре и стоят в группе ПОКАЗ (иначе окно их не увидит)
spec = {e[1]: e for e in s.SETTINGS_SPEC}
for k in ("river_step", "river_periods", "river_top", "river_new"):
    if k not in spec:
        fails.append("нет ключа %s в SETTINGS_SPEC" % k)
    elif spec[k][0] != "ПОКАЗ":
        fails.append("%s должен быть в группе ПОКАЗ (сейчас %r)" % (k, spec[k][0]))

# 4) ДЕФОЛТЫ есть и того же типа, что в реестре (кнопки «Реки» стартуют из них)
for k, ktype in (("river_step", str), ("river_periods", int),
                 ("river_top", int), ("river_new", bool)):
    if k not in s.DEFAULT_SETTINGS:
        fails.append("нет дефолта %s в DEFAULT_SETTINGS" % k)
    elif not isinstance(s.DEFAULT_SETTINGS[k], ktype):
        fails.append("дефолт %s должен быть %s" % (k, ktype.__name__))
print("river-настройки: ", {k: s.DEFAULT_SETTINGS.get(k)
                            for k in ("river_step", "river_periods", "river_top", "river_new")})

print("")
print("ИТОГ: " + ("ОК — метрика «Реки» дробная, river-настройки в реестре" if not fails
                  else "ПРОВАЛЫ: " + "; ".join(fails)))
sys.exit(1 if fails else 0)
