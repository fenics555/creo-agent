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
