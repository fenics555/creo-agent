# -*- coding: utf-8 -*-
r"""
ТРАНСФОРМЕР v12 — БЛОК ПАМЯТИ (memory_tools.py)
История диалогов, стратегия КБ, избранное, каталог ошибок, PROVEN.
"""
import re, json, datetime, threading
from core import log, db, REPO

try:
    import scanner
except Exception:
    scanner = None

STRATEGY = REPO / "strategy.md"
FAV = REPO / "Избранное"; ERR = REPO / "Ошибки"

def init():
    c = db()
    c.execute("CREATE TABLE IF NOT EXISTS history(id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, q TEXT, a TEXT, sources TEXT, verdict TEXT, client TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS skill_usage(path TEXT, client TEXT, ts TEXT, cnt INTEGER, UNIQUE(path,client))")
    c.commit(); c.close()
init()

def log_dialog(q, a, srcs, client):
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    try:
        c = db()
        c.execute("INSERT INTO history(ts,q,a,sources,verdict,client) VALUES(?,?,?,?,?,?)", (ts, q, a, json.dumps(srcs, ensure_ascii=False), "ok", client))
        for s in srcs:
            if s.get("path", "").startswith(str(REPO)):
                c.execute("INSERT INTO skill_usage(path,client,ts,cnt) VALUES(?,?,?,1) ON CONFLICT(path,client) DO UPDATE SET cnt=cnt+1,ts=?", (s["path"], client, ts, ts))
        c.commit(); c.close()
    except Exception as e:
        log("memory err: %s" % e)

def history_block(q, limit=4):
    toks = [t for t in re.findall(r"[A-Za-zА-Яа-я0-9][A-Za-zА-Яа-я0-9.-]{2,}", q)][:5]
    if not toks: return ""
    c = db(); rows = []
    for t in toks:
        rows += c.execute("SELECT ts,q,a FROM history WHERE q LIKE ? OR a LIKE ? ORDER BY id DESC LIMIT 3", ("%" + t + "%", "%" + t + "%")).fetchall()
    c.close(); seen = set(); out = []
    for ts, q_, a_ in rows:
        if q_ in seen: continue
        seen.add(q_); out.append("[%s] В: %s\n   О: %s" % (ts[:10], q_, a_[:300]))
        if len(out) >= limit: break
    return "[ИЗ ИСТОРИИ ДИАЛОГОВ]:\n" + "\n".join(out) if out else ""

def strategy_read():
    if not STRATEGY.exists():
        STRATEGY.write_text("# СТРАТЕГИЯ КБ\n\n## Активные направления\n- ТРАНСФОРМЕР v12, инструменты, скиллы\n\n## Закрытые направления\n- (пусто)\n", encoding="utf-8")
    return STRATEGY.read_text(encoding="utf-8")

def proven():
    c = db()
    rows = c.execute("SELECT path,COUNT(DISTINCT client) n FROM skill_usage GROUP BY path HAVING n>=3 ORDER BY n DESC").fetchall()
    c.close()
    return "\n".join("✓ %s (%d чел.)" % (p, n) for p, n in rows) or "пока нет скиллов с 3+ пользователями"

def fav_path(client): return FAV / ("SKILL_favorites_%s.md" % client)

def tool_history(query="", **kw):
    return history_block(query) or "история пуста"

def tool_strategy(**kw):
    return strategy_read()

def tool_proven(**kw):
    return proven()

def tool_fav_show(client="server", **kw):
    p = fav_path(client)
    return p.read_text(encoding="utf-8") if p.exists() else "избранное пусто"

def tool_fav_add(text="", client="server", **kw):
    if not text: return "укажите текст"
    FAV.mkdir(exist_ok=True)
    with open(fav_path(client), "a", encoding="utf-8") as f: f.write("- [FAV] %s\n" % text)
    if scanner: threading.Thread(target=scanner.index_all, daemon=True).start()
    return "добавлено в избранное"

def tool_save_error(client="server", **kw):
    c = db()
    rows = c.execute("SELECT q,a FROM history WHERE client=? ORDER BY id DESC LIMIT 6", (client,)).fetchall()
    c.close()
    err = None
    for q, a in rows:
        if any(k in q.lower() for k in ("error", "ошибк", "invalid", "не удается", "не найден")): err = (q, a); break
    if not err: return "не нашёл ошибку в последних диалогах"
    q, a = err; ERR.mkdir(exist_ok=True)
    name = "ERR_%s.md" % datetime.datetime.now().strftime("%y%m%d_%H%M")
    (ERR / name).write_text("# ОШИБКА: %s\n\n## Симптом\n%s\n\n## Лечение\n%s\n" % (q[:80], q[:1500], a[:2000]), encoding="utf-8")
    if scanner: threading.Thread(target=scanner.index_all, daemon=True).start()
    return "ошибка записана: %s" % name
    
TOOLS = [
    {"name": "history_search", "desc": "Поиск в истории прошлых диалогов", "params": {"query": "о чём"}, "approval": False, "fn": tool_history},
    {"name": "strategy_read", "desc": "Стратегия КБ: активные/закрытые направления", "params": {}, "approval": False, "fn": tool_strategy},
    {"name": "proven_show", "desc": "Скиллы, проверенные 3+ пользователями", "params": {}, "approval": False, "fn": tool_proven},
    {"name": "fav_show", "desc": "Избранное клиента", "params": {}, "approval": False, "fn": tool_fav_show},
    {"name": "fav_add", "desc": "Добавить в избранное", "params": {"text": "текст"}, "approval": False, "fn": tool_fav_add},
    {"name": "save_error", "desc": "Сохранить последнюю ошибку в каталог", "params": {}, "approval": False, "fn": tool_save_error},
]