# -*- coding: utf-8 -*-
"""Регресс-тест V210: авто-обслуживание не путает НАСТРОЙКИ (dict) и scan_config (кортеж).

Живой дефект: `apply_update` звал `scan_config() or {}` и затем `.get(...)` — а `scan_config`
возвращает КОРТЕЖ `(roots, exclude)` ⇒ `'tuple' object has no attribute 'get'`, авто-обслуживание
не выполнялось. Тест фиксирует контракт: настройки — словарь, scan_config — кортеж.
Шару Z: не трогает. Выход: 0 — ок, 1 — провал."""
import os
import sys

HERE = r"D:\AI\tools\agent\plm_reader"
sys.path.insert(0, HERE)
os.chdir(HERE)
import engine as E  # noqa: E402

fails = []
cfg = E._settings_json()
print("_settings_json() ->", type(cfg).__name__)
if not isinstance(cfg, dict):
    fails.append("_settings_json() вернул не dict, а %s" % type(cfg).__name__)

sc = E.scan_config()
print("scan_config() ->", type(sc).__name__, "(len=%d)" % (len(sc) if isinstance(sc, tuple) else -1))
if not isinstance(sc, tuple):
    fails.append("scan_config() вернул не кортеж, а %s" % type(sc).__name__)

# ключевая защита: настройки ПОДДЕРЖИВАЮТ .get (именно это ломалось)
try:
    bool(cfg.get("auto_maintenance", True))
except Exception as e:                        # noqa: BLE001
    fails.append("cfg.get упал: %s" % e)

print("")
print("ИТОГ: " + ("ОК — настройки это dict, scan_config это tuple" if not fails
                  else "ПРОВАЛЫ: " + "; ".join(fails)))
sys.exit(1 if fails else 0)
