import os, sys, argparse, shutil, json, time, datetime, re, subprocess
from pathlib import Path

EXTENSIONS = {'.prt', '.asm', '.drw', '.frm', '.lay', '.sec'}

class PurgeLock:
    def __init__(self, path):
        self.path = Path(path)
        self.pid = os.getpid()
    def acquire(self):
        if self.path.exists():
            try:
                p_str = self.path.read_text().strip()
                if p_str:
                    p = int(p_str)
                    cmd = f'tasklist /FI "PID eq {p}"'
                    output = subprocess.check_output(cmd, shell=True).decode(errors='ignore')
                    if str(p) in output:
                        return False, f"Locked by {p}"
            except: pass
        self.path.write_text(str(self.pid))
        return True, None
    def release(self):
        if self.path.exists():
            try:
                if int(self.path.read_text().strip()) == self.pid:
                    self.path.unlink()
            except: pass

def get_groups(root):
    root = Path(root)
    all_files = sorted([f for f in root.rglob('*') if f.is_file()])
    print(f"All files: {[f.name for f in all_files]}")
    groups, singles, assigned = {}, [], set()
    for f in all_files:
        if re.search(r'[-_](01|v2|v3)$', f.stem, re.IGNORECASE):
            singles.append(f); assigned.add(f)
    for f in all_files:
        if f in assigned: continue
        m = re.match(r'^(.*)\.(\d+)$', f.name)
        if m:
            base_name = m.group(1)
            base = root / base_name
            if base.is_file() and base.suffix.lower() in EXTENSIONS:
                if base not in groups: groups[base] = [base]
                groups[base].append(f); assigned.add(f); assigned.add(base)
            else: singles.append(f); assigned.add(f)
        else: pass
    for f in all_files:
        if f not in assigned: singles.append(f); assigned.add(f)
    return groups, singles

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--keep", type=int, default=1)
    parser.add_argument("--backup-dir", default=None)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--creo-mode", action="store_true")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    log_dir = Path(r"D:\AI\log\purge")
    log_dir.mkdir(parents=True, exist_ok=True)
    lock = PurgeLock(log_dir / "purge.lock")
    
    ok, err = lock.acquire()
    if not ok: print(f"Error: {err}"); sys.exit(1)

    try:
        groups, singles = get_groups(root)
        backup_dir = Path(args.backup_dir or root / "_purge_backup" / datetime.datetime.now().strftime("%Y%m%d"))
        
        report = {
            "root": str(root), 
            "keep": args.keep, 
                        target_path = base / target_name
                        if target_path.exists() and target_path not in members:
                            report["пропущено_с_причиной"].append(f"{base.name}: target {target_name} busy")
                            continue
                        try:
                            to_move = members[:-1]
                            for m in to_move:
                                size = m.stat().st_size
                                dest = backup_dir / m.name
                                backup_dir.mkdir(parents=True, exist_ok=True)
                                shutil.move(str(m), str(dest))
                                report["перенесено_парами"].append(f"{m.name}->{dest.name}")
                                report["освобождено_байт"] += size
                            shutil.move(str(latest), str(target_path))
                            report["перенесено_парами"].append(f"{latest.name}->{target_name}")
                        except Exception as e:
                            report["пропущено_с_причиной"].append(f"{base.name}: {e}")

            "было_версий": 0, 
            "перенесено_парами": [], 
            "пропущено_с_причиной": [], 
            "освобождено_байт": 0, 
            "seconds": 0
        }
        start_t = time.time()

        if args.creo_mode:
            print("--- CREO MODE ---")
            if not args.execute:
                for base, members in groups.items():
                    if len(members) > 1:
                        latest = members[-1]
                        print(f"PREVIEW: {latest.name} -> {latest.stem}.1 (New)")
                        for m in members[:-1]: print(f"  MOVE: {m.name} -> backup")
                return
            else:
                for base, members in groups.items():
                    if len(members) > 1:
                        latest = members[-1]
                        target_name = f"{latest.stem}.1"
                        target_path = base / target_name
                        try:
                            to_move = members[:-1]
                            for m in to_move:
                                size = m.stat().st_size
                                dest = backup_dir / m.name
                                backup_dir.mkdir(parents=True, exist_ok=True)
                                shutil.move(str(m), str(dest))
                                report["перенесено_парами"].append(f"{m.name}->{dest.name}")
                                report["освобождено_байт"] += size
                            if target_path.exists():
                                raise Exception(f"target {target_name} busy")
                            shutil.move(str(latest), str(target_path))
                            report["перенесено_парами"].append(f"{latest.name}->{target_name}")
                        except Exception as e:
                            report["пропущено_с_причиной"].append(f"{base.name}: {e}")
                return


        if not args.execute:
            print("--- PURGE PREVIEW ---")
            for base, members in groups.items():
                print(f"Group {base.name}: {[m.name for m in members]}")
            for s in singles: print(f"Single: {s.name}")
            return

        for base, members in groups.items():
            report["было_версий"] += len(members)
            to_keep = members[-args.keep:]
            to_move = members[:-args.keep]
            for m in to_move:
                try:
                    if m.exists():
                        dest = backup_dir / m.name
                        backup_dir.mkdir(parents=True, exist_ok=True)
                        size = m.stat().st_size
                        shutil.move(str(m), str(dest))
                        report["перенесено_парами"].append(f"{m.name}->{dest.name}")
                        report["освобождено_байт"] += size
                except Exception as e:
                    report["пропущено_с_причиной"].append(f"{m.name}: {e}")

        report["seconds"] = time.time() - start_t
        with open(log_dir / "last_purge.json", "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"Done. Report: {log_dir / 'last_purge.json'}")

    finally:
        lock.release()

if __name__ == "__main__":
    main()
