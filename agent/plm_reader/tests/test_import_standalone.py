# -*- coding: utf-8 -*-
"""Регресс-тест V209 (P1): КАЖДЫЙ модуль импортируется АВТОНОМНО (чистый процесс).

РАНЬШЕ plm_scan/plm_parse/plm_history/plm_paths_window шли через `from plm_reader import (...)`
и при прямом импорте падали `ImportError` (цикл импортов). Теперь все 23 модуля автономны.
Шару Z: не трогает (только импорт). Выход: 0 — ок, 1 — провал.
"""
import os
import subprocess
import sys

HERE = r"D:\AI\tools\agent\plm_reader"

# Все модули кода в корне (23; `__init__.py` — маркер пакета, не считаем).
MODULES = [
    "creo_read", "engine", "make_version_json", "plm_asm_parse", "plm_build_links",
    "plm_creo_parse", "plm_database", "plm_db_admin_win", "plm_dbview", "plm_facade",
    "plm_graph", "plm_graph_build", "plm_history", "plm_links", "plm_parse",
    "plm_paths_window", "plm_queries", "plm_reader", "plm_scan", "plm_scanner",
    "plm_schema", "plm_settings", "plm_toolwin",
]

fails = []
for m in MODULES:
    r = subprocess.run([sys.executable, "-c", "import " + m], cwd=HERE,
                       capture_output=True, text=True)
    ok = (r.returncode == 0)
    print("%-22s %s" % (m, "OK" if ok else "FAIL"))
    if not ok:
        tail = (r.stderr or "").strip().splitlines()
        fails.append("%s: %s" % (m, tail[-1] if tail else "?"))

print("")
print("ИТОГ: " + ("ВСЁ ОК — все %d модулей автономны" % len(MODULES)
                  if not fails else "ПРОВАЛЫ: " + "; ".join(fails)))
sys.exit(1 if fails else 0)
