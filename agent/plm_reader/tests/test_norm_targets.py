# -*- coding: utf-8 -*-
"""Регресс-тест V204: NORM_TARGETS покрывает ВСЕ таблицы с именами (в т.ч. bodies, drawing)."""
import os
import sys

HERE = r"D:\AI\tools\agent\plm_reader"
sys.path.insert(0, HERE)
os.chdir(HERE)
import plm_database as DB       # noqa: E402

need = [("snapshots", "model"), ("params", "model"), ("links", "parent"), ("links", "child"),
        ("derived", "child"), ("derived", "base"), ("items", "model"), ("bodies", "model"),
        ("drawing", "model"), ("materials", "model"), ("tools", "model"), ("dim_all", "model"),
        ("master_mat", "model"), ("graph_nodes", "model"), ("graph_edges", "from")]
have = set(DB.NORM_TARGETS)
missing = [x for x in need if x not in have]
print("NORM_TARGETS всего:", len(DB.NORM_TARGETS))
print("не хватает:", missing)
print("")
print("ИТОГ: " + ("ОК — все ключевые колонки покрыты" if not missing else "ПРОВАЛ: %s" % missing))
sys.exit(1 if missing else 0)
