# -*- coding: utf-8 -*-
r"""ПЛМ: реестр изделий + BOM + ревизии + ИИ (ГОСТ 2.503)."""
import os, re, time, datetime
import core
def _db():
    c = core.db()
    c.execute("CREATE TABLE IF NOT EXISTS usage(child TEXT, parent TEXT, parent_path TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS items(designation TEXT PRIMARY KEY, name TEXT, type TEXT, material TEXT, format TEXT, mass REAL, lifecycle TEXT, rev TEXT, source TEXT, updated TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS bom(parent TEXT, child TEXT, qty REAL, source TEXT, PRIMARY KEY(parent, child))")
    c.execute("CREATE TABLE IF NOT EXISTS revisions(id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, rev TEXT, status TEXT, author TEXT, comment TEXT, ts TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS changes(id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, rev TEXT, kind TEXT, descr TEXT, who TEXT, reason TEXT, ts TEXT)")
    return c
def _base(n): return re.sub(r"\\.(prt|asm|drw)(\\.\\d+)?$", "", n, flags=re.I)
def tool_plm_mine(xml_dir="", **kw):
    c = _db(); n_items = 0
    for (n, e) in c.execute("SELECT name, ext FROM models WHERE LOWER(ext) IN ('prt','asm')"):
        d = _base(n); t = "Сборка" if e.lower() == "asm" else "Деталь"
        c.execute("INSERT OR IGNORE INTO items(designation,name,type,lifecycle,source,updated) VALUES(?,?,?,?,?,?)", (d.lower(), d, t, "Разработка", "models", time.strftime("%d.%m %H:%M")))
        n_items += 1
    c.execute("DELETE FROM bom")
    c.execute("INSERT OR IGNORE INTO bom(parent,child,qty,source) SELECT LOWER(parent), LOWER(child), 1, 'usage' FROM usage")
    n_xml = 0
    if xml_dir and os.path.isdir(xml_dir):
        import xml.etree.ElementTree as ET
        for fn in os.listdir(xml_dir):
            if not fn.lower().endswith(".xml"): continue
            try:
                root = ET.parse(os.path.join(xml_dir, fn)).getroot(); P = {}
                for p in root.findall("Parameter"):
                    v = p.find("Value"); P[p.get("Name")] = (v.text or "").strip() if v is not None else ""
                d = (P.get("ОБОЗНАЧЕНИЕ") or _base(fn)).strip().lower()
                name = " ".join(x for x in (P.get("НАИМЕНОВАНИЕ"), P.get("НАИМЕНОВАНИЕ1"), P.get("НАИМЕНОВАНИЕ2")) if x)
                try: mass = float(P.get("MASS") or 0)
                except Exception: mass = 0.0
                c.execute("INSERT INTO items(designation,name,type,material,format,mass,source,updated) VALUES(?,?,?,?,?,?,?,?) "
                          "ON CONFLICT(designation) DO UPDATE SET name=excluded.name,type=excluded.type,material=excluded.material,format=excluded.format,mass=excluded.mass,source='xml',updated=excluded.updated",
                          (d, name or d, P.get("ТИП") or "", P.get("PTC_MASTER_MATERIAL") or "", P.get("ФОРМАТ") or "", mass, time.strftime("%d.%m %H:%M")))
                n_xml += 1
            except Exception: pass
    c.commit()
    tot = c.execute("SELECT COUNT(*) FROM items").fetchone()[0]; bb = c.execute("SELECT COUNT(*) FROM bom").fetchone()[0]
    c.close()
    return "ПЛМ: изделий %d (models %d, XML %d), связей BOM %d" % (tot, n_items, n_xml, bb)
def tool_plm_item(q="", **kw):
    if not q: return "укажи обозначение"
    c = _db(); r = c.execute("SELECT * FROM items WHERE designation LIKE ?", ("%" + q.lower() + "%",)).fetchone()
    if not r: c.close(); return "не найдено: %s" % q
    cols = [d[0] for d in c.description]; c.close()
    return "; ".join("%s=%s" % (k, v) for k, v in zip(cols, r) if v not in (None, ""))
def tool_plm_bom(q="", depth=3, **kw):
    if not q: return "укажи обозначение сборки"
    c = _db(); q = q.lower(); out = []; seen = set()
    def walk(node, lvl):
        if lvl > int(depth) or node in seen: return
        seen.add(node)
        for (ch,) in c.execute("SELECT child FROM bom WHERE parent=?", (node,)):
            out.append("  " * lvl + "- %s" % ch); walk(ch, lvl + 1)
    walk(q, 0); c.close()
    return "Состав %s:\n%s" % (q, "\n".join(out) or "(пусто)")
def tool_plm_where(q="", **kw):
    if not q: return "укажи обозначение детали"
    c = _db(); rows = c.execute("SELECT parent FROM bom WHERE child LIKE ?", ("%" + q.lower() + "%",)).fetchall()
    c.close()
    return "%s входит в: %s" % (q, ", ".join(r[0] for r in rows) or "(никуда)")
def tool_lifecycle_set(q="", status="", **kw):
    if not (q and status): return "укажи обозначение и статус"
    c = _db(); c.execute("UPDATE items SET lifecycle=? WHERE designation LIKE ?", (status, "%" + q.lower() + "%"))
    n = c.total_changes; c.commit(); c.close()
    return "статус '%s' применён к %d" % (status, n)
def tool_generate_ii(q="", reason="", who="", **kw):
    if not q: return "укажи обозначение"
    c = _db()
    row = c.execute("SELECT designation, rev, lifecycle FROM items WHERE designation LIKE ?", ("%" + q.lower() + "%",)).fetchone()
    if not row: c.close(); return "не найдено: %s" % q
    des, rev, lc = row
    newrev = chr(ord(rev) + 1) if rev and rev < "Я" else "А"
    ts = datetime.datetime.now().strftime("%y%m%d_%H%M")
    c.execute("INSERT INTO changes(item,rev,kind,descr,who,reason,ts) VALUES(?,?,?,?,?,?,?)", (des, newrev, "модификация", "статус %s->Утверждено" % lc, who or "агент", reason, ts))
    c.execute("INSERT INTO revisions(item,rev,status,author,comment,ts) VALUES(?,?,?,?,?,?)", (des, newrev, "Утверждено", who or "агент", reason, ts))
    c.execute("UPDATE items SET rev=?, lifecycle='Утверждено', updated=? WHERE designation=?", (newrev, time.strftime("%d.%m %H:%M"), des))
    c.commit(); c.close()
    d = core.REPO / "Изменения"; d.mkdir(parents=True, exist_ok=True)
    p = d / ("ИИ_%s_%s.md" % (ts, des))
    p.write_text("ИЗВЕЩЕНИЕ ОБ ИЗМЕНЕНИИ (ГОСТ 2.503)\nОбозначение: %s\nРевизия: %s -> %s\nДата: %s\nКто: %s\nПричина: %s\n" % (des, rev or "—", newrev, ts, who or "агент", reason or "—"), encoding="utf-8")
    return "ИИ %s: %s (%s->%s)" % (p.name, des, rev or "—", newrev)
def tool_param_audit(**kw):
    c = _db()
    tot = c.execute("SELECT COUNT(*) FROM items").fetchone()[0]
    nomat = c.execute("SELECT COUNT(*) FROM items WHERE type='Деталь' AND (material IS NULL OR material='')").fetchone()[0]
    nofmt = c.execute("SELECT COUNT(*) FROM items WHERE (format IS NULL OR format='')").fetchone()[0]
    dup = c.execute("SELECT name, COUNT(*) n FROM items GROUP BY name HAVING n>1 LIMIT 10").fetchall()
    c.close()
    return "АУДИТ ПЛМ: изделий %d; без материала %d; без формата %d; дубли: %s" % (tot, nomat, nofmt, ", ".join("%s×%d" % (n, k) for n, k in dup) or "нет")
TOOLS = [
 {"name": "plm_mine", "desc": "Наполнить реестр изделий+BOM (models+usage+XML)", "params": {"xml_dir": "папка XML"}, "approval": True, "fn": tool_plm_mine},
 {"name": "plm_item", "desc": "Карточка изделия", "params": {"q": "обозначение"}, "approval": False, "fn": tool_plm_item},
 {"name": "plm_bom", "desc": "Состав сборки", "params": {"q": "сборка", "depth": "глубина"}, "approval": False, "fn": tool_plm_bom},
 {"name": "plm_where", "desc": "Куда входит деталь", "params": {"q": "деталь"}, "approval": False, "fn": tool_plm_where},
 {"name": "plm_lifecycle", "desc": "Сменить статус изделия", "params": {"q": "обозначение", "status": "статус"}, "approval": True, "fn": tool_lifecycle_set},
 {"name": "plm_ii", "desc": "Извещение об изменении (ГОСТ 2.503)", "params": {"q": "обозначение", "reason": "причина", "who": "кто"}, "approval": True, "fn": tool_generate_ii},
 {"name": "plm_audit", "desc": "Аудит реестра", "params": {}, "approval": False, "fn": tool_param_audit},
]
