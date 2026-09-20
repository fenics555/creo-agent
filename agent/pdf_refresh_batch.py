# -*- coding: utf-8 -*-
"""pdf_refresh_batch.py — перепечать устаревших PDF пачкой (спека 104, рука 1: библиотека+CLI).
Библиотека читает пары «устарел» из harvest.db (pairs), экспортирует чертежи через
CREOSON interface:export_pdf {file: X.drw, dirname: <папка чертежа>, use_drawing_settings:true,
sheet_range:"all"}; mtime pdf после экспорта — единственный источник свежести.
Лок data\pdf_refresh.lock общий для всех трёх рук; лог и отчёт — D:\AI\log\pdfrefresh\.
dirname = папка чертежа всегда; перед экспортом сверяется pwd сессии (creo:cd при расхождении).
"""
import argparse, json, os, re, sqlite3, subprocess, sys, time
from datetime import datetime
from pathlib import Path

AG = Path(__file__).resolve().parent
DBF = AG / "data" / "harvest.db"
LOCK = AG / "data" / "pdf_refresh.lock"
LOGDIR = Path(r"D:\AI\log\pdfrefresh")
LOGF = LOGDIR / "pdfrefresh.log"
REPORT = LOGDIR / "last_refresh.json"
CREOSON = "http://127.0.0.1:8080/creoson"

def log(msg):
    line = "%s | %s" % (datetime.now().isoformat(timespec="seconds"), msg)
    print(line, flush=True)
    try:
        LOGDIR.mkdir(parents=True, exist_ok=True)
        with open(LOGF, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def die(code, msg):
    log("FATAL: " + msg)
    print(msg)
    sys.exit(code)

def acquire_lock():
    if LOCK.exists():
        print("уже идёт")
        sys.exit(2)
    try:
        LOCK.write_text(str(os.getpid()), encoding="ascii")
    except Exception as e:
        die(2, "lock err: %s" % e)

def release_lock():
    try:
        LOCK.unlink(missing_ok=True)
    except Exception:
        pass

def _pid_alive(pid):
    import ctypes
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, int(pid))
    if h:
        k.CloseHandle(h)
        return True
    return False

def stop():
    """Остановка прогона по PID лока (рука 2/3 зовут это же)."""
    if not LOCK.exists():
        return {"stopped": False, "reason": "лока нет — прогон не идёт"}
    try:
        pid = int(LOCK.read_text(encoding="ascii", errors="ignore").strip() or "0")
    except Exception:
        pid = 0
    if not pid or not _pid_alive(pid):
        return {"stopped": False, "reason": "stale-лок PID %s (владелец мёртв)" % pid}
    import subprocess
    r = subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True, text=True)
    good = r.returncode == 0
    return {"stopped": good, "pid": pid,
            "reason": "остановлен" if good else (r.stderr or r.stdout or "taskkill fail")}

def outdated_pairs(root="", limit=0):
    """Пары с вердиктом «устарел» (модель свежее своего pdf), уникально по pdf."""
    c = sqlite3.connect(str(DBF))
    rows = c.execute(
        "SELECT pdf_path, model, mtime FROM pairs p JOIN models_raw m ON m.path=p.model "
        "WHERE p.freshness='устарел' ORDER BY p.pdf_path").fetchall()
    c.close()
    seen, out = set(), []
    for pdf, model, mtime in rows:
        if root and root.lower() not in pdf.lower():
            continue
        if pdf in seen:
            continue
        seen.add(pdf)
        out.append({"pdf": pdf, "model": model, "model_mtime": mtime})
        if limit and len(out) >= limit:
            break
    return out

def find_drw(pdf_path):
    """Чертёж для pdf: тот же base в папке pdf (base.drw или base.drw.N)."""
    d = os.path.dirname(pdf_path)
    base = os.path.splitext(os.path.basename(pdf_path))[0]
    try:
        for fn in os.listdir(d):
            m = re.match(re.escape(base) + r"\.drw(\.\d+)?$", fn, re.I)
            if m:
                return os.path.join(d, fn)
    except Exception:
        pass
    return None

import urllib.request

def cc(sess, cmd, fn, data=None, t=60):
    body = {"sessionId": sess, "command": cmd, "function": fn, "data": data or {}}
    r = urllib.request.Request(CREOSON, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(r, timeout=t))

def ok(j): return bool(j) and not (j.get("status") or {}).get("error")

def ensure_pwd(sess, dirname):
    """Спека 104: CREOSON-сессию перед экспортом сверять pwd с папкой чертежа."""
    j = cc(sess, "creo", "pwd", {}, 15)
    d = j.get("data") or {}
    cur = d.get("dirname") if isinstance(d, dict) else (d or "")
    cur = str(cur).replace("/", "\\")
    want = str(dirname).replace("/", "\\")
    if cur.rstrip("\\").lower() == want.rstrip("\\").lower():
        return True
    jc = cc(sess, "creo", "cd", {"dirname": dirname}, 15)
    return ok(jc)

def run(execute=False, root="", limit=0, report_path=None):
    """Спека 104 Ф1: возвращает dict отчёта. execute=False — только таблица превью."""
    acquire_lock()
    t0 = time.time()
    try:
        pairs = outdated_pairs(root=root, limit=limit)
        plan, errors = [], []
        for it in pairs:
            drw = find_drw(it["pdf"])
            if not drw:
                errors.append({"pdf": it["pdf"], "причина": "нет чертежа (.drw) рядом"})
                continue
            plan.append({"pdf": it["pdf"], "drw": drw,
                         "model_mtime": it["model_mtime"]})
        log("план: %d перепечаток (execute=%s, root=%r)" % (len(plan), execute, root))
        if not execute:
            rep = {"ts": datetime.now().isoformat(timespec="seconds"),
                   "mode": "dry-run", "было_устаревших": len(outdated_pairs(root=root)),
                   "план": plan[:50], "к_перепечатке": len(plan),
                   "ошибки": errors, "seconds": round(time.time() - t0, 1),
                   "exit_code": 0}
            _write_report(rep, report_path)
            return rep
        import urllib.request
        sess = cc(None, "connection", "connect", {}, 10).get("sessionId")
        if not sess:
            errors.append({"pdf": "", "причина": "creoson не дал sessionId"})
            rep = _finish(plan, errors, t0, report_path)
            return rep
        became = 0
        for it in plan:
            drw, pdf = it["drw"], it["pdf"]
            d = os.path.dirname(drw)
            name = os.path.basename(drw)
            try:
                if not ensure_pwd(sess, d):
                    errors.append({"pdf": pdf, "причина": "pwd не сверился, cd не удался"})
                    continue
                jo = cc(sess, "file", "open", {"file": name, "dirname": d, "display": False}, 90)
                if not ok(jo):
                    errors.append({"pdf": pdf, "причина": "file:open: %s" % (jo.get("status") or {}).get("message")})
                    continue
                je = cc(sess, "interface", "export_pdf",
                        {"file": name, "filename": os.path.basename(pdf), "dirname": d,
                         "use_drawing_settings": True, "sheet_range": "all"}, 120)
                cc(sess, "file", "erase", {"file": name}, 30)
                if not ok(je):
                    errors.append({"pdf": pdf, "причина": "export_pdf: %s" % (je.get("status") or {}).get("message")})
                    continue
                if os.path.getmtime(pdf) > it["model_mtime"]:
                    became += 1
                    _mark_fresh(pdf)
                    log("ok: %s" % os.path.basename(pdf))
                else:
                    errors.append({"pdf": pdf, "причина": "mtime pdf не обновился после экспорта"})
            except Exception as e:
                errors.append({"pdf": pdf, "причина": str(e)[:200]})
        rep = _finish(plan, errors, t0, report_path, became=became)
        return rep
    finally:
        release_lock()

def _mark_fresh(pdf):
    try:
        c = sqlite3.connect(str(DBF))
        c.execute("UPDATE pairs SET freshness='актуален' WHERE pdf_path=?", (pdf,))
        c.commit(); c.close()
    except Exception as e:
        log("mark err: %s" % e)

def _write_report(rep, report_path=None):
    p = Path(report_path) if report_path else REPORT
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(rep, f, ensure_ascii=False, indent=1)
    log("отчёт: %s" % p)

def _finish(plan, errors, t0, report_path, became=None):
    was = len(plan) + len(errors)
    rep = {"ts": datetime.now().isoformat(timespec="seconds"), "mode": "execute",
           "было_устаревших": was, "стало_актуальных": became if became is not None else 0,
           "ошибки": errors, "seconds": round(time.time() - t0, 1), "exit_code": 0 if not errors else 1}
    _write_report(rep, report_path)
    return rep

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--execute", action="store_true")
    ap.add_argument("--root", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--report", default=None)
    args = ap.parse_args()
    rep = run(execute=args.execute, root=args.root, limit=args.limit, report_path=args.report)
    if args.execute:
        print("pdf_refresh: было=%s стало=%s ошибок=%s" % (
            rep.get("было_устаревших"), rep.get("стало_актуальных"), len(rep.get("ошибки", []))))
    else:
        for p in rep.get("план", []):
            print("будет перепечатано: %s <- %s" % (os.path.basename(p["pdf"]), os.path.basename(p["drw"])))
        print("план: %d, ошибок: %d" % (rep.get("к_перепечатке", 0), len(rep.get("ошибки", []))))

if __name__ == "__main__":
    main()
