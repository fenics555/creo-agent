import argparse, json, logging, os, re, shutil, sys
from datetime import datetime
from pathlib import Path

DEFAULT_EXTS = {".prt", ".asm", ".drw", ".frm", ".lay", ".sec"}
LOG_FILE = "purge.log"

def setup_logging():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler(sys.stdout)])

class PurgeLock:
    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self.pid = os.getpid()
    def acquire(self) -> bool:
        if self.lock_path.exists():
            try:
                with open(self.lock_path, "r") as f:
                    c = f.read().strip()
                    if c:
                        old_pid = int(c)
                        os.kill(old_pid, 0)
                        return False
            except (OSError, ValueError): self.lock_path.unlink()
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.lock_path, "w") as f: f.write(str(self.pid))
        return True
    def release(self):
        if self.lock_path.exists(): self.lock_path.unlink()

def get_file_info(p: Path):
    if p.suffix and p.suffix[1:].isdigit(): return p.with_suffix(""), int(p.suffix[1:]), "."
    return p, 0, ""

def run_purge(args):
    start_time = datetime.now()
    root = Path(args.root).resolve()
    if not root.exists(): print(f"Error: {root} not found"); return
    backup_dir = Path(args.backup_dir or str(root / "_purge_backup" / datetime.now().strftime("%Y%m%d_%H%M%S"))).resolve()
    lock = PurgeLock(root / "data" / "purge.lock")
    if not lock.acquire(): print("Error: Lock active"); return
    try:
        setup_logging()
        exts = set(args.extensions) if args.extensions else DEFAULT_EXTS
        report = {"root": str(root), "keep": args.keep, "creo_mode": args.creo_mode, "было_версий": 0, "перенесено": [], "пропущено_с_причиной": [], "освобождено_байт": 0, "seconds": 0}
        groups = {}
        for p in root.rglob("*"):
            if not p.is_file() or "_purge_backup" in p.parts: continue
            base_id, ver, delim = get_file_info(p)
            if base_id.suffix.lower() not in exts or p.name == LOG_FILE: continue
            if ver > 0:
                if base_id not in groups: groups[base_id] = []
                groups[base_id].append((ver, p, delim))
        for base, files in groups.items():
            files.sort(key=lambda x: x[0])
            if len(files) <= args.keep and not args.creo_mode: continue
            report["было_версий"] += len(files)
            if args.creo_mode:
                latest_ver, latest_p, latest_delim = files[-1]
                to_move = files[:-1]
                target_p = base.parent / f"{base.name}.1"
                for v, p, d in to_move:
                    try:
                        sz = p.stat().st_size
                        dst = backup_dir / p.relative_to(root)
                        if args.execute:
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(p), str(dst))
                            report["перенесено"].append({"old": str(p), "new": str(dst)})
                            report["освобождено_байт"] += sz
                        else: report["перенесено"].append({"old": str(p), "new": str(dst)})
                    except Exception as e: report["пропущено_с_причиной"].append({"file": str(p), "reason": str(e)})
                if args.execute:
                    if latest_p != target_p:
                        if target_p.exists(): report["пропущено_с_причиной"].append({"file": str(latest_p), "reason": f"Target {target_p.name} occupied"})
                        else:
                            latest_p.rename(target_p)
                            report["перенесено"].append({"old": str(latest_p), "new": str(target_p), "note": "renamed_to_1"})
                    else: report["перенесено"].append({"old": str(latest_p), "new": str(latest_p), "note": "already_1"})
                else: report["перенесено"].append({"old": str(latest_p), "new": str(target_p), "note": "preview_rename"})
            else:
                to_move = files[:-args.keep]
                for v, p, d in to_move:
                    try:
                        sz = p.stat().st_size
                        dst = backup_dir / p.relative_to(root)
                        if args.execute:
                            dst.parent.mkdir(parents=True, exist_ok=True)
                            shutil.move(str(p), str(dst))
                            report["перенесено"].append({"old": str(p), "new": str(dst)})
                            report["освобождено_байт"] += sz
                        else: report["перенесено"].append({"old": str(p), "new": str(dst)})
                    except Exception as e: report["пропущено_с_причиной"].append({"file": str(p), "reason": str(e)})
        report["seconds"] = (datetime.now() - start_time).total_seconds()
        if not args.execute:
            print("\n--- DRY RUN PREVIEW ---")
            for item in report["перенесено"]: print(f"  {Path(item['old']).name} -> {item['new']} {item.get('note', '')}")
            print(f"Skipped: {len(report['пропущено_с_причиной'])}")
        else: print(f"\nDone. Freed: {report['освобождено_байт']/1024:.2f} KB")
        with open(args.report, "w", encoding="utf-8") as f: json.dump(report, f, ensure_ascii=False, indent=4)
    finally: lock.release()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True); parser.add_argument("--keep", type=int, default=1)
    parser.add_argument("--backup-dir"); parser.add_argument("--execute", action="store_true")
    parser.add_argument("--creo-mode", action="store_true"); parser.add_argument("--report", default="purge_report.json")
    parser.add_argument("--extensions", nargs="+"); run_purge(parser.parse_args())
