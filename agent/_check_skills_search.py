# -*- coding: utf-8 -*-
"""Проверка: skills_search (инструмент Агента) читает ТУ ЖЕ базу, что skills_index.py."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import skills_index_tools as t
import skills_index as eng

print("DB движка   :", eng.DB)
print("DB существует:", eng.DB.exists(), eng.DB.stat().st_size if eng.DB.exists() else 0)

q = "сделать коммит по правилам дома"
r = t.search_preview(q, 3)
print("search_preview:", json.dumps(r, ensure_ascii=False, indent=1)[:900])

s = t.status_preview()
print("status_preview:", json.dumps(s, ensure_ascii=False))
