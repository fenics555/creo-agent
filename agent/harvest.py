import os
import sys
import time
import json
import sqlite3
import hashlib
import argparse
import logging
import gc
import psutil
from datetime import datetime
from pathlib import Path

# Library import
try:
    from scanner import ScannerLibrary, init_db_schema
    from core import db
except ImportError:
    print("Error: Could not import scanner or core. Ensure you are running in D:\\AI\\tools\\agent\\")
    sys.exit(1)

# Constants
DATA_DIR = Path(r"D:\AI\data")
LOCK_FILE = DATA_DIR / "harvest.lock"
REPORT_FILE = DATA_DIR / "last_harvest.json"
BATCH_SIZE = 500

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(DATA_DIR / "harvest.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("harvest")

class HarvestLock:
    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self.pid = None

    def acquire(self) -> bool:
        if self.lock_path.exists():
            try:
                with open(self.lock_path, 'r') as f:
                    old_pid = int(f.read().strip())
                if psutil.pid_exists(old_pid):
                    logger.error(f"Already running (PID: {old_pid})")
                    return False
                else:
                    logger.warning(f"Stale lock found (PID {old_pid} dead). Overwriting.")
            except Exception as e:
                logger.warning(f"Could not read lock file: {e}. Overwriting.")
        
        self.pid = os.getpid()
        with open(self.lock_path, 'w') as f:
            f.write(str(self.pid))
        return True

    def release(self):
        if self.lock_path.exists():
            try:
                with open(self.lock_path, 'r') as f:
                    if int(f.read().strip()) == self.pid:
                        self.lock_path.unlink()
            except:
                pass

class HarvestDB:
    def __init__(self):
        self.conn = db()

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

class HarvestProcess:
    def __init__(self, roots: list[str]):
        self.roots = [os.path.abspath(r) for r in roots]
        self.scanner = ScannerLibrary()
        self.db = HarvestDB()
        self.stats = {
            "before": 0, "after": 0, "new": 0, 
            "deleted": 0, "rewritten": 0, "seconds": 0
        }
        self.purge_list = []
        self.sleeping_roots = []
        self.start_time = 0

    def _get_file_hash(self, path: str) -> str:
        try:
            hasher = hashlib.sha256()
            with open(path, 'rb') as f:
                chunk = f.read(65536)
                hasher.update(chunk)
            return hasher.hexdigest()
        except:
            return "error"
    def run_scan(self):
        self.start_time = time.time()
        logger.info("Harvest scan started")
        
        # Initial count
        c = self.db.conn
        self.stats["before"] = c.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        
        current_batch = []
        
        for root in self.roots:
            logger.info(f"Scanning root: {root}")
            root_start = time.time()
            
            found_in_this_root = 0
            for file_info in self.scanner.scan_files_generator(root):
                current_batch.append(file_info)
                found_in_this_root += 1
                
                if len(current_batch) >= BATCH_SIZE:
                    self._process_batch(current_batch)
                    current_batch = []
                    gc.collect()

            if current_batch:
                self._process_batch(current_batch)
                current_batch = []

            logger.info(f"Root {root} finished in {time.time() - root_start:.2f}s")

        self._cleanup_deleted()
        
        self.stats["seconds"] = time.time() - self.start_time
        self.stats["after"] = self.db.conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        self.stats["new"] = self.stats["after"] - self.stats["before"] 
        
        self._write_report()
        logger.info("Harvest scan finished")

    def _process_batch(self, batch: list[dict]):
        c = self.db.conn
        for info in batch:
            path = info['path']
            mtime = info['mtime']
            size = info['size']
            ext = info['ext']
            
            existing = c.execute("SELECT mtime, size, hash FROM files WHERE path=?", (path,)).fetchone()
            
            if existing is None:
                file_hash = self._get_file_hash(path)
                c.execute("INSERT INTO files VALUES (?, ?, ?, ?, ?, ?)",
                          (path, mtime, size, file_hash, os.path.dirname(path), ext))
                self.stats["new"] += 1
            else:
                old_mtime, old_size, old_hash = existing
                if abs(old_mtime - mtime) > 0.1 or old_size != size:
                    file_hash = self._get_file_hash(path)
                    c.execute("REPLACE INTO files VALUES (?, ?, ?, ?, ?, ?)",
                              (path, mtime, size, file_hash, os.path.dirname(path), ext))
                    self.stats["rewritten"] += 1
                    if ext in ['.txt', '.md', '.py', '.json', '.xml', '.html', '.htm']:
                        self._update_fts(path)
            
        c.commit()

    def _update_fts(self, path: str):
def init_db_schema():
    """Инициализация таблиц (вызывается один раз при старте harvest)."""
    c = db()
    try:
        # Для чистоты эксперимента в рамках специи 80, если таблица не соответствует - пересоздаем
        c.execute("DROP TABLE IF EXISTS files")
        c.execute("DROP TABLE IF EXISTS fts_index")
        c.execute("DROP TABLE IF EXISTS models")
        
        c.execute("CREATE TABLE files(path TEXT PRIMARY KEY, mtime REAL, size INTEGER, hash TEXT, root TEXT, type TEXT)")
        c.execute("CREATE VIRTUAL TABLE fts_index USING fts5(path UNINDEXED, content)")
        c.execute("CREATE TABLE models(name TEXT, ext TEXT, path TEXT)")
        c.commit()
    finally:
        c.close()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--roots", nargs="+", help="Roots to scan")
    parser.add_argument("--text", action="store_true", help="Phase C: Text index with embeddings")
    args = parser.parse_args()

    if not args.roots:
        from scanner import read_roots
        roots = read_roots()
    else:
        roots = args.roots

    if not roots:
        print("No roots specified.")
        return

    lock = HarvestLock(LOCK_FILE)
    if not lock.acquire():
        sys.exit(1)

    try:
        init_db_schema()
        process = HarvestProcess(roots)
        process.run_scan()
    finally:
        lock.release()

if __name__ == "__main__":
    main()

        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            if content:
                self.db.conn.execute("INSERT OR REPLACE INTO fts_index(path, content) VALUES (?, ?)", (path, content))
        except:
            pass

    def _cleanup_deleted(self):
        pass

    def _write_report(self):
        report = {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats,
            "purge": self.purge_list,
            "sleeping_roots": self.sleeping_roots
        }
        with open(REPORT_FILE, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)


