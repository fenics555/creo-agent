# -*- coding: utf-8 -*-
r"""skills_index — индекс скиллов дома и ПОИСК ПО СМЫСЛУ (эмбеддинги).

Самодостаточный инструмент. Референс: repo\INDEX (PowerShell, для тестов).
Модель — nomic-embed-text-v2-moe (Ollama). Префиксы ОБЯЗАТЕЛЬНЫ: индексация
"search_document: ", поиск "search_query: ".

Своя БД: db\skills_index.db (SQLite: chunks(path,part,head,vec BLOB)+manifest+meta).
«В базу сразу не пишем»: сборка в db\staging_<дата>.db, publish = os.replace; прежняя
БД копируется в versions\, чистка по keep_versions. Инкремент: неизменённые файлы
(size+mtime) переиспользуют vec.

Запуск:  build [--full] [--keep N] | search <запрос> [--top N] [--full] | status
"""
import argparse
import json
import os
import sqlite3
import struct
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
AGENT = HERE.parent
DB = HERE / "db" / "skills_index.db"
VERDIR = HERE / "db" / "versions"
LOGDIR = HERE / "log"
OLL = "http://127.0.0.1:11434"

# ПЕРЕНОСИМОСТЬ (15.10.2026): корни НЕ зашиты. По умолчанию — дом, найденный от себя:
#   skills_index -> tools\agent -> tools -> D:\AI (корень дома). Любой корень перекрывается
#   настройкой "roots" в settings\settings.json — тогда копия на шаре/другом ПК работает со своими путями.
DEFAULT_HOME = HERE.parents[2] if len(HERE.parents) > 2 else HERE


def _resolve_roots(s):
    """Корни корпуса: из settings roots (иначе — от расположения инструмента)."""
    home = Path(s.get("home") or DEFAULT_HOME)
    raw = s.get("roots") or {}
    out = {}
    for key, default in (("repo", home / "repo"), ("tools", home / "tools" / "agent"),
                         ("agent_settings", home / "AGENT_SETTINGS"), ("root", home)):
        out[key] = Path(raw[key]) if raw.get(key) else default
    return out


def settings():
    p = HERE / "settings" / "settings.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


# Корни корпуса (см. _resolve_roots выше): вычисляются ЗДЕСЬ — после объявления settings().
ROOTS = _resolve_roots(settings())


def log(msg):
    LOGDIR.mkdir(parents=True, exist_ok=True)
    line = "[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg)
    try:
        with open(LOGDIR / ("index_%s.log" % datetime.now().strftime("%Y-%m-%d")),
                  "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line)


def corpora_files(s):
    excl = [e.lower().replace("\\", "/") for e in s.get("exclude", [])]
    out = []
    for key in s.get("corpora", list(ROOTS)):
        r = ROOTS.get(key)
        if not r or not r.exists():
            continue
        for f in r.rglob("*"):
            if not f.is_file():
                continue
            low = str(f).replace("\\", "/").lower()
            if any(x in low for x in excl):
                continue
            nm, ext = f.name, f.suffix.lower()
            hit = (
                (key == "repo" and (nm.startswith("SKILL_") or nm.startswith(".clinerules")
                 or nm in ("MANIFEST.md", "README.md") or nm.endswith("index.md"))),
                (key == "tools" and ext in (".py", ".md")),
                (key == "agent_settings" and (ext == ".md" or nm.startswith(".clinerules"))),
                (key == "root" and (ext == ".md" or nm.startswith(".clinerules"))),
            )
            if any(hit):
                out.append(f)
    return out


def head_of(path, txt):
    lines = [l.strip() for l in txt.splitlines() if l.strip()][:4]
    return "FILE: %s\n" % path + " ".join(lines)[:200]


def chunk_text(txt, mc, ov, mp):
    parts, pos, idx = [], 0, 0
    while pos < len(txt) and idx < mp:
        parts.append((idx, txt[pos:pos + mc]))
        idx += 1
        if pos + mc >= len(txt):
            break
        pos += mc - ov
    return parts


def embed(model, texts):
    body = json.dumps({"model": model, "input": texts, "keep_alive": "30m"}).encode()
    req = urllib.request.Request(OLL + "/api/embed", data=body,
                                 headers={"Content-Type": "application/json"})
    r = json.loads(urllib.request.urlopen(req, timeout=300).read())
    return r.get("embeddings") or []


def vpack(v):
    return struct.pack("<%df" % len(v), *v)


def vunpack(b):
    return struct.unpack("<%df" % (len(b) // 4), b)


def cos(a, b):
    num = sum(x * y for x, y in zip(a, b))
    da = sum(x * x for x in a) ** 0.5
    dbb = sum(y * y for y in b) ** 0.5
    return num / (da * dbb) if da and dbb else 0.0


def new_db(p):
    c = sqlite3.connect(str(p))
    c.execute("CREATE TABLE meta(k TEXT PRIMARY KEY, v TEXT)")
    c.execute("CREATE TABLE chunks(id INTEGER PRIMARY KEY, path TEXT, part INTEGER, head TEXT, vec BLOB)")
    c.execute("CREATE TABLE manifest(path TEXT PRIMARY KEY, size INTEGER, mtime REAL)")
    c.commit()
    return c


def ro(path):
    return sqlite3.connect("file:%s?mode=ro" % str(path).replace("\\", "/"), uri=True)


def old_manifest():
    if not DB.exists():
        return {}
    try:
        c = ro(DB)
        m = {p: (s, t) for p, s, t in c.execute("SELECT path,size,mtime FROM manifest")}
        c.close()
        return m
    except Exception:
        return {}


def old_vecs(paths):
    if not DB.exists():
        return {}
    res = {}
    try:
        c = ro(DB)
        for p in paths:
            rows = c.execute("SELECT part,head,vec FROM chunks WHERE path=?", (p,)).fetchall()
            if rows:
                res[p] = rows
        c.close()
    except Exception:
        pass
    return res


# === COMMANDS (appended below) ===


def cmd_build(a):
    s = settings()
    model = a.model or s.get("model") or "nomic-embed-text-v2-moe:latest"
    mc, ov, mp = s.get("max_chars", 800), s.get("overlap", 150), s.get("max_parts", 30)
    batch, keep = s.get("batch", 32), a.keep or s.get("keep_versions", 3)
    (HERE / "db").mkdir(parents=True, exist_ok=True)
    VERDIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    staging = HERE / "db" / ("staging_%s.db" % stamp)
    files = corpora_files(s)
    log("СТАРТ build: файлов %d | модель=%s | Full=%s" % (len(files), model, a.full))
    oman = {} if a.full else old_manifest()
    sc = new_db(staging)
    reused_f = 0
    todo, todo_info = [], []
    t0 = time.time()
    for f in files:
        try:
            st = f.stat()
            txt = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        key = str(f)
        head = head_of(key, txt)
        parts = chunk_text(txt, mc, ov, mp)
        if a.full or oman.get(key) != (st.st_size, st.st_mtime):
            for idx, ch in parts:
                todo.append("search_document: " + head + "\n" + ch)
                todo_info.append((key, idx, head))
        else:
            reused_f += 1
        sc.execute("INSERT OR REPLACE INTO manifest VALUES(?,?,?)", (key, st.st_size, st.st_mtime))
    log("разбор: изменённых/новых %d, переиспользовано файлов %d" % (len(files) - reused_f, reused_f))
    if todo:
        for i in range(0, len(todo), batch):
            grp = todo[i:i + batch]
            try:
                vecs = embed(model, grp)
            except Exception as e:
                log("ошибка пачки %d: %s" % (i, e)); continue
            for k, v in enumerate(vecs):
                path, part, head = todo_info[i + k]
                sc.execute("INSERT INTO chunks(path,part,head,vec) VALUES(?,?,?,?)",
                           (path, part, head, vpack(v)))
        log("эмбеддинг: %d чанков новых" % len(todo))
    ovec = old_vecs([str(f) for f in files]) if reused_f else {}
    for p, rows in ovec.items():
        for part, head, vec in rows:
            sc.execute("INSERT INTO chunks(path,part,head,vec) VALUES(?,?,?,?)", (p, part, head, vec))
    nch = sc.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    meta = {"version": "ver_" + stamp, "model": model, "created": datetime.now().isoformat(),
            "files": len(files), "chunks": nch, "full": bool(a.full)}
    for k, v in meta.items():
        sc.execute("INSERT OR REPLACE INTO meta VALUES(?,?)", (k, str(v)))
    sc.commit(); sc.close()
    if DB.exists():
        import shutil
        try:
            shutil.copy2(str(DB), str(VERDIR / ("ver_%s.db" % stamp)))
        except Exception:
            pass
    os.replace(str(staging), str(DB))
    olds = sorted(VERDIR.glob("ver_*.db"), key=os.path.getmtime, reverse=True)[keep:]
    for o in olds:
        try: o.unlink()
        except Exception: pass
    log("ОПУБЛИКОВАНО ver_%s | файлов %d, чанков %d | %.1f с | %.1f МБ"
        % (stamp, len(files), nch, time.time() - t0, os.path.getsize(str(DB)) / 1048576))
    return 0


def cmd_search(a):
    if not DB.exists():
        print("индекса нет — сначала build"); return 2
    s = settings()
    model = a.model or s.get("model") or "nomic-embed-text-v2-moe:latest"
    q = " ".join(a.query) or ""
    try:
        qv = embed(model, ["search_query: " + q])[0]
    except Exception as e:
        print("ошибка эмбеддинга запроса: %s" % e); return 2
    c = ro(DB)
    rows = c.execute("SELECT path,head,vec FROM chunks").fetchall(); c.close()
    scored = sorted(((cos(qv, vunpack(v)), p, h) for p, h, v in rows), reverse=True)
    seen, shown = set(), 0
    for sc_, p, h in scored:
        if p in seen:
            continue
        seen.add(p); shown += 1
        print("%.3f  %s" % (sc_, p if a.full else os.path.basename(p)))
        if shown >= a.top:
            break
    return 0


def cmd_status(a):
    if not DB.exists():
        print("индекса нет"); return 2
    c = ro(DB)
    meta = dict(c.execute("SELECT k,v FROM meta").fetchall())
    nch = c.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    nf = c.execute("SELECT COUNT(*) FROM manifest").fetchone()[0]
    c.close()
    print("=== СТАТУС ИНДЕКСА СКИЛЛОВ ===")
    for k in ("version", "model", "created", "files", "chunks"):
        if k in meta:
            print("  %-8s %s" % (k, meta[k]))
    print("  файлов %d · чанков %d · размер %.1f МБ"
          % (nf, nch, os.path.getsize(str(DB)) / 1048576))
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="Индекс скиллов дома: поиск по смыслу")
    ap.add_argument("--model", default=None, help="модель эмбеддингов (иначе из настроек)")
    sub = ap.add_subparsers(dest="cmd")
    b = sub.add_parser("build"); b.add_argument("--full", action="store_true"); b.add_argument("--keep", type=int, default=None)
    q = sub.add_parser("search"); q.add_argument("query", nargs="*"); q.add_argument("--top", type=int, default=5); q.add_argument("--full", action="store_true")
    sub.add_parser("status")
    a = ap.parse_args(argv)
    if a.cmd == "build": return cmd_build(a)
    if a.cmd == "search": return cmd_search(a)
    if a.cmd == "status": return cmd_status(a)
    ap.print_help(); return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

