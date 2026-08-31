# -*- coding: utf-8 -*-
r"""Поиск по отсканированным моделям Creo: сколько и каких изделий есть по всем папкам."""
import re
import core

def _query(q, ext):
    toks = [t.lower() for t in re.findall(r"[A-Za-zА-Яа-я0-9][A-Za-zА-Яа-я0-9.-]{2,}", q or "") if len(t) >= 3]
    conds, args = [], []
    if toks:
        conds.append("(" + " OR ".join(["name LIKE ?"] * len(toks)) + ")")
        args += ["%" + t + "%" for t in toks]
    if ext:
        conds.append("ext = ?"); args.append(ext.lower().strip(". "))
    return ((" WHERE " + " AND ".join(conds)) if conds else ""), args

def tool_models_find(q="", ext="", limit=30, **kw):
    where, args = _query(q, ext)
    c = core.db()
    rows = c.execute("SELECT name, ext, path FROM models" + where + " ORDER BY name LIMIT 20000", args).fetchall()
    c.close()
    seen = {}
    for n, e, p in rows:
        base = re.sub(r"\.\d+$", "", n)
        if base not in seen:
            seen[base] = (base, e, p)
    uniq = sorted(seen.values())
    if not uniq:
        return "по запросу '%s' среди отсканированных моделей ничего не найдено" % (q or ext)
    show = uniq[:int(limit) or 30]
    out = ["'%s'%s: найдено %d (показаны %d):" % (q or "все модели", (" [" + ext + "]") if ext else "", len(uniq), len(show))]
    out += ["- %s  (%s)  %s" % (b, e, p) for b, e, p in show]
    if len(uniq) > len(show):
        out.append("...и ещё %d. Уточни запрос." % (len(uniq) - len(show)))
    return "\n".join(out)

def tool_models_stats(**kw):
    c = core.db()
    rows = c.execute("SELECT ext, COUNT(*) FROM models GROUP BY ext ORDER BY 2 DESC").fetchall()
    c.close()
    return "всего моделей: %d; по типам: %s" % (sum(r[1] for r in rows), ", ".join("%s=%d" % r for r in rows))

TOOLS = [
    {"name": "models_find", "desc": "Найти модели Creo по ключевым словам во всех папках: сколько и список (рычаги, держатели форм, механизмы воронок)", "params": {"q": "ключевые слова", "ext": "prt/asm/drw (необязательно)", "limit": "сколько строк"}, "approval": False, "fn": tool_models_find},
    {"name": "models_stats", "desc": "Сколько всего моделей отсканировано, разбивка по типам", "params": {}, "approval": False, "fn": tool_models_stats},
]