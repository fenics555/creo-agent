# -*- coding: utf-8 -*-
"""map_tools.py: карта проекта — корневые каталоги и топ моделей по связям."""
import os
import core

TOOLS = [
    {"name": "map", "desc": "Карта проекта: корни и топ моделей по связям",
     "params": {"top": "сколько топовых моделей"}, "fn": "build_map"}
]

def build_map(top_n=100):
    c = core.db()
    try:
        # степени моделей одним SQL с LEFT JOIN по трём таблицам (без цикла по строкам)
        rows = c.execute("""
            SELECT f.path,
                   COALESCE(u.cnt, 0) + COALESCE(b.cnt, 0) + COALESCE(l.cnt, 0) AS links
            FROM files f
            LEFT JOIN (SELECT parent, COUNT(*) AS cnt FROM usage GROUP BY parent) u ON f.path = u.parent
            LEFT JOIN (SELECT parent, COUNT(*) AS cnt FROM bom GROUP BY parent) b ON f.path = b.parent
            LEFT JOIN (SELECT parent, COUNT(*) AS cnt FROM links GROUP BY parent) l ON f.path = l.parent
        """).fetchall()
        # группировка по корню (последний компонент родительского пути)
        roots = {}
        top = []
        for path, links in rows:
            d = os.path.dirname(path)
            root = os.path.basename(d) if d else ""
            roots.setdefault(root, {"name": root, "count": 0, "links": 0})
            roots[root]["count"] += 1
            roots[root]["links"] += links
            top.append({"name": path, "root": root, "links": links})
        root_list = sorted(roots.values(), key=lambda r: r["links"], reverse=True)
        top_sorted = sorted(top, key=lambda t: t["links"], reverse=True)[:top_n]
        return {"roots": root_list, "top": top_sorted}
    finally:
        c.close()
