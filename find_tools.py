# -*- coding: utf-8 -*-
r"""Поиск моделей по имени и папкам; адаптивная автогруппировка относительно
корней индекса (у каждого своя структура — группировка подстраивается)."""
import re
import core

SYNONYMS = {"турновер": ["переворот", "turnover"], "turnover": ["переворот"],
            "ворошитель": ["переворот"], "держатель": ["держател"]}

def _tokens(q):
    toks = [t.lower() for t in re.findall(r"[A-Za-zА-Яа-я0-9][A-Za-zА-Яа-я0-9.-]{2,}", q or "") if len(t) >= 3]
    out = []
    for t in toks:
        out.append(t)
        for k, syns in SYNONYMS.items():
            if t.startswith(k) or k.startswith(t):
                out += syns
    return list(dict.fromkeys(out))

def _query(q, ext):
    toks = _tokens(q)
    conds, args = [], []
    if toks:
        per = []
        for t in toks:
            per.append("(name LIKE ? OR path LIKE ?)")
            args += ["%" + t + "%", "%" + t + "%"]
        conds.append("(" + " OR ".join(per) + ")")
    if ext:
        conds.append("ext = ?"); args.append(ext.lower().strip("."))
    return ((" WHERE " + " AND ".join(conds)) if conds else ""), args

def _rel_parts(path):
    low = str(path).replace("\\", "/").lower()
    best = ""
    try:
        roots = core.read_roots()
    except Exception:
        roots = []
    for r in roots:
        rl = str(r).replace("\\", "/").lower().rstrip("/")
        if low.startswith(rl + "/") and len(rl) > len(best):
            best = rl
    rel = str(path)[len(best) + 1:] if best else str(path)
    return [p for p in rel.replace("\\", "/").split("/") if p]

def _groups(uniq, depth):
    folders = {}
    for b, e, p in uniq:
        body = _rel_parts(p)[:-1] or ["?"]
        key = "/".join(body[:depth]) if len(body) > depth else "/".join(body)
        folders[key] = folders.get(key, 0) + 1
    return folders

def tool_models_find(q="", ext="", limit=20, **kw):
    where, args = _query(q, ext)
    c = core.db()
    rows = c.execute("SELECT name, ext, path FROM models " + where + " ORDER BY path LIMIT 5000", args).fetchall()
    c.close()
    seen = {}
    for n, e, p in rows:
        key = (re.sub(r"\.\d+$", "", n), e)
        if key not in seen:
            seen[key] = (key[0], e, p)
    uniq = sorted(seen.values(), key=lambda x: x[2])
    if not uniq:
        return "по '%s' ничего не нашлось (ищу по именам файлов И папок). Попробуй другое слово." % (q or ext)
    folders = _groups(uniq, 2)
    if len(folders) > 40:
        folders = _groups(uniq, 1)
    elif len(folders) < 3:
        folders = _groups(uniq, 3)
    out = ["'%s': найдено %d моделей в %d категориях (автогруппировка)." % (q or "все", len(uniq), len(folders))]
    out += ["📁 %s — %d" % (f, n) for f, n in sorted(folders.items(), key=lambda x: -x[1])[:12]]
    out.append("файлы:")
    lim = int(limit) or 20
    out += ["- %s (%s) %s" % (b, e, p) for b, e, p in uniq[:lim]]
    if len(uniq) > lim:
        out.append("…и ещё %d. Уточни категорию или имя." % (len(uniq) - lim))
    out.append("Дальше просто напиши имя модели или «вот этот» — продолжу работу с ней.")
    return "\n".join(out)

def tool_models_stats(**kw):
    c = core.db()
    rows = c.execute("SELECT ext, COUNT(*) FROM models GROUP BY ext ORDER BY 2 DESC").fetchall()
    c.close()
    return "всего моделей: %d; по типам: %s" % (sum(r[1] for r in rows), ", ".join("%s=%d" % r for r in rows))

TOOLS = [
    {"name": "models_find", "desc": "Список моделей/категорий по вопросу «какие турноверы/держатели есть»: поиск по именам и папкам, адаптивная автогруппировка", "params": {"q": "ключевые слова", "ext": "prt/asm/drw", "limit": "сколько файлов"}, "approval": False, "fn": tool_models_find},
    {"name": "models_stats", "desc": "Сколько всего моделей отсканировано, разбивка по типам", "params": {}, "approval": False, "fn": tool_models_stats},
]
