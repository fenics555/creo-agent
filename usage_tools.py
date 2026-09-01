# -*- coding: utf-8 -*-
r"""Индекс «где используется»: деталь -> родительские сборки (слова из бинарных .asm)."""
import os, re, threading, time
import core
from core import trace
import scanner as SC

RUN = re.compile(rb"[A-Za-z0-9_\-]{3,}")
STATE = {"busy": False, "done": 0, "total": 0, "links": 0, "finished": "", "error": ""}

def _db():
    c = core.db()
    c.execute("CREATE TABLE IF NOT EXISTS usage(child TEXT, parent TEXT, parent_path TEXT)")
    c.execute("CREATE INDEX IF NOT EXISTS ix_usage_child ON usage(child)")
    return c

def build_usage():
    if STATE["busy"]:
        return
    STATE.update(busy=True, done=0, total=0, links=0, error="")
    trace("USAGE build", "START", 0, "начали")
    try:
        c = _db()
        names = set()
        for (n,) in c.execute("SELECT name FROM models WHERE ext IN ('prt','asm')"):
            names.add(re.sub(r"\.(prt|asm)(\.\d+)?$", "", n).upper())
        c.execute("DELETE FROM usage"); c.commit()
        pats = SC._pats()
        tasks = []
        for root in SC.read_roots():
            if not os.path.exists(root):
                continue
            for dp, dn, fns in os.walk(root):
                dn[:] = [d for d in dn if not SC.is_excluded(os.path.join(dp, d) + "/", pats)]
                tasks += [os.path.join(dp, fn) for fn in fns if re.search(r"\.asm(?:\.\d+)?$", fn.lower())]
        STATE["total"] = len(tasks)
        rows = []
        for path in tasks:
            parent = re.sub(r"\.\d+$", "", os.path.basename(path)).upper()
            try:
                data = open(path, "rb").read()
            except Exception:
                data = b""
            found = set()
            for mm in RUN.finditer(data):
                w = mm.group(0).decode()
                if w in names and w != parent:
                    found.add(w)
            rows += [(w.lower(), parent.lower(), path) for w in found]
            STATE["done"] += 1
            STATE["links"] = len(rows)
        c.executemany("INSERT INTO usage(child,parent,parent_path) VALUES(?,?,?)", rows)
        c.commit(); c.close()
        STATE["finished"] = time.strftime("%d.%m %H:%M")
        trace("USAGE build", "OK", 0, "%d ссылок" % len(rows))
    except Exception as e:
        STATE["error"] = str(e)[:200]
        trace("USAGE build", "ERR", 0, str(e)[:120])
    finally:
        STATE["busy"] = False

def tool_usage_build(**kw):
    threading.Thread(target=build_usage, daemon=True).start()
    return "индекс строится в фоне; прогресс — usage_state"

def tool_usage_state(**kw):
    if STATE["busy"]:
        return "идёт построение: %d/%d файлов, пока %d ссылок" % (STATE["done"], STATE["total"], STATE["links"])
    if STATE["error"]:
        return "ошибка последнего построения: %s" % STATE["error"]
    if STATE["finished"]:
        return "индекс готов (%s): %d ссылок. Спрашивай models_where" % (STATE["finished"], STATE["links"])
    return "индекс ещё не строили. Скажи: usage_build"

def tool_models_where(q="", limit=30, **kw):
    try:
        c = _db()
        total = c.execute("SELECT COUNT(*) FROM usage").fetchone()[0]
        if not total:
            c.close()
            return "индекс пуст или не построен — скажи: usage_build, и подожди"
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
    except Exception as e:
        return "ошибка: %s — если индекс строится прямо сейчас, подожди минуту" % e

TOOLS = [
    {"name": "models_where", "desc": "Показать сборки, в которых используется модель/деталь", "params": {"q": "имя или слово", "limit": "сколько строк"}, "approval": False, "fn": tool_models_where},
    {"name": "usage_build", "desc": "Построить/обновить индекс «где используется»", "params": {}, "approval": False, "fn": tool_usage_build},
    {"name": "usage_state", "desc": "Прогресс построения индекса: сколько файлов прошло, сколько ссылок", "params": {}, "approval": False, "fn": tool_usage_state},
]