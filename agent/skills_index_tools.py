# -*- coding: utf-8 -*-
r"""skills_index_tools — мост индекса скиллов к живому агенту (рука 3, витрин-data).

Read-only: витрина/агент зовёт поиск по смыслу и статус индекса. Авто-подхват через
реестр TOOLS (как copy_tools). Сам поиск тянет Ollama только в рантайме вызова.
Канон: approval=False (чтение), ничего не пишет; перестройка — отдельно (build/gui).
"""
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE / "skills_index"))
import skills_index as eng  # noqa: E402


def search_preview(query="", top=5, **kw):
    """Витрина: top-N скиллов по смыслу. read-only, ничего не пишет."""
    q = (query or "").strip()
    if not q:
        return {"error": "нужен запрос"}
    if not eng.DB.exists():
        return {"error": "индекса нет — сначала skills_index.py build"}
    model = eng.settings().get("model") or "nomic-embed-text-v2-moe:latest"
    try:
        qv = eng.embed(model, ["search_query: " + q])[0]
    except Exception as e:
        return {"error": "эмбеддинг: %s" % e}
    c = eng.ro(eng.DB)
    rows = c.execute("SELECT path,head,vec FROM chunks").fetchall(); c.close()
    scored = sorted(((eng.cos(qv, eng.vunpack(v)), p, h) for p, h, v in rows), reverse=True)
    seen, out = set(), []
    for s, p, h in scored:
        if p in seen:
            continue
        seen.add(p)
        out.append({"score": round(s, 3), "path": p, "head": (h or "")[:140]})
        if len(out) >= max(1, int(top)):
            break
    return {"query": q, "model": model, "results": out, "total": len(out)}


def status_preview(**kw):
    """Витрина: состояние индекса (read-only)."""
    if not eng.DB.exists():
        return {"error": "индекса нет", "hint": "skills_index.py build"}
    c = eng.ro(eng.DB)
    meta = dict(c.execute("SELECT k,v FROM meta").fetchall())
    nch = c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    c.close()
    return {"version": meta.get("version", "?"), "model": meta.get("model", "?"),
            "created": meta.get("created", "?"), "chunks": nch}


TOOLS = [
    {"name": "skills_search", "desc": "Поиск скилла/инструмента/закона по СМЫСЛУ (эмбеддинги)",
     "params": {"query": "текст задачи", "top": "сколько (по умолч. 5)"},
     "approval": False, "fn": search_preview},
    {"name": "skills_status", "desc": "Состояние индекса скиллов (версия, чанков, модель)",
     "params": {}, "approval": False, "fn": status_preview},
]
