# -*- coding: utf-8 -*-
"""graph_tools: build connection graph for a model."""
import core

def _children_bom(name):
    try:
        c = core.db()
        rows = c.execute("SELECT child FROM bom WHERE parent LIKE ?", ("%" + name + "%",)).fetchall()
        c.close()
        return [r[0] for r in rows]
    except Exception:
        return []

def _parents_bom(name):
    try:
        c = core.db()
        rows = c.execute("SELECT parent FROM bom WHERE child LIKE ?", ("%" + name + "%",)).fetchall()
        c.close()
        return [r[0] for r in rows]
    except Exception:
        return []

def _usage_links(name):
    try:
        c = core.db()
        rows = c.execute("SELECT child FROM usage WHERE parent LIKE ?", ("%" + name + "%",)).fetchall()
        c.close()
        return [r[0] for r in rows]
    except Exception:
        return []

def _cross_links(name):
    try:
        c = core.db()
        rows = c.execute("SELECT child FROM links WHERE parent LIKE ?", ("%" + name + "%",)).fetchall()
        c.close()
        return [r[0] for r in rows]
    except Exception:
        return []

def build_graph(name, depth=2):
    nodes = []
    links = []
    visited = set()
    nodes.append({"id": name, "name": name, "kind": "center", "meta": {}})
    visited.add(name)
    for _ in range(depth):
        new_nodes = []
        for n in list(visited):
            for child in _children_bom(n):
                if child not in visited:
                    visited.add(child)
                    nodes.append({"id": child, "name": child, "kind": "bom_child", "meta": {}})
                    links.append({"source": n, "target": child, "kind": "bom"})
                    new_nodes.append(child)
            for parent in _parents_bom(n):
                if parent not in visited:
                    visited.add(parent)
                    nodes.append({"id": parent, "name": parent, "kind": "bom_parent", "meta": {}})
                    links.append({"source": parent, "target": n, "kind": "bom"})
                    new_nodes.append(parent)
    for u in _usage_links(name):
        if u not in visited:
            visited.add(u)
            nodes.append({"id": u, "name": u, "kind": "usage", "meta": {}})
            links.append({"source": name, "target": u, "kind": "usage"})
    for lnk in _cross_links(name):
        if lnk not in visited:
            visited.add(lnk)
            nodes.append({"id": lnk, "name": lnk, "kind": "link", "meta": {}})
            links.append({"source": name, "target": lnk, "kind": "link"})
    return {"nodes": nodes, "links": links}

TOOLS = [{"name": "graph", "desc": "\u0413\u0440\u0430\u0444 \u0441\u0432\u044f\u0437\u0435\u0439 \u043c\u043e\u0434\u0435\u043b\u0438", "params": {"name": "\u0438\u043c\u044f"}, "fn": build_graph}]
