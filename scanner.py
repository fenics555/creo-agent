# -*- coding: utf-8 -*-
r"""
АГЕНТ v12 — СКАНЕР (scanner.py)
Индекс текстов (files/chunks) и моделей Creo (models).
done растёт только на успехе; исчезнувшие файлы вычищаются.
"""
import os, re, time, threading
from pathlib import Path
import numpy as np
import core
from core import log, embed, clean, chunker, is_creo, is_excluded, read_roots, db, trace
import settings
try:
    from pypdf import PdfReader
    HAS_PYPDF = True
except Exception:
    HAS_PYPDF = False
try:
    import knowledge_tools as KN
except Exception:
    KN = None

def read_roots():
    """Список корней для скана из kb_roots.txt или scan_roots из settings."""
    try:
        from pathlib import Path
        import settings
        r = Path(__file__).parent / "kb_roots.txt"
        if r.exists():
            lines = r.read_text(encoding="utf-8").splitlines()
            return [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
        raw = settings.get("scan_roots") or []
        return raw if isinstance(raw, list) else [raw]
    except Exception:
        return []

def _pats():
    """Паттерны исключения из kb_exclude.txt."""
    try:
        from pathlib import Path
        p = Path(__file__).parent / "kb_exclude.txt"
        if p.exists():
            return [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith("#")]
        return []
    except Exception:
        return []

def is_excluded(path, pats):
    """Проверка исключения по паттернам."""
    p = path.lower()
    return any(pat.lower() in p for pat in (pats or []))


EXTS = {".htm", ".html", ".md", ".txt", ".py", ".xml", ".json", ".csv",
        ".pro", ".dtl", ".pnt", ".pdf", ".mil", ".drl"}
STATE = {"indexing": False, "done": 0, "total": 0, "errors": 0, "fscan": False, "fcount": 0}

def init_tables():
    c = db()
    c.execute("CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY, mtime REAL, size INTEGER)")
    c.execute("CREATE TABLE IF NOT EXISTS chunks(id INTEGER PRIMARY KEY, path TEXT, text TEXT, emb BLOB)")
    c.execute("CREATE TABLE IF NOT EXISTS models(name TEXT, ext TEXT, path TEXT)")
    c.commit(); c.close()

def state():
    c = db()
    try:
        nf = c.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        nc = c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        nm = c.execute("SELECT COUNT(*) FROM models").fetchone()[0]
    except Exception:
        nf = nc = nm = 0
    c.close()
    return dict(files=nf, chunks=nc, models=nm, indexing=STATE["indexing"],
                done=STATE["done"], total=STATE["total"])

def read_file_text(f):
    if f.suffix.lower() == ".pdf":
        if not HAS_PYPDF: return None
        try:
            r = PdfReader(str(f))
            return "\n".join(p.extract_text() or "" for p in r.pages)
        except Exception as e:
            log("PDF err %s: %s" % (f.name, e)); return None
    try: return f.read_text(encoding="utf-8", errors="ignore")
    except Exception: return None

def _pats():
    from pathlib import Path as _P
    import core as _c
    pats = []
    for base in (_c.BASE, _c.REPO):
        f = _P(base) / "kb_exclude.txt"
        if f.exists():
            for ln in f.read_text(encoding="utf-8", errors="ignore").splitlines():
                ln = ln.strip()
                if ln and not ln.startswith("#"):
                    pats.append(ln)
            break
    return pats

def index_all():
    if STATE["indexing"]: return
    STATE.update(indexing=True, done=0, total=0, errors=0)
    t0 = time.time(); c = None
    try:
        c = db(); seen, todo = set(), []; pats = _pats()
        max_mb = settings.get("max_file_mb") or 4
        for root in read_roots():
            rp = Path(root)
            if not rp.exists(): continue
            for f in rp.rglob("*"):
                try:
                    if f.is_file() and f.suffix.lower() in EXTS \
                       and f.stat().st_size < max_mb * 1024 * 1024 \
                       and not is_excluded(f, pats):
                        seen.add(str(f)); st = f.stat()
                        m = c.execute("SELECT mtime,size FROM files WHERE path=?", (str(f),)).fetchone()
                        if not m or m[0] != st.st_mtime or m[1] != st.st_size: todo.append(f)
                except Exception: pass
        for (p,) in c.execute("SELECT path FROM files").fetchall():
            if p not in seen:
                c.execute("DELETE FROM chunks WHERE path=?", (p,))
                c.execute("DELETE FROM files WHERE path=?", (p,))
        STATE["total"] = len(todo)
        cs, ov = settings.get("chunk_size") or 1500, settings.get("chunk_overlap") or 200
        for f in todo:
            c.execute("DELETE FROM chunks WHERE path=?", (str(f),))
            okf = True; txt = read_file_text(f)
            if txt is not None:
                tc = clean(txt)
                if tc:
                    for ch in chunker(tc, cs, ov):
                        e = embed(ch)
                        if e is None:
                            okf = False; STATE["errors"] += 1; break
                        c.execute("INSERT INTO chunks(path,text,emb) VALUES(?,?,?)",
                                  (str(f), ch, np.array(e, np.float32).tobytes()))
            if okf:
                st = f.stat()
                c.execute("REPLACE INTO files VALUES(?,?,?)", (str(f), st.st_mtime, st.st_size))
                STATE["done"] += 1
            else:
                STATE["errors"] += 1
            c.commit()
        c.commit()
        log("индекс: %d файлов за %.0f сек, ошибок %d" % (STATE["done"], time.time() - t0, STATE["errors"]))
        trace("SCANNER index_all", "OK", int((time.time() - t0) * 1000))
    except Exception as e:
        log("ОШИБКА индекса: %s" % e)
        trace("SCANNER index_all", "ERR", int((time.time() - t0) * 1000))
    finally:
        STATE["indexing"] = False
        if c: c.close()
    if KN: KN.reload_matrix()

def scan_models():
    if STATE["fscan"]: return
    STATE.update(fscan=True); t0 = time.time(); rows = []; c = None
    try:
        c = db(); c.execute("DELETE FROM models"); pats = _pats()
        for root in read_roots():
            rp = Path(root)
            if not rp.exists(): continue
            for dp, dn, fns in os.walk(rp):
                dn[:] = [d for d in dn if not is_excluded(os.path.join(dp, d) + "/", pats)]
                for fn in fns:
                    full = os.path.join(dp, fn)
                    if is_creo(fn) and not is_excluded(full, pats):
                        m = re.search(r"\.(prt|asm|drw|frm|sec|lay)(?:\.\d+)?$", fn.lower())
                        rows.append((fn.lower(), m.group(1) if m else "", full))
        c.executemany("INSERT INTO models(name,ext,path) VALUES(?,?,?)", rows); c.commit()
        trace("SCANNER scan_models", "OK", int((time.time() - t0) * 1000), "%d моделей" % len(rows))
    except Exception as e:
        log("ОШИБКА скана: %s" % e)
    finally:
        STATE["fscan"] = False; STATE["fcount"] = len(rows)
        if c: c.close()

def start_threads():
    init_tables()
    threading.Thread(target=index_all, daemon=True).start()
    threading.Thread(target=lambda: (time.sleep(30), scan_models()), daemon=True).start()

def name_search(q, limit=8):
    toks = [t for t in re.findall(r"[A-Za-zА-Яа-я0-9][A-Za-zА-Яа-я0-9.-]{3,}", q or "") if len(t) >= 3]
    if not toks: return []
    c = db(); hits = []
    for t in toks:
        for (p,) in c.execute("SELECT path FROM models WHERE name LIKE ? LIMIT 6", ("%" + t.lower() + "%",)).fetchall():
            if p not in hits: hits.append(p)
    c.close()
    return hits[:limit]

def dup_report():
    c = db()
    rows = c.execute("SELECT name,COUNT(*) c FROM models GROUP BY name HAVING c>1 ORDER BY c DESC LIMIT 40").fetchall()
    if not rows: c.close(); return "Дублей не найдено."
    out = ["ДУБЛИ ИМЁН:"]
    for n, _ in rows:
        out.append("• " + n)
        for (p,) in c.execute("SELECT path FROM models WHERE name=?", (n,)).fetchall(): out.append("     " + p)
    c.close()
    return "\n".join(out)
# v14-fix-db: БД всегда рядом с этим файлом, независимо от core.BASE
import sqlite3 as _sq
from pathlib import Path as _P
def db():
    c = _sq.connect(str(_P(__file__).resolve().parent / "data" / "agent.sqlite"), timeout=10)
    c.execute("PRAGMA journal_mode=WAL")
    return c

# v14-fix-excl: is_excluded/_pats — понимают Path и читают kb_exclude.txt
import fnmatch as _fm2
from pathlib import Path as _P2
def _pats():
    try:
        p = _P2(__file__).resolve().parent / "kb_exclude.txt"
        out = []
        if p.exists():
            for l in p.read_text(encoding="utf-8").splitlines():
                l = l.strip()
                if l and not l.startswith("#"): out.append(l)
        return out
    except Exception:
        return []
def is_excluded(path, pats):
    st = str(path).lower().replace("/", "\\")
    for pat in (pats or []):
        q = pat.lower().replace("/", "\\")
        if "*" in q:
            if _fm2.fnmatch(st.split("\\")[-1], q) or _fm2.fnmatch(st, q): return True
        elif q in st:
            return True
    return False
