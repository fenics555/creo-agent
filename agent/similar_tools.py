# -*- coding: utf-8 -*-
import numpy as np
import os
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
    scanner.init_db_schema()
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
        r_emb = c.execute("SELECT emb FROM model_embs WHERE name=?", (name,)).fetchone()
        if r_emb:
            qv = np.frombuffer(r_emb[0], np.float32)
        
        if qv is None:
            model = c.execute("SELECT path FROM models WHERE name=?", (name,)).fetchone()
            if model:
                path = model[0]
                rows = c.execute("SELECT emb FROM chunks WHERE path LIKE ?", (path + '%',)).fetchall()
                if not rows:
                    alt_path = None
                    if path.startswith("Z:"): alt_path = "D:" + path[2:]
                    elif path.startswith("D:"): alt_path = "Z:" + path[2:]
                    if alt_path:
                        rows = c.execute("SELECT emb FROM chunks WHERE path LIKE ?", (alt_path + '%',)).fetchall()
                if not rows:
                    fname = os.path.basename(path)
                    rows = c.execute("SELECT emb FROM chunks WHERE path LIKE ?", ('%' + fname,)).fetchall()
                
                if rows:
                    embs = [np.frombuffer(row[0], np.float32) for row in rows]
                    qv = np.mean(embs, axis=0)
        
        if qv is None:
            e = embed(name)
            if not e:
                c.close()
                return [{"error": "embed fail"}]
            qv = np.array(e, np.float32)
        c.close()
    elif q:
        e = embed(q)
        if not e: return [{"error": "embed fail"}]
        qv = np.array(e, np.float32)
    else:
        return [{"error": "укажите name или q"}]

    if MAT is None or len(MAT) == 0:
        return [{"error": "matrix empty"}]

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
    "desc": "Поиск похожих моделей по эмбеддингам",
    "params": {"name": "имя", "q": "запрос", "top": "сколь"},
    "fn": find_similar
}]
