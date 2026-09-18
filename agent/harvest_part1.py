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
