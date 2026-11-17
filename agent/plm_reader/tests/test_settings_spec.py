# -*- coding: utf-8 -*-
"""Регресс-тест V211: реестр настроек БЕЗ дублей + `special` скрыт из HTML-реестра.

Ловит два живых дефекта окна настроек: повторный заголовок группы (напр. «СКАН») и дубль полей
(спец-секции + общий список). Шару Z: не трогает. Выход: 0 — ок, 1 — провал.
"""
import os
import sys
from collections import Counter

HERE = r"D:\AI\tools\agent\plm_reader"
sys.path.insert(0, HERE)
os.chdir(HERE)
import plm_settings as s  # noqa: E402

fails = []

# 1) КЛЮЧИ уникальны
keys = [e[1] for e in s.SETTINGS_SPEC]
dup = [k for k, n in Counter(keys).items() if n > 1]
print("ключей:", len(keys), "| дубли:", dup)
if dup:
    fails.append("дубли ключей: %s" % dup)

# 2) ГРУППЫ идут НЕПРЕРЫВНЫМИ блоками (нет повторного заголовка)
seen, prev = set(), None
for g in [e[0] for e in s.SETTINGS_SPEC]:
    if g != prev:
        if g in seen:
            fails.append("группа «%s» повторяется (второй заголовок)" % g)
        seen.add(g)
        prev = g

# 3) КЛЮЧЕВЫЕ граф-настройки на месте
for k in ("graph_depth", "graph_nodes_max", "graph_children_max",
          "graph_graph_layout", "graph_card_layout"):
    if k not in keys:
        fails.append("нет ключа %s" % k)

# 4) HTML-реестр НЕ содержит `special` (они только в спец-секциях окна)
jkeys = [d["key"] for d in s.settings_spec_json()]
for k in ("config_pro", "db_dir", "purge_backup_dir", "mirror_keep", "mirror_full_only"):
    if k in jkeys:
        fails.append("special «%s» просочился в HTML-реестр" % k)
print("HTML-реестр ключей:", len(jkeys))

print("")
print("ИТОГ: " + ("ОК — реестр без дублей, special скрыт из HTML" if not fails
                  else "ПРОВАЛЫ: " + "; ".join(fails)))
sys.exit(1 if fails else 0)
