# -*- coding: utf-8 -*-
r"""graph_tools: граф связей модели — источник теперь база ПЛМ-READER (03.10.2026).

Раньше блок читал агентские `bom/usage/links`, а `usage` пуст с 27.09 — граф был пустым.
Теперь всё из `plm_reader\db\...\links` (parent/child) одним SQL на узел.
"""
import plm_reader_tools as PRT


def _both(name):
    """(дети, родители) из links ПЛМ-READER — направление «вниз» и «вверх»."""
    E = PRT.engine()
    c = E.connect(ro=True)
    try:
        like = "%" + name + "%"
        kids = [r[0] for r in c.execute(
            "SELECT child FROM links WHERE parent LIKE ?", (like,))]
        pars = [r[0] for r in c.execute(
            "SELECT parent FROM links WHERE child LIKE ?", (like,))]
    finally:
        c.close()
    return kids, pars


def build_graph(name, depth=2):
    nodes = [{"id": name, "name": name, "kind": "center", "meta": {}}]
    links = []
    visited = {name}
    for _ in range(int(depth or 2)):
        for n in list(visited):
            kids, pars = _both(n)
            for child in kids:
                if child not in visited:
                    visited.add(child)
                    nodes.append({"id": child, "name": child, "kind": "bom_child", "meta": {}})
                    links.append({"source": n, "target": child, "kind": "bom"})
            for parent in pars:
                if parent not in visited:
                    visited.add(parent)
                    nodes.append({"id": parent, "name": parent, "kind": "bom_parent", "meta": {}})
                    links.append({"source": parent, "target": n, "kind": "bom"})
            if len(visited) > 600:          # предохранитель на больших сборках
                break
    return {"nodes": nodes, "links": links, "db": PRT._where_db()}


TOOLS = [{"name": "graph", "desc": "Граф связей модели (данные из ПЛМ-READER)",
          "params": {"name": "имя"}, "fn": build_graph}]
