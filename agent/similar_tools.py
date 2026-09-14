# -*- coding: utf-8 -*-
"""SIMILAR: поиск похожих Creo-моделей по эмбеддингам (спека 30)."""
import numpy as np
from core import log, embed, db
import scanner

MAT = None   # np.ndarray (N,768)
ROWS = []    # [(name, path, emb_blob), ...]

def reload_model_matrix():
    global MAT, ROWS
    try:
        c = db()
        ROWS = c.execute(
            "SELECT m.name, m.path, e.emb FROM models m JOIN model_embs e ON e.name=m.name"
        ).fetchall()
        c.close()
        if ROWS:
            MAT = np.stack([np.frombuffer(r[2], np.float32) for r in ROWS])
            log("similar: матрица %d моделей" % len(ROWS))
        else:
            MAT = None
    except Exception as ex:
        log("similar err: %s" % ex)
        MAT = None
        ROWS = []

try:
    scanner.init_tables()
    reload_model_matrix()
except Exception as ex:
    log("similar init err: %s" % ex)

def find_similar(name="", q="", top=10):
    try:
        top = int(top)
    except:
        top = 10
        
    qv = None
    if name:
        c = db()
        model = c.execute("SELECT path FROM models WHERE name=?", (name,)).fetchone()
        c.close()
        if model:
            path = model[0]
            c = db()
            rows = c.execute("SELECT emb FROM chunks WHERE path LIKE ?", (path + '%',)).fetchall()
            c.close()
            if rows:
                embs = [np.frombuffer(r[0], np.float32) for r in rows]
                qv = np.mean(embs, axis=0)
            else:
                return [{"error": "chunks not found for model"}]
        else:
            e = embed(name)
            if not e: return [{"error": "embed fail"}]
            qv = np.array(e, np.float32)
    elif q:
        e = embed(q)
        if not e: return [{"error": "embed fail"}]
        qv = np.array(e, np.float32)
    else:
        return [{"error": "\u0443\u043a\u0430\u0436\u0438\u0442\u0435 name \u0438\u043b\u0438 q"}]

    if MAT is None or len(MAT) == 0:
        return [{"error": "matrix empty"}]

    # Cosine similarity
    norm_mat = np.linalg.norm(MAT, axis=1)
    norm_qv = np.linalg.norm(qv)
    sim = (MAT @ qv) / (norm_mat * norm_qv + 1e-9)
    
    idx = np.argsort(sim)[::-1][:top]
    
    res = []
    for i in idx:
        res.append({
            "name": ROWS[i][0],
            "score": round(float(sim[i]) * 100, 1),
            "path": ROWS[i][1]
        })
    return res

TOOLS = [{
    "name": "find_similar",
    "desc": "\u041f\u043e\u0438\u0441\u043a \u043f\u043e\u0445\u043e\u0436\u0438\u0445 \u043c\u043e\u0434\u0435\u043b\u0435\u0439 \u043f\u043e \u044d\u043c\u0431\u0435\u0434\u0434\u0438\u043d\u0433\u0430\u043c",
    "params": {"name": "\u0438\u043c\u044f", "q": "\u0437\u0430\u043f\u0440\u043e\u0441", "top": "\u0441\u043a\u043e\u043b\u044c"},
    "fn": find_similar
}]
