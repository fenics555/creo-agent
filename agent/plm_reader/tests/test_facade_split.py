# -*- coding: utf-8 -*-
"""Регресс-тест V207: обёртки plm_queries вынесены в plm_facade, engine реэкспортирует."""
import os
import sys

HERE = r"D:\AI\tools\agent\plm_reader"
sys.path.insert(0, HERE)
os.chdir(HERE)
import engine as E          # noqa: E402
import plm_facade as F      # noqa: E402

fails = []
for name in ("plm_children", "plm_parents", "plm_instances", "plm_tops", "models_info",
             "count_tops", "derived_bases", "derived_children", "derived_map", "plm_tree_data",
             "mfg_models", "model_info", "plm_up_data", "plm_down_data", "full_tree_lines",
             "made_of_list", "do_where", "do_tree", "do_rename_plan"):
    got = getattr(E, name, None)
    want = getattr(F, name, None)
    ok = (got is not None and got is want)
    print("%-20s %s" % (name, "OK" if ok else "FAIL"))
    if not ok:
        fails.append(name)
print("")
print("ИТОГ: " + ("ВСЁ ОК" if not fails else "ПРОВАЛЫ: " + ", ".join(fails)))
sys.exit(1 if fails else 0)
