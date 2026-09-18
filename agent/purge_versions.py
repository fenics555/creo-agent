import argparse
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Настройки
EXTENSIONS = {'.prt', '.asm', '.drw', '.frm', '.lay', '.sec'}
LOG_FILE = "purge.log"

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

class PurgeLock:
    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self.pid = os.getpid()

    def acquire(self) -> bool:
        if self.lock_path.exists():
            try:
                with open(self.lock_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        old_pid = int(content)
                        logging.warning(f"Lock file {self.lock_path} already exists (PID: {old_pid}).")
                        return False
            except ValueError:
                logging.warning(f"Lock file {self.lock_path} is corrupted. Ignoring PID.")
                return False
            except Exception as e:
                logging.warning(f"Could not read lock file: {e}")
                return False
        
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.lock_path, 'w') as f:
                f.write(str(self.pid))
            return True
def get_file_groups(root_path: Path):
    groups = {}
    ext_pattern = '|'.join(re.escape(ext) for ext in EXTENSIONS)
    pattern_str = r'^(.*?(?:\.' + ext_pattern + r'))(?:\.(\d+))?$'
    pattern = re.compile(pattern_str)
    
    for p in root_path.rglob("*"):
        if p.is_file():
            match = pattern.match(p.name)
            if match:
                base_name = match.group(1)
                ver_str = match.group(2)
                
                group_key = (p.parent, base_name)
                if group_key not in groups:
                    groups[group_key] = []
                
                version = int(ver_str) if ver_str else 0
                groups[group_key].append((version, p))
    return groups

def run_purge(args):
    start_time = datetime.now()
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Error: Root path {root} does not exist.")
        return

    backup_dir = Path(args.backup_dir).resolve()
    lock = PurgeLock(root / "data" / "purge.lock")
    
    if not lock.acquire():
        print("Error: Could not acquire lock. Another process might be running.")
        return

    try:
        setup_logging()
        logging.info(f"Starting purge. Root: {root}, Keep: {args.keep}, Execute: {args.execute}")
        groups = get_file_groups(root)
        report = {
            "root": str(root),
            "keep": args.keep,
            "было_версий": 0,
            "перенесено": [],
            "пропущено_с_причиной": [],
            "освобождено_байт": 0,
            "seconds": 0
        }
        for (parent, base_name), files in groups.items():
            if len(files) <= args.keep:
        end_time = datetime.now()
        report["seconds"] = (end_time - start_time).total_seconds()
        if not args.execute:
            print("\n--- DRY-RUN PREVIEW ---")
            print(f"{'Original File':<40} | {'Target Backup Path'}")
            print("-" * 85)
            for item in report["перенесено"]:
                print(f"{item['old'][-40:]:<40} | {item['new']}")
            print(f"\nSummary: {len(report['перенесено'])} files to move, {len(report['пропущено_с_причиной'])} skipped.")
            print("-----------------------\n")
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=4)
        logging.info(f"Purge finished. Report saved to {report_path}")
    finally:
        lock.release()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Purge old versions of files and move them to backup.")
    parser.add_argument("--root", required=True, help="Root directory to scan")
    parser.add_argument("--keep", type=int, default=1, help="Number of versions to keep (default: 1)")
    parser.add_argument("--backup-dir", help="Directory to move old versions to")
    parser.add_argument("--execute", action="store_true", help="Actually move the files")
    parser.add_argument("--report", default="data/last_purge.json", help="Path to JSON report")
    args = parser.parse_args()
    if not args.backup_dir:
        root_path = Path(args.root).resolve()
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.backup_dir = str(root_path / "_purge_backup" / date_str)
    run_purge(args)

                continue
            files.sort()
            keep_files = files[-args.keep:]
            to_move = files[:-args.keep]
            report["было_версий"] += len(files)
            for ver, f in to_move:
                try:
                    with open(f, 'a'): pass
                except OSError as e:
                    reason = f"File busy or access denied: {e.strerror}"
                    logging.warning(f"Skipping {f.name}: {reason}")
                    report["пропущено_с_причиной"].append({"file": str(f), "reason": reason})
                    continue
                file_size = f.stat().st_size
                dest_path = backup_dir / f.relative_to(root)
                if args.execute:
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.move(str(f), str(dest_path))
                        report["перенесено"].append({"old": str(f), "new": str(dest_path)})
                        report["освобождено_байт"] += file_size
                        logging.info(f"MOVED: {f.name} -> {dest_path.relative_to(backup_dir)}")
                    except Exception as e:
                        report["пропущено_с_причиной"].append({"file": str(f), "reason": str(e)})
                        logging.error(f"Failed to move {f.name}: {e}")
                else:
                    dest_path_str = str(backup_dir / f.relative_to(root))
                    report["перенесено"].append({"old": str(f), "new": dest_path_str})
                    logging.info(f"DRY-RUN: {f.name} would move to {dest_path.relative_to(backup_dir)}")

        except Exception as e:
            logging.error(f"Failed to create lock file: {e}")
            return False

    def release(self):
        if self.lock_path.exists():
            try:
                with open(self.lock_path, 'r') as f:
                    if f.read().strip() == str(self.pid):
                        self.lock_path.unlink()
            except Exception:
                pass

import argparse
import json
import logging
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

# Настройки
EXTENSIONS = {'.prt', '.asm', '.drw', '.frm', '.lay', '.sec'}
LOG_FILE = "purge.log"

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

class PurgeLock:
    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self.pid = os.getpid()

    def acquire(self) -> bool:
        if self.lock_path.exists():
            try:
                with open(self.lock_path, 'r') as f:
                    content = f.read().strip()
                    if content:
                        old_pid = int(content)
                        logging.warning(f"Lock file {self.lock_path} already exists (PID: {old_pid}).")
                        return False
            except ValueError:
                logging.warning(f"Lock file {self.lock_path} is corrupted. Ignoring PID.")
                return False
            except Exception as e:
                logging.warning(f"Could not read lock file: {e}")
                return False
        
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.lock_path, 'w') as f:
                f.write(str(self.pid))
            return True
        except Exception as e:
            logging.error(f"Failed to create lock file: {e}")
            return False

    def release(self):
        if self.lock_path.exists():
            try:
                with open(self.lock_path, 'r') as f:
                    if f.read().strip() == str(self.pid):
                        self.lock_path.unlink()
            except Exception:
                pass

def get_file_groups(root_path: Path):
    groups = {}
    ext_pattern = '|'.join(re.escape(ext) for ext in EXTENSIONS)
    pattern_str = r'^(.*?(?:\.' + ext_pattern + r'))(?:\.(\d+))?$'
    pattern = re.compile(pattern_str)
    
    for p in root_path.rglob("*"):
        if p.is_file():
            match = pattern.match(p.name)
            if match:
                base_name = match.group(1)
                ver_str = match.group(2)
                
                group_key = (p.parent, base_name)
                if group_key not in groups:
                    groups[group_key] = []
                
                version = int(ver_str) if ver_str else 0
                groups[group_key].append((version, p))
    return groups

def run_purge(args):
    start_time = datetime.now()
    root = Path(args.root).resolve()
    if not root.exists():
        print(f"Error: Root path {root} does not exist.")
        return

    backup_dir = Path(args.backup_dir).resolve()
    lock = PurgeLock(root / "data" / "purge.lock")
    
    if not lock.acquire():
        print("Error: Could not acquire lock. Another process might be running.")
        return

    try:
        setup_logging()
        end_time = datetime.now()
        report["seconds"] = (end_time - start_time).total_seconds()
        if not args.execute:
            print("\n--- DRY-RUN PREVIEW ---")
            print(f"{'Original File':<40} | {'Target Backup Path'}")
            print("-" * 85)
            for item in report["перенесено"]:
                print(f"{item['old'][-40:]:<40} | {item['new']}")
            print(f"\nSummary: {len(report['перенесено'])} files to move, {len(report['пропущено_с_причиной'])} skipped.")
            print("-----------------------\n")
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=4)
        logging.info(f"Purge finished. Report saved to {report_path}")
    finally:
        lock.release()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Purge old versions of files and move them to backup.")
    parser.add_argument("--root", required=True, help="Root directory to scan")
    parser.add_argument("--keep", type=int, default=1, help="Number of versions to keep (default: 1)")
    parser.add_argument("--backup-dir", help="Directory to move old versions to")
    parser.add_argument("--execute", action="store_true", help="Actually move the files")
    parser.add_argument("--report", default="data/last_purge.json", help="Path to JSON report")
    args = parser.parse_args()
    if not args.backup_dir:
        root_path = Path(args.root).resolve()
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.backup_dir = str(root_path / "_purge_backup" / date_str)
    run_purge(args)

        logging.info(f"Starting purge. Root: {root}, Keep: {args.keep}, Execute: {args.execute}")
        groups = get_file_groups(root)
        report = {
            "root": str(root),
            "keep": args.keep,
            "было_версий": 0,
            "перенесено": [],
            "пропущено_с_причиной": [],
            "освобождено_байт": 0,
            "seconds": 0
        }
        for (parent, base_name), files in groups.items():
            if len(files) <= args.keep:
                continue
            files.sort()
            keep_files = files[-args.keep:]
            to_move = files[:-args.keep]
            report["было_версий"] += len(files)
            for ver, f in to_move:
                try:
                    with open(f, 'a'): pass
                except OSError as e:
                    reason = f"File busy or access denied: {e.strerror}"
                    logging.warning(f"Skipping {f.name}: {reason}")
                    report["пропущено_с_причиной"].append({"file": str(f), "reason": reason})
                    continue
                file_size = f.stat().st_size
                dest_path = backup_dir / f.relative_to(root)
                if args.execute:
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.move(str(f), str(dest_path))
                        report["перенесено"].append({"old": str(f), "new": str(dest_path)})
                        report["освобождено_байт"] += file_size
                        logging.info(f"MOVED: {f.name} -> {dest_path.relative_to(backup_dir)}")
                    except Exception as e:
                        report["пропущено_с_причиной"].append({"file": str(f), "reason": str(e)})
                        logging.error(f"Failed to move {f.name}: {e}")
                else:
                    dest_path_str = str(backup_dir / f.relative_to(root))
                    report["перенесено"].append({"old": str(f), "new": dest_path_str})
                    logging.info(f"DRY-RUN: {f.name} would move to {dest_path.relative_to(backup_dir)}")

