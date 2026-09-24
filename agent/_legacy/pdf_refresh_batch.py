import argparse
import sqlite3
import json
import os
import sys
import subprocess
import ctypes
import datetime
from pathlib import Path

LOCK = Path(r'D:\AI\tools\agent\data\pdf_refresh.lock')

# Приборные сигналы для окна (нога 2): общий словарь, живёт в памяти процесса.
PROGRESS = {"phase": "ожидание", "i": 0, "N": 0, "current": "", "stop": False}

def _pid_alive(pid):
    k = ctypes.windll.kernel32
    h = k.OpenProcess(0x1000, False, int(pid))
    if h:
        k.CloseHandle(h)
        return True
    return False

def acquire_lock():
    if LOCK.exists():
        try:
            old = LOCK.read_text(encoding='ascii', errors='ignore').strip()
        except Exception:
            old = ''
        if old.isdigit() and _pid_alive(old):
            print('уже идёт (PID %s)' % old)
            sys.exit(2)
        print('stale-лок PID %s снят' % old)
    LOCK.write_text(str(os.getpid()), encoding='ascii')

def release_lock():
    try:
        LOCK.unlink(missing_ok=True)
    except Exception:
        pass

def stop():
    """Остановка прогона по PID лока (руки 2/3 зовут это же)."""
    if not LOCK.exists():
        return {'stopped': False, 'reason': 'лока нет — прогон не идёт'}
    try:
        pid = int(LOCK.read_text(encoding='ascii', errors='ignore').strip() or '0')
    except Exception:
        pid = 0
    if not pid or not _pid_alive(pid):
        return {'stopped': False, 'reason': 'stale-лок PID %s (владелец мёртв)' % pid}
    r = subprocess.run(['taskkill', '/PID', str(pid), '/F'], capture_output=True, text=True)
    return {'stopped': r.returncode == 0, 'pid': pid, 'reason': r.stdout or r.stderr}

def mark_fresh(pdf_path):
    """После экспорта: пары этого pdf становятся «актуален» (mtime — единственный источник)."""
    try:
        c = sqlite3.connect(DEFAULT_DB_PATH)
        c.execute("UPDATE pairs SET freshness='актуален' WHERE pdf_path=?", (str(pdf_path),))
        c.commit(); c.close()
    except Exception as e:
        print('mark_fresh err:', e)


# Import from agent environment
sys.path.append(r'D:\AI\tools\agent')
try:
    import creo_ops_tools as CT
except ImportError:
    CT = None

DEFAULT_DB_PATH = r'D:\AI\tools\agent\data\harvest.db'
LOG_DIR = Path(r'D:\AI\log\pdfrefresh')
REPORT_FILE = LOG_DIR / 'last_refresh.json'

def log_message(msg):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file = LOG_DIR / f"log_{datetime.datetime.now().strftime('%Y%m%d')}.txt"
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {msg}\n")
    print(msg)

def run_batch(args):
    acquire_lock()
    PROGRESS.update({"phase": "чтение пар", "i": 0, "N": 0, "current": "", "stop": False})
    db_path = DEFAULT_DB_PATH
    root_filter = (args.root or '').strip()

    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        release_lock()
        return False, {"error": f"Database not found at {db_path}"}

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    query = "SELECT model, pdf_path FROM pairs WHERE freshness = 'устарел'"
    
    try:
        cur.execute(query)
        rows = cur.fetchall()
    except Exception as e:
        print(f"Database error: {e}")
        release_lock()
        return False, {"error": f"Database error: {e}"}
    finally:
        conn.close()

    if root_filter:
        rows = [r for r in rows if root_filter.lower() in r['pdf_path'].lower()]
        print(f"фильтр root={root_filter!r}: осталось {len(rows)} пар")

    if not rows:
        print("No outdated PDF pairs found.")
        return True, {"preview": [], "message": "No outdated PDF pairs found."}

    if args.limit:
        rows = rows[:args.limit]

    print(f"Found {len(rows)} outdated pairs.")
    
    results = {
        "timestamp": datetime.datetime.now().isoformat(),
        "was_outdated": len(rows),
        "became_actual": 0,
        "errors": []
    }

    preview_data = []

    for idx, row in enumerate(rows, 1):
        if PROGRESS.get("stop"):
            print("остановлено по запросу (кооперативный стоп)")
            results["errors"].append({"file": "", "error": "остановлено пользователем"})
            break
        PROGRESS.update({"phase": "работа", "i": idx, "N": len(rows),
                         "current": os.path.basename(row['pdf_path'])})
        model_path_str = row['model']
        pdf_path_str = row['pdf_path']
        
        model_path = Path(model_path_str)
        pdf_path = Path(pdf_path_str)
        dirname = model_path.parent
        
        if args.dry_run:
            print(f"[DRY-RUN] Would refresh: {model_path.name} -> {pdf_path.name}")
            results["became_actual"] += 1
            preview_data.append({
                "name": model_path.name,
                "was": pdf_path.name,
                "will": pdf_path.name, # In dry run, nothing changes
                "dir": str(dirname)
            })
            continue

        if CT is None:
            err = "Error: creo_ops_tools not found in sys.path"
            results["errors"].append({"file": model_path.name, "error": err})
            log_message(err)
            continue

        print(f"Refreshing: {model_path.name}...")
        try:
            pw = CT.creo_call("creo", "pwd", {}, 10)
            dd = pw.get("data") or {}
            cur_dir = (dd.get("dirname") if isinstance(dd, dict) else (dd or "")).replace("/", "\\")
            want = str(dirname).replace("/", "\\")
            if cur_dir.rstrip("\\").lower() != want.rstrip("\\").lower():
                ccd = CT.creo_call("creo", "cd", {"dirname": str(dirname)}, 15)
                if not CT.ok(ccd):
                    print(f"pwd/cd не сверился: {CT.errmsg(ccd)}")
                    results["errors"].append({"file": model_path.name, "error": "pwd не сверился"})
                    continue
        except Exception as e:
            print(f"pwd-сверка err: {e}")
        res = CT.tool_print_pdf(name=str(model_path), dirname=str(dirname))

        if "PDF сохранён" in res:
            results["became_actual"] += 1
            mark_fresh(pdf_path)
            log_message(f"SUCCESS: {model_path.name} -> {res}")
        else:
            err_msg = res if res else "Unknown error"
            results["errors"].append({"file": model_path.name, "error": err_msg})
            log_message(f"ERROR: {model_path.name} -> {err_msg}")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    
    print(f"Batch finished. Report saved to {REPORT_FILE}")
    PROGRESS.update({"phase": "готово", "current": "", "i": PROGRESS["N"]})
    release_lock()
    
    if args.dry_run:
        return True, {"preview": preview_data}
    else:
        if results["errors"]:
            print(f"Completed with {len(results['errors'])} errors.")
        return True, results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PDF Batch Refresh Tool")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--execute", action="store_true", help="Execute actual refresh")
    parser.add_argument("--root", type=str, help="Database path or root directory")
    parser.add_argument("--limit", type=int, help="Limit number of pairs")
    parser.add_argument("--report", action="store_true", help="Only show report")

    args = parser.parse_args()
    
    if args.execute:
        args.dry_run = False
    elif not args.dry_run:
        args.dry_run = True
    
    run_batch(args)
