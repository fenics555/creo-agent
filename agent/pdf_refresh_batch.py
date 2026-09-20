import argparse
import sqlite3
import json
import os
import sys
import datetime
from pathlib import Path

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
    db_path = args.root if args.root else DEFAULT_DB_PATH
    
    # If provided path is a directory, assume it's a root containing 'data/harvest.db'
    if os.path.isdir(db_path):
        db_path = os.path.join(db_path, 'data', 'harvest.db')
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
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
        return False, {"error": f"Database error: {e}"}
    finally:
        conn.close()

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

    for row in rows:
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
        res = CT.tool_print_pdf(name=str(model_path), dirname=str(dirname))
        
        if "PDF сохранён" in res:
            results["became_actual"] += 1
            log_message(f"SUCCESS: {model_path.name} -> {res}")
        else:
            err_msg = res if res else "Unknown error"
            results["errors"].append({"file": model_path.name, "error": err_msg})
            log_message(f"ERROR: {model_path.name} -> {err_msg}")

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    
    print(f"Batch finished. Report saved to {REPORT_FILE}")
    
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
