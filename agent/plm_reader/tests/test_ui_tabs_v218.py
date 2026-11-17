# -*- coding: utf-8 -*-
"""Регресс-тест V218: исправление 5 дефектов UI и HTML-консоли (живые скриншоты владельца).

Проверяет (статически, без боевой базы и без шары Z:):
  1) plm_toolwin.py: импорт `defaultdict` есть; нет обращения к неопределённой `raw`;
  2) plm_toolwin.py: предохранители max_nodes / _g_max_nodes в «Дереве связей» и «Родословной»;
  3) plm_toolwin.py: фильтры var_hist_all / var_hist_ext во вкладке «История файла»;
  4) plm_graph_page.html: узлы без даты (ts == 0) уходят в конец при «Свежие ↓»;
  5) plm_graph.py: ts_by_model сопоставляется по canon_model(model);
  6) plm_graph_build.py: has_media через os.path.normcase / canon-похожий стем.
Выход: код 0 — всё ок, 1 — есть провалы.
"""
import os
import re
import sys

HERE = r"D:\AI\Tools\agent\plm_reader"
sys.path.insert(0, HERE)

fails = []


def check(name, ok, detail=""):
    print("%-64s %-6s %s" % (name, "OK" if ok else "FAIL", detail))
    if not ok:
        fails.append(name + (": " + detail if detail else ""))


def read_text(rel):
    p = os.path.join(HERE, rel)
    with open(p, encoding="utf-8") as f:
        return f.read()


# ── 1) defaultdict импортирован, raw не используется как переменная ──
tw = read_text("plm_toolwin.py")
check("plm_toolwin.py: импорт `from collections import defaultdict`",
      "from collections import defaultdict" in tw)
raw_calls = re.findall(r"read_dims_all\(raw\)|read_history\(raw\)|dwg_models\(raw\)|\braw\s*=", tw)
check("plm_toolwin.py: нет обращения к неопределённой `raw` (_prop_show)",
      not raw_calls, "найдено: %s" % raw_calls)

# ── 2) предохранители max_nodes / _g_max_nodes ──
check("plm_toolwin.py: `max_nodes` в _fill_up (Дерево связей)",
      "max_nodes" in tw and "def _fill_up" in tw)
check("plm_toolwin.py: `_g_max_nodes = 800` (Родословная)", "_g_max_nodes = 800" in tw)
check("plm_toolwin.py: `_g_ok` предохранитель графа (посещённые вершины visited)",
      "def _g_ok" in tw and "_g_seen" in tw)

# ── 3) фильтры «История файла» ──
check("plm_toolwin.py: `var_hist_all` (по всему изделию)", "var_hist_all" in tw)
check("plm_toolwin.py: `var_hist_ext` (тип файла .prt/.asm/.drw)", "var_hist_ext" in tw)

# ── 4) HTML: ts == 0 в конец при «Свежие ↓» ──
html = read_text("plm_graph_page.html")
check("plm_graph_page.html: сравнение ts с нулём (ta === 0 / tb === 0)",
      "ta === 0" in html and "tb === 0" in html)
check("plm_graph_page.html: возврат +1/-1 для ts==0 (в конец)",
      "return -1" in html and "return 1" in html)

# ── 5) plm_graph.py: canon_model для ts_by_model ──
gp = read_text("plm_graph.py")
check("plm_graph.py: импорт canon_model", "from creo_read import canon_model" in gp)
check("plm_graph.py: canon_model(_m) при построении ts_by_model", "ts_by_model.get(_k" in gp)

# ── 6) plm_graph_build.py: normcase + стем для has_media ──
gb = read_text("plm_graph_build.py")
check("plm_graph_build.py: os.path.normcase при сопоставлении media_cache",
      "os.path.normcase" in gb)
check("plm_graph_build.py: fallback по стеблю (media_by_stem)", "media_by_stem" in gb)

# ── импорты модулей не ломаются (без БД) ──
try:
    import plm_reader  # noqa: F401
    check("import plm_reader", True)
except Exception as e:
    check("import plm_reader", False, str(e))

try:
    import plm_graph  # noqa: F401
    check("import plm_graph", True)
except Exception as e:
    check("import plm_graph", False, str(e))

try:
    import plm_graph_build  # noqa: F401
    check("import plm_graph_build", True)
except Exception as e:
    check("import plm_graph_build", False, str(e))

print()
print("ИТОГ: " + ("ВСЁ ОК" if not fails else "ПРОВАЛЫ: " + "; ".join(fails)))
sys.exit(1 if fails else 0)