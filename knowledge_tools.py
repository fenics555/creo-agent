# -*- coding: utf-8 -*-
r"""
ТРАНСФОРМЕР v12 — БЛОК ЗНАНИЙ (knowledge_tools.py)
Векторный поиск по БЗ, чтение файлов, сохранение скиллов.
"""
import threading
from pathlib import Path
import numpy as np
import core
from core import log, embed, REPO
import settings

try:
    import scanner
except Exception:
    scanner = None

MAT = None; ROWS = []

def reload_matrix():
    global MAT, ROWS
    try:
        c = core.db()
        ROWS = c.execute("SELECT path, text, emb FROM chunks").fetchall()
        c.close()
        MAT = np.stack([np.frombuffer(r[2], np.float32) for r in ROWS]) if ROWS else None
        log("knowledge: матрица %d фрагментов" % len(ROWS))
    except Exception as e:
        log("knowledge err: %s" % e)

reload_matrix()

def tool_search(query="", **kw):
    if not query: return "пустой запрос"
    if MAT is None: return "база не загружена"
    e = embed(query)
    if e is None: return "эмбеддинг не ответил (Ollama?)"
    qv = np.array(e, np.float32)
    sim = MAT @ qv / (np.linalg.norm(MAT, axis=1) * np.linalg.norm(qv) + 1e-9)
    raw = sim.copy()
    boost = np.array([(settings.get("repo_boost") or 1.2) if (r[0].startswith(str(REPO)) and raw[i] > (settings.get("repo_boost_min_sim") or 0.2)) else 1.0 for i, r in enumerate(ROWS)])
    sim = sim * boost
    out = []
    for n, i in enumerate(sim.argsort()[::-1][:(settings.get("top_chunks") or 4)]):
        out.append("[%d] %s\n%s" % (n + 1, ROWS[i][0], ROWS[i][1][:settings.get("chunk_chars") or 900]))
    return "\n\n".join(out) or "пусто"

def tool_read(path="", **kw):
    if not path: return "укажите path"
    p = Path(path)
    if not p.exists(): return "нет файла %s" % path
    return p.read_text(encoding="utf-8", errors="ignore")[:6000]

def tool_save(name="", content="", **kw):
    if not name or not content: return "нужны name и content"
    p = REPO / ("SKILL_" + name + ".md")
    p.write_text(content, encoding="utf-8")
    if scanner: threading.Thread(target=scanner.index_all, daemon=True).start()
    return "скилл сохранён: %s, переиндексация запущена" % p
    
TOOLS = [
    {"name": "search_kb", "desc": "Поиск по базе знаний КБ (скиллы, ГОСТы, docs)", "params": {"query": "запрос"}, "approval": False, "fn": tool_search},
    {"name": "read_file", "desc": "Прочитать файл целиком (до 6000 симв.)", "params": {"path": "полный путь"}, "approval": False, "fn": tool_read},
    {"name": "save_skill", "desc": "Сохранить новый скилл в базу знаний", "params": {"name": "имя", "content": "markdown"}, "approval": True, "fn": tool_save},
]