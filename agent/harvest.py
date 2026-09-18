# -*- coding: utf-8 -*-
"""harvest.py — суперкрутой сканер дома (спека 84).
CLI: python harvest.py [--roots <файл>] [--text]; корни по умолчанию kb_roots.txt.
Живые корни сканирует ТОЛЬКО этот скрипт, вне процесса агента (манифест п.19).
База data/harvest.db; лок data/harvest.lock; лог data/harvest.log;
отчёт data/last_harvest.json. Парсер заголовков — scanner.ScannerLibrary.
"""
import argparse, hashlib, json, os, sqlite3, sys, time
from datetime import datetime
from pathlib import Path

AG = Path(__file__).resolve().parent
DATA = AG / "data"
LOCK = DATA / "harvest.lock"
DBF = DATA / "harvest.db"
LOGF = Path(r"D:\AI\log\harvest\harvest.log")
REPORT = Path(r"D:\AI\log\harvest\last_harvest.json")
DEFAULT_ROOTS = AG / "kb_roots.txt"
BATCH = 500

def log(msg):
    line = "%s | %s" % (datetime.now().isoformat(timespec="seconds"), msg)
    print(line, flush=True)
    try:
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def die(code, msg):
    log("FATAL: " + msg)
    print(msg)
    sys.exit(code)

def _pid_alive(pid):
    import ctypes
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
    if h:
        k.CloseHandle(h)
        return True
    return False

def acquire_lock():
    if LOCK.exists():
        try:
            old = LOCK.read_text(encoding="ascii", errors="ignore").strip()
        except Exception:
            old = ""
        if old.isdigit() and _pid_alive(old):
            print("уже идёт")
            sys.exit(2)
        log("stale-лок PID %s снят" % (old or "?"))
        try:
            LOCK.unlink(missing_ok=True)
        except Exception as e:
            die(2, "лок занят, снять не удалось: %s" % e)
    DATA.mkdir(parents=True, exist_ok=True)
    try:
        LOCK.write_text(str(os.getpid()), encoding="ascii")
    except Exception as e:
        die(2, "lock err: %s" % e)

def release_lock():
    try:
        LOCK.unlink(missing_ok=True)
    except Exception:
        pass

def read_roots(path):
    roots = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.replace("\ufeff", "").strip()
            if line and not line.startswith("#"):
                roots.append(line)
    if not roots:
        die(3, "корни не найдены в %s" % path)
    return roots

SQL = """
CREATE TABLE IF NOT EXISTS models_raw(
  name TEXT, ext TEXT, path TEXT PRIMARY KEY,
  mtime REAL, size INTEGER, sha256head TEXT);
CREATE TABLE IF NOT EXISTS instances(
  path TEXT, inst_name TEXT, family TEXT, verified INTEGER);
CREATE TABLE IF NOT EXISTS pairs(
  model TEXT, pdf_path TEXT, freshness TEXT);
CREATE TABLE IF NOT EXISTS facts_parser(
  subject TEXT, pred TEXT, obj TEXT, source TEXT, verified INTEGER);
"""

def open_db():
    existed = DBF.exists() and DBF.stat().st_size > 0
    reset = False
    con = sqlite3.connect(str(DBF))
    con.execute("PRAGMA journal_mode=WAL")
    try:
        n = con.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
        if n == 0:
            reset = True
    except sqlite3.DatabaseError:
        reset = True
    if reset:
        log('ERROR «сброс в 0»: база пуста или отсутствовала, пересборка')
    con.executescript(SQL)
    has_fts = con.execute("SELECT count(*) FROM sqlite_master WHERE name='chunks_fts'").fetchone()[0]
    if not has_fts:
        try:
            con.executescript("CREATE VIRTUAL TABLE chunks_fts USING fts5(path, title, body);")
            log("chunks_fts: fts5")
        except sqlite3.OperationalError:
            con.executescript("CREATE VIRTUAL TABLE chunks_fts USING fts4(path, title, body);")
            log("chunks_fts: fts4 (fallback)")
    con.commit()
    return con, existed, reset

def sha256head(path):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            h.update(f.read(4096))
    except Exception:
        return ""
    return h.hexdigest()[:8]

def flush_batch(con, batch, old, added, rewrote):
    a = r = 0
    for m in batch:
        p = m["path"]
        sig = (round(m["mtime"], 3), m["size"])
        o = old.get(p)
        if o is None:
            added.append(p)
            a += 1
        elif (round(o[0], 3), o[1]) != sig:
            rewrote.append(p)
            r += 1
        head = sha256head(p)
        if not head:
            log("не читается: %s" % p)
        con.execute(
            "INSERT OR REPLACE INTO models_raw(name,ext,path,mtime,size,sha256head)"
            " VALUES(?,?,?,?,?,?)",
            (m["name"], m["ext"], p, m["mtime"], m["size"], head))
    con.commit()
    del batch[:]
    return a, r


def scan_models(con, roots):
    old = {p: (mt, sz) for p, mt, sz in
           con.execute("SELECT path, mtime, size FROM models_raw")}
    from scanner import ScannerLibrary
    lib = ScannerLibrary()
    added, rewrote, deleted = [], [], []
    per_root, vanished = {}, 0
    t_all = time.time()
    for root in roots:
        t0 = time.time()
        if not Path(root).exists():
            vanished += 1
            log("START %s" % root)
            log("FINISH %s added=0 rewrote=0 deleted=0 seconds=%.1f (корень спит)" % (root, time.time() - t0))
            per_root[root] = {"added": 0, "rewrote": 0, "deleted": 0,
                              "seconds": round(time.time() - t0, 1), "asleep": True}
            continue
        log("START %s" % root)
        rp = str(Path(root))
        old_here = [p for p in old if p.startswith(rp)]
        seen_here = set()
        batch, a, r = [], 0, 0
        for meta in lib.scan_files_generator(root):
            seen_here.add(meta["path"])
            batch.append(meta)
            if len(batch) >= BATCH:
                a2, r2 = flush_batch(con, batch, old, added, rewrote)
                a += a2; r += r2
                log("  батч: прочитано %d, added=%d, rewrote=%d" % (len(seen_here), a, r))
        if batch:
            a2, r2 = flush_batch(con, batch, old, added, rewrote)
            a += a2; r += r2
        d_here = sorted(set(old_here) - seen_here)
        for p in d_here:
            con.execute("DELETE FROM models_raw WHERE path=?", (p,))
            con.execute("DELETE FROM instances WHERE path=?", (p,))
        deleted.extend(d_here)
        con.commit()
        secs = time.time() - t0
        log("FINISH %s added=%d rewrote=%d deleted=%d seconds=%.1f" % (root, a, r, len(d_here), secs))
        per_root[root] = {"added": a, "rewrote": r, "deleted": len(d_here),
                          "seconds": round(secs, 1)}
    return added, rewrote, deleted, per_root, vanished, time.time() - t_all


def parse_instances(con, lib):
    n = 0
    rows = con.execute("SELECT path FROM models_raw WHERE ext IN ('.prt','.asm')").fetchall()
    con.execute("DELETE FROM instances")
    for (p,) in rows:
        try:
            res = lib.parse_model_header(p)
        except Exception as e:
            log("parser err %s: %s" % (p, e))
            continue
        for inst in res.get("instances", []):
            con.execute("INSERT INTO instances(path,inst_name,family,verified) VALUES(?,?,?,0)",
                        (p, inst, ""))
            n += 1
        for fam in res.get("families", []):
            con.execute("INSERT INTO instances(path,inst_name,family,verified) VALUES(?,?,?,0)",
                        (p, "", fam))
            n += 1
    con.commit()
    log("instances: %d (verified=False до сверки Ф3)" % n)
    return n


def build_pairs(con):
    n = 0
    con.execute("DELETE FROM pairs")
    rows = con.execute("SELECT path, name, mtime FROM models_raw WHERE ext IN ('.prt','.asm','.drw')").fetchall()
    for p, name, mt in rows:
        base = os.path.splitext(name)[0]
        d = os.path.dirname(p)
        pdf_path, pdf_mt = "", 0
        try:
            for fn in os.listdir(d):
                if fn.lower().startswith(base.lower()) and fn.lower().endswith(".pdf"):
                    fp = os.path.join(d, fn)
                    mfp = os.path.getmtime(fp)
                    if mfp > pdf_mt:
                        pdf_path, pdf_mt = fp, mfp
        except Exception:
            continue
        if not pdf_path:
            continue
        fresh = "актуален" if pdf_mt >= mt else "устарел"
        con.execute("INSERT INTO pairs(model,pdf_path,freshness) VALUES(?,?,?)", (p, pdf_path, fresh))
        n += 1
    con.commit()
    log("pairs: %d" % n)
    return n


def ollama_alive():
    import socket
    try:
        socket.create_connection(("127.0.0.1", 11434), timeout=2).close()
        return True
    except Exception:
        return False


def flush_text(con, buf):
    import urllib.request
    for p, title, ch in buf:
        con.execute("INSERT INTO chunks_fts(path,title,body) VALUES(?,?,?)", (p, title, ch))
        prompt = ("Извлеки из текста факты в формате subject|pred|obj, по одному на строку, "
                  "максимум 5. Только факты из текста. Текст:\n" + ch[:1500])
        try:
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/generate",
                data=json.dumps({"model": "gemma4:26b", "prompt": prompt, "stream": False}).encode(),
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                ans = json.loads(resp.read().decode("utf-8", "ignore")).get("response", "")
            for line in ans.splitlines():
                parts = [x.strip() for x in line.split("|")]
                if len(parts) == 3 and all(parts):
                    con.execute("INSERT INTO facts_parser(subject,pred,obj,source,verified)"
                                " VALUES(?,?,?,?,0)", (parts[0], parts[1], parts[2], p))
        except Exception as e:
            log("text err %s: %s" % (p, e))
    n = len(buf)
    con.commit()
    del buf[:]
    return n


def text_pass(con, roots):
    if not ollama_alive():
        log("text: ollama недоступна")
        print("ollama недоступна")
        sys.exit(4)
    con.execute("DELETE FROM chunks_fts")
    n, buf = 0, []
    for root in roots:
        if not Path(root).exists():
            continue
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for fn in files:
                if not fn.lower().endswith((".md", ".txt")):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    body = open(p, encoding="utf-8", errors="ignore").read(6000)
                except Exception:
                    continue
                chunks = [body[i:i + 2000] for i in range(0, len(body), 2000)] or [""]
                for ch in chunks:
                    buf.append((p, fn, ch))
                    if len(buf) >= 8:
                        n += flush_text(con, buf)
                        time.sleep(1)
    if buf:
        n += flush_text(con, buf)
    log("text pass: %d чанков" % n)
    return n


def write_report(con, roots, added, rewrote, deleted, per_root, vanished, seconds):
    tables = {}
    for t in ("models_raw", "instances", "pairs", "facts_parser"):
        tables[t] = con.execute("SELECT count(*) FROM " + t).fetchone()[0]
    try:
        tables["chunks_fts"] = con.execute("SELECT count(*) FROM chunks_fts").fetchone()[0]
    except Exception:
        tables["chunks_fts"] = 0
    rep = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "roots": roots,
        "tables": tables,
        "added_head": [os.path.basename(p) for p in added[:20]],
        "deleted": len(deleted),
        "deleted_head": [os.path.basename(p) for p in deleted[:20]],
        "rewritten": len(rewrote),
        "vanished_guard": vanished,
        "seconds": round(seconds, 1),
        "per_root": per_root,
    }
    rich = {}
    for p, inst, fam, ver in con.execute(
            "SELECT path, inst_name, family, verified FROM instances"):
        d = rich.setdefault(p, {"instances": 0, "families": 0, "verified": bool(ver)})
        if inst:
            d["instances"] += 1
        if fam:
            d["families"] += 1
    top = []
    for p, d in sorted(rich.items(), key=lambda kv: -(kv[1]["instances"] + kv[1]["families"]))[:20]:
        row = con.execute("SELECT name FROM models_raw WHERE path=?", (p,)).fetchone()
        top.append({"name": row[0] if row else os.path.basename(p), **d})
    rep["bench_top"] = top
    with open(REPORT, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    log("отчёт: %s" % REPORT)
    return rep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--roots", default=str(DEFAULT_ROOTS))
    ap.add_argument("--text", action="store_true")
    ap.add_argument("--bench", action="store_true")
    args = ap.parse_args()
    acquire_lock()
    t0 = time.time()
    log("harvest PID %d старт: roots=%s text=%s bench=%s" % (os.getpid(), args.roots, args.text, args.bench))
    try:
        con, existed, reset = open_db()
        roots = read_roots(args.roots)
        if args.text:
            text_pass(con, roots)
        added, rewrote, deleted, per_root, vanished, seconds = scan_models(con, roots)
        from scanner import ScannerLibrary
        lib = ScannerLibrary()
        parse_instances(con, lib)
        build_pairs(con)
        con.commit()
        rep = write_report(con, roots, added, rewrote, deleted, per_root, vanished, time.time() - t0)
        if args.bench:
            ni = con.execute("SELECT count(*) FROM instances WHERE inst_name<>''").fetchone()[0]
            nf = con.execute("SELECT count(*) FROM instances WHERE family<>''").fetchone()[0]
            log("BENCH: seconds=%.2f files=%d files/sec=%.1f instances=%d families=%d" %
                (rep["seconds"], rep["tables"]["models_raw"],
                 rep["tables"]["models_raw"] / max(rep["seconds"], 0.01), ni, nf))
        con.close()
        if reset:
            log("код выхода 3: пересборка выполнена")
            print("пересборка выполнена")
            sys.exit(3)
        print("harvest ok: added=%d rewritten=%d deleted=%d" % (len(added), len(rewrote), len(deleted)))
    finally:
        release_lock()

if __name__ == "__main__":
    main()

