# -*- coding: utf-8 -*-
"""SIMILAR: поиск похожих Creo-моделей по эмбеддингам имен (спека 30).
Автоподключается через tools_registry.load_all() как блок <similar_tools>."""
import numpy as np
from core import log, embed, db
import scanner

MAT = None   # np.ndarray (N,768) — матрица эмбеддингов моделей
ROWS = []    # [(name, path, emb_blob), ...]

def reload_model_matrix():
    """Перезагружает матрицу model_embs (аналог KN.reload_matrix для chunks)."""
    global MAT, ROWS
    try:
        c = db(); ROWS = c.execute(
            "SELECT m.name, m.path, e.emb FROM models m JOIN model_embs e ON e.name=m.name"
        ).fetchall(); c.close()
        MAT = np.stack([np.frombuffer(r[2], np.float32) for r in ROWS]) if ROWS else None
        log("similar: матрица %d моделей" % len(ROWS))
    except Exception as ex:
        log("similar err: %s" % ex); MAT = None; ROWS = []

# Создаём таблицу и загружаем при старте
try:
    scanner.init_tables(); reload_model_matrix()
except Exception as ex:
    log("similar init err: %s" % ex)

def find_similar(name="", q="", top=10):
    """Поиск похожих моделей. name — точное имя модели (без пути);
    q — поисковый запрос. Возвращает список {name, path, score%}."""
    if not name and not q:
        return [{"error": "укажите name (имя модели) или q (запрос)"}]
    # вектор искомого
    qv = None
    if name:
        nm = name.lower()
        c = db()
        r = c.execute("SELECT e.emb FROM model_embs e WHERE e.name=?", (nm,)).fetchone()
        c.close()
        if r:
            qv = np.frombuffer(r[2], np.float32)
        else:
            e = embed(nm)
            if not e:
                return [{"error": "embed не ответил для '%s'" % nm}]
            qv = np.array(e, np.float32)
    else:
        e = embed(q)
        if not e:
            return [{"error": "embed не ответил для запроса"}]
        qv = np.array(e, np.float32)
    # косинусное сходство с матрицей всех моделей
    if not MAT or not ROWS:
        return [{"error": "model_embs пуста — запустите индексацию model_embs"}]
    sim = MAT @ qv / (np.linalg.norm(MAT, axis=1) * np.linalg.norm(qv) + 1e-9)
    idx = np.argsort(sim)[::-1][:top]
    return [{"name": ROWS[i][0], "path": ROWS[i][1],
             "score": round(float(sim[i]) * 100, 1)} for i in idx]

TOOLS = [
    {"name": "find_similar", "desc": "Поиск похожих Creo-моделей по эмбеддингам имен",
     "params": {"name": "имя модели (напр. korpus.prt.1)", "q": "поисковый запрос", "top": "сколько результатов"},
     "approval": False, "fn": find_similar},
]
