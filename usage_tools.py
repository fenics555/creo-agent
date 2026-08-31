# -*- coding: utf-8 -*-
r"""Индекс «где используется»: деталь -> родительские сборки (по текстовым ссылкам в .asm)."""
import os, re, threading
import core
from core import trace
import scanner as SC

REF = re.compile(r"([A-Za-zА-Яа-я0-9_\-]+)\.(prt|asm)", re.I)
STATE = {"busy": False}

def _db():
    c = core.db()
    c.execute("CREATE TABLE IF NOT EXISTS usage(child TEXT, parent TEXT, parent_path TEXT)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_usage_child ON usage(child)")
    return c

def build_usage():
    if STATE["busy"]:
        return
    STATE["busy"] = True
    try:
        c = _db()
        names = set()
        for (n,) in c.execute("SELECT name FROM models WHERE ext IN ('prt','asm')"):
            names.add(re.sub(r"\.\d+$", "", n).lower())
        c.execute("DELETE FROM usage")
        rows, pats = [], SC._pats()
        for root in SC.read_roots():
            if not os.path.exists(root):
                continue
            for dp, dn, fns in os.walk(root):
                dn[:] = [d for d in dn if not SC.is_excluded(os.path.join(dp, d) + "/", pats)]
                for fn in fns:
                    low = fn.lower()
                    if not re.search(r"\.asm(?:\.\d+)?$", low):
                        continue
                    parent = re.sub(r"\.\d+$", "", low)
                    try:
                        txt = open(os.path.join(dp, fn), "rb").read().decode("utf-8", "ignore")
                    except Exception:
                        continue
                    found = set()
                    for mm in REF.finditer(txt):
                        ref = mm.group(1).lower()
                        if ref in names and ref != parent:
                            found.add(ref)
                    rows += [(ref, parent, os.path.join(dp, fn)) for ref in found]
        c.executemany("INSERT INTO usage(child,parent,parent_path) VALUES(?,?,?)", rows)
        c.commit(); c.close()
        trace("USAGE build", "OK", 0, "%d ссылок" % len(rows))
    finally:
        STATE["busy"] = False

def tool_usage_build(**kw):
    threading.Thread(target=build_usage, daemon=True).start()
    return "индекс «где используется» строится в фоне"

def tool_models_where(q="", limit=30, **kw):
    c = _db()
    total = c.execute("SELECT COUNT(*) FROM usage").fetchone()[0]
    if not total:
        c.close()
        return "индекс «где используется» ещё не построен — скажи: usage_build"
    toks = [t.lower() for t in re.findall(r"[A-Za-zА-Яа-я0-9][A-Za-zА-Яа-я0-9.\-]{2,}", q or "") if len(t) >= 3]
    if not toks:
        c.close()
        return "укажи имя модели или ключевое слово"
    out = []
    for t in toks:
        rows = c.execute("SELECT DISTINCT parent, parent_path FROM usage WHERE child LIKE ? LIMIT ?",
                         ("%" + t + "%", int(limit) or 30)).fetchall()
        out.append("'%s': входит в сборок: %d" % (t, len(rows)))
        out += ["- %s  (%s)" % (p, pp) for p, pp in rows]
    c.close()
    return "\n".join(out)

TOOLS = [
    {"name": "models_where", "desc": "Показать сборки, в которых используется модель/деталь (по индексу ссылок)", "params": {"q": "имя или ключевое слово", "limit": "сколько строк"}, "approval": False, "fn": tool_models_where},
    {"name": "usage_build", "desc": "Построить/обновить индекс «где используется» по всем папкам", "params": {}, "approval": False, "fn": tool_usage_build},
]