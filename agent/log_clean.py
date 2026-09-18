import os, json, time, datetime
from pathlib import Path

RETENTION_FILE = Path(r"D:\AI\log\retention.json")
CLEAN_LOG = Path(r"D:\AI\log\cleaner\clean.log")

def get_retention():
    try:
        with open(RETENTION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def is_file_open(filepath):
    try:
        # On Windows, we can try to open in exclusive mode to see if it's locked
        with open(filepath, 'a') as f:
            return False
    except OSError:
        return True

def clean():
    retention = get_retention()
    log_entries = []
    root_log = Path(r"D:\AI\log")
    
    if not root_log.exists():
        return

    for subdir in root_log.iterdir():
        if subdir.is_dir():
            # Get retention for this subdir name
            days = retention.get(subdir.name, 30)
            now = time.time()
            
            for file in subdir.glob("*"):
                if file.is_file():
                    if file == RETENTION_FILE or file == CLEAN_LOG:
                        continue
                    
                    # Check if file is open
                    if is_file_open(file):
                        log_entries.append(f"{datetime.datetime.now().isoformat()} | SKIPPED: {file.name} (file is open)")
                        continue
                    
                    # Check mtime
                    file_mtime = file.stat().st_mtime
                    age_days = (now - file_mtime) / (24 * 3600)
                    
                    if age_days > days:
                        try:
                            file.unlink()
                            log_entries.append(f"{datetime.datetime.now().isoformat()} | DELETED: {file.name}")
                        except Exception as e:
                            log_entries.append(f"{datetime.datetime.now().isoformat()} | ERROR: {file.name} ({e})")

    if log_entries:
        with open(CLEAN_LOG, "a", encoding="utf-8") as f:
            for entry in log_entries:
                f.write(entry + "\n")

if __name__ == "__main__":
    clean()
    print("clean finished")
