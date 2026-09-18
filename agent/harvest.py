import os
import json
import logging
import sqlite3
from datetime import datetime
import re

class HarvestScanner:
    def __init__(self, root_dir, db_path='harvest.db', log_path='harvest.log'):
        self.root_dir = os.path.abspath(root_dir)
        self.db_path = db_path
        self.log_path = log_path
        self._setup_logging()
        self._init_db()

    def _setup_logging(self):
        logging.basicConfig(
            filename=self.log_path,
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS harvest_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE,
                    last_seen TIMESTAMP,
                    hash TEXT
                )
            ''')

    def scan(self):
        logging.info(f"Starting scan in {self.root_dir}")
        results = []
        for root, _, files in os.walk(self.root_dir):
            for file in files:
                if file.endswith('.py') or file.endswith('.md'):
                    full_path = os.path.join(root, file)
                    results.append(full_path)
        
        self._update_db(results)
        return results

    def _update_db(self, file_paths):
        with sqlite3.connect(self.db_path) as conn:
            now = datetime.now().isoformat()
            for path in file_paths:
                conn.execute('''
                    INSERT INTO harvest_entries (file_path, last_seen)
                    VALUES (?, ?)
                    ON CONFLICT(file_path) DO UPDATE SET last_seen=excluded.last_seen
                ''', (path, now))

if __name__ == "__main__":
    # Test run
    test_dir = "test_root"
    os.makedirs(test_dir, exist_ok=True)
    with open(os.path.join(test_dir, "test.py"), "w") as f:
        f.write("print('hello')")
    
    scanner = HarvestScanner(test_dir)
    found = scanner.scan()
    print(f"Found: {found}")
    
    with open("last_harvest.json", "w") as f:
        json.dump({"timestamp": datetime.now().isoformat(), "count": len(found)}, f)
    
    # Cleanup test artifacts
    import shutil
    shutil.rmtree(test_dir)
    os.remove("harvest.db")
    os.remove("harvest.log")
    os.remove("last_harvest.json")
