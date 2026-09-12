# -*- coding: utf-8 -*-
r"""Индекс «где используется»: деталь -> сборки (слова из бинарных .asm)."""
import os, re, threading, time
import core
from core import trace
RUN = re.compile(rb"[A-Za-z0-9_-]{3,}")
STATE = {"busy": False, "done": 0, "total": 0, "links": 0, "names": 0, "finished": "", "error": "", "roots_info": ""}
def _db():
    c = core.db()
    c.execute("CREATE TABLE IF NOT EXISTS usage(child TEXT, parent TEXT, parent_path TEXT)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_usage_child ON usage(child)")
    c.execute("CREATE TABLE IF NOT EXISTS usage_meta(path TEXT PRIMARY KEY, mtime REAL)")
    return c
def _base(n): return re.sub(r"\.(prt|asm)(\.\d+)?$", "", n, flags=re.I)
def build_usage(full=False):
    if STATE["busy"]: return
    STATE.update(busy=True, done=0, total=0, links=0, error="")
    trace("USAGE build", "START", 0, "полный " if full else "инкремент")
    try:
        c = _db(); names = set()
        for (n,) in c.execute("SELECT name FROM models WHERE LOWER(ext) IN ('prt','asm')"): names.add(_base(n).upper())
        STATE["names"] = len(names)
        has_old = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usage'").fetchone()
        old_meta = {}
        if has_old and not full: old_meta = dict(c.execute("SELECT path, mtime FROM usage_meta").fetchall())
        if not old_meta: full = True
        roots = (__import__('scanner').read_roots())
        STATE["roots_info"] = "; ".join("%s:%s" % (r, "есть" if os.path.exists(r) else "НЕТ") for r in roots)
        tasks = []
        for root in roots:
            if not os.path.exists(root): continue
            for dp, dn, fns in os.walk(root):
                tasks += [os.path.join(dp, fn) for fn in fns if re.search(r"\.asm(\.\d+)?$", fn, re.I)]
        STATE["total"] = len(tasks)
        c.execute("DROP TABLE IF EXISTS usage_new"); c.execute("CREATE TABLE usage_new(child TEXT, parent TEXT, parent_path TEXT)")
        rows, new_meta, reused = [], {}, 0
        for path in tasks:
            try: mt = os.path.getmtime(path)
            except Exception: mt = 0.0
            new_meta[path] = mt; parent = _base(os.path.basename(path)).upper()
            if has_old and not full and old_meta.get(path) == mt:
                rows += c.execute("SELECT child, parent, parent_path FROM usage WHERE parent_path=?", (path,)).fetchall(); reused += 1
            else:
                try:
                    with open(path, "rb") as f: data = f.read()
                except Exception: data = b""
                found = set()
                for mm in RUN.finditer(data):
                    ref = mm.group(0).decode().upper()
                    if ref in names and ref != parent: found.add(ref)
                rows += [(ref.lower(), parent.lower(), path) for ref in found]
            STATE["done"] += 1
            if STATE["done"] % 20 == 0: time.sleep(0.001)
        c.executemany("INSERT INTO usage_new(child,parent,parent_path) VALUES(?,?,?)", rows)
        c.execute("DELETE FROM usage_meta"); c.executemany("INSERT INTO usage_meta(path,mtime) VALUES(?,?)", list(new_meta.items()))
        c.execute("DROP TABLE IF EXISTS usage_old")
        if has_old: c.execute("ALTER TABLE usage RENAME TO usage_old")
        c.execute("ALTER TABLE usage_new RENAME TO usage"); c.execute("DROP TABLE IF EXISTS usage_old")
        c.execute("CREATE INDEX IF NOT EXISTS ix_usage_child ON usage(child)")
        c.commit(); c.close()
        STATE.update(links=len(rows), finished=time.strftime("%d.%m %H:%M"))
        trace("USAGE build", "OK", 0, "names=%d tasks=%d links=%d reused=%d" % (len(names), len(tasks), len(rows), reused))
    except Exception as e:
        STATE["error"] = str(e)[:200]; trace("USAGE build", "ERR", 0, str(e)[:120])
    finally: STATE["busy"] = False
def tool_usage_build(full=0, **kw):
    threading.Thread(target=build_usage, args=(str(full) in ("1","true","True"),), daemon=True).start()
    return "индекс строится в фоне; прогресс — usage_state; full=1 — полный"
def tool_usage_state(**kw):
    if STATE["busy"]: return "идёт построение: %d/%d файлов, пока %d ссылок" % (STATE["done"], STATE["total"], STATE["links"])
    if STATE["error"]: return "ошибка: %s" % STATE["error"]
    if STATE["finished"]: return "индекс готов (%s): ссылок %d (имён %d, asm %d). Корни: %s" % (STATE["finished"], STATE["links"], STATE["names"], STATE["total"], STATE.get("roots_info",""))
    try:
        _c = _db(); _tot = _c.execute("SELECT COUNT(*) FROM usage").fetchone()[0]; _c.close()
        if _tot: return "индекс готов (из базы): ссылок %d (имён %d). Корни: %s" % (_tot, STATE["names"], STATE.get("roots_info", ""))
    except Exception: pass
    return "индекс ещё не строили. Скажи: usage_build full=1"
def tool_models_where(q="", limit=30, **kw):
    try:
        c = _db(); total = c.execute("SELECT COUNT(*) FROM usage").fetchone()[0]
        if not total: c.close(); return "usage пуста. Билд: имён=%d, asm=%d. Корни: %s. Запусти usage_build full=1" % (STATE["names"], STATE["total"], STATE.get("roots_info",""))
        toks = [t.lower() for t in re.findall(r"[A-Za-zА-Яа-я0-9][A-Za-zА-Яа-я0-9.-]{2,}", q or "") if len(t) >= 3]
        if not toks: c.close(); return "укажи имя модели"
        out = []
        for t in toks:
            rows = c.execute("SELECT DISTINCT parent, parent_path FROM usage WHERE child LIKE ? LIMIT ?", ("%" + t + "%", int(limit) or 30)).fetchall()
            out.append("'%s': входит в сборок: %d" % (t, len(rows))); out += ["- %s  (%s)" % (p, pp) for p, pp in rows]
        c.close(); return "\n".join(out)
    except Exception as e: return "ошибка: %s" % e
TOOLS = [
 {"name": "models_where", "desc": "Сборки, в которых используется деталь", "params": {"q": "имя", "limit": "строк"}, "approval": False, "fn": tool_models_where},
 {"name": "usage_build", "desc": "Построить индекс «где используется» (full=1)", "params": {"full": "1"}, "approval": False, "fn": tool_usage_build},
 {"name": "usage_state", "desc": "Прогресс индекса + корни", "params": {}, "approval": False, "fn": tool_usage_state},
]
