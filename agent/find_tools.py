# -*- coding: utf-8 -*-
r"""Поиск моделей по имени и папкам; адаптивная автогруппировка относительно
корней индекса (у каждого своя структура — группировка подстраивается)."""
import re
import core
from pathlib import Path

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
        roots = core.read_roots() or (__import__('scanner').read_roots())
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


_FAMRUN = re.compile(rb"[A-Za-z0-9_\-]{3,}")

def _fam_instances(dirp, gen):
    gl = gen.lower()
    res = []
    for ip in dirp.iterdir():
        if not ip.is_file(): continue
        low = ip.name.lower()
        if not re.search(r"\.(prt|xpr)(\.\d+)?$", low): continue
        base = re.sub(r"\.(prt|xpr)(\.\d+)?$", "", low)
        if base == gl: continue
        if ("<%s>" % gl) in low or base.startswith(gl + "-") or base.startswith(gl + "_"):
            res.append(ip)
    return sorted(res, key=lambda p: p.name)

def _fam_row(name, gen):
    base = re.sub(r"\.(prt|xpr)(\.\d+)?$", "", name, flags=re.I)
    base = re.sub(r"<%s>$" % re.escape(gen), "", base, flags=re.I)
    return base

def _fam_parse(gp):
    gen = re.sub(r"\.(prt|xpr)(\.\d+)?$", "", gp.name, flags=re.I)
    data = gp.read_bytes()
    strs = {m.group(0).decode().lower() for m in _FAMRUN.finditer(data)}
    rows, ghost = [], []
    for ip in _fam_instances(gp.parent, gen):
        row = _fam_row(ip.name, gen)
        (rows if row.lower() in strs else ghost).append(row)
    rows = sorted(set(rows)); ghost = sorted(set(ghost))
    # вложенная таблица = строка со своими инстансами, отличными от инстансов верхнего generic
    nested = []
    for r in rows:
        own = _fam_instances(gp.parent, r)
        top = _fam_instances(gp.parent, gen)
        top_basenames = {Path(p.name).stem.lower() for p in top}
        if own and not all(Path(p.name).stem.lower() in top_basenames for p in own):
            nested.append(r)
    # строки вида gen-prefix без файлов — вероятные вложенные таблицы без инстансов
    missing_nested = sorted(x for x in strs
                            if x != gen.lower() and not re.fullmatch(r"d\d+", x)
                            and x.startswith(gen.lower() + "-")
                            and not _fam_instances(gp.parent, x)
                            and not any(r.lower() == x for r in rows))
    missing_plain = sorted(x for x in strs
                           if x != gen.lower() and not re.fullmatch(r"d\d+", x)
                           and x.startswith(gen.lower() + "-")
                           and x not in missing_nested
                           and not _fam_instances(gp.parent, x)
                           and not any(r.lower() == x for r in rows))
    ghost = [g for g in ghost if g != gen.lower()]
    return {"generic": gen, "rows": rows, "nested": nested,
            "missing_nested": missing_nested, "missing_plain": missing_plain, "ghost": ghost}

def tool_family_parse(q="", **kw):
    q = (q or "").strip()
    if not q: return "укажи имя generic или путь к .prt"
    p = Path(q)
    if not p.exists():
        c = core.db()
        row = c.execute("SELECT path FROM models WHERE LOWER(name)=? AND ext IN ('prt','xpr')", (q.lower() + ".prt",)).fetchone() \
              or c.execute("SELECT path FROM models WHERE LOWER(name) LIKE ? AND ext IN ('prt','xpr') LIMIT 1", (q.lower() + "%",)).fetchone()
        c.close()
        if not row: return "не нашёл generic: %s" % q
        p = Path(row[0])
    r = _fam_parse(p)
    out = ["GENERIC %s: строк %d (вложенных таблиц %d)" % (r["generic"], len(r["rows"]), len(r["nested"]))]
    out += ["  - %s%s" % (x, "  <- вложенная таблица" if x in r["nested"] else "") for x in r["rows"][:40]]
    if len(r["rows"]) > 40: out.append("  …и ещё %d" % (len(r["rows"]) - 40))
    if r["nested"]: out.append("вложенные таблицы с инстансами: %s" % ", ".join(r["nested"]))
    if r["missing_nested"]: out.append("вложенные таблицы БЕЗ инстансов: %s" % ", ".join(r["missing_nested"]))
    if r["missing_plain"]: out.append("строки без файлов: %s" % ", ".join(r["missing_plain"][:10]))
    if r["ghost"]: out.append("файлы без строки в бинарнике: %s" % ", ".join(r["ghost"][:10]))
    return "\n".join(out)

if not any(t.get("name") == "family_parse" for t in TOOLS):
    TOOLS.append({"name": "family_parse", "desc": "Таблица семейств без сессии Creo: строки, вложенные таблицы, строки без файлов (байт-парсер, оба именования)", "params": {"q": "имя generic или путь"}, "approval": False, "fn": tool_family_parse})
