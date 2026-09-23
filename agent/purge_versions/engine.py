import os, sys, argparse, shutil, json, time, datetime, re, subprocess
from pathlib import Path

EXTS = {'.prt', '.asm', '.drw', '.frm', '.lay', '.sec'}

# --- автономная программа: всё своё рядом, логи по закону дома ---
PROG_DIR = Path(__file__).resolve().parent
LOG_DIR = Path(r"D:\AI\log\purge_versions")
SETTINGS_FILE = PROG_DIR / "gui_settings.json"

class Lock:
    def __init__(self, p): self.p = Path(p)
    def acq(self):
        if self.p.exists():
            try:
                p_s = self.p.read_text().strip()
                if p_s:
                    p = int(p_s)
                    cmd = f'tasklist /FI "PID eq {p}"'
                    output = subprocess.check_output(cmd, shell=True).decode(errors='ignore')
                    if str(p) in output: return False, f"Locked by {p}"
            except: pass
        self.p.write_text(str(os.getpid()))
        return True, None
    def rel(self):
        if self.p.exists():
            try:
                if int(self.p.read_text().strip()) == os.getpid():
                    self.p.unlink()
            except: pass

def get_groups(root):
    root = Path(root)
    if not root.exists(): return {}, []
    fs = sorted([f for f in root.iterdir() if f.is_file()])
    grps, sings, ass = {}, [], set()
    for f in fs:
        is_versioned = bool(re.match(r'.+\.\d+$', f.name))
        is_ext = f.suffix.lower() in EXTS
        if not (is_versioned or is_ext): continue
        if re.search(r'[-_](01|v2|v3)$', f.stem, re.IGNORECASE):
            if f.name not in ass:
                sings.append(f)
                ass.add(f.name)
            continue
        m = re.match(r'^(.*)\.(\d+)$', f.name)
        if m:
            base_name = m.group(1)
            base_path = root / base_name
            if base_path.is_file() and base_path.suffix.lower() in EXTS:
                if base_name not in grps: grps[base_name] = [base_path]
                grps[base_name].append(f)
                ass.add(f.name)
                ass.add(base_name)
            else:
                # базового файла без версии может НЕ быть — тогда не выдумываем его в составе группы
                # (иначе в отчёте появляется ложное "пропущено: файла нет"). Правка 23.09.2026.
                if base_name not in grps: grps[base_name] = []
                grps[base_name].append(f)
                if f.name not in ass:
                    sings.append(f)
                    ass.add(f.name)
                ass.add(base_name)
        else:
            if f.suffix.lower() in EXTS:
                if f.name not in ass:
                    ass.add(f.name)
    for f in fs:
        if f.name not in ass and f.suffix.lower() in EXTS:
            if f not in sings:
                sings.append(f)
                ass.add(f.name)
    path_grps = {root / name: members for name, members in grps.items()}
    return path_grps, sings

def preview(root: Path, keep: int, creo_mode: bool) -> dict:
    grps, sings = get_groups(root)
    res = {"groups": [], "singles": []}
    if creo_mode:
        for b, m in grps.items():
            if len(m) > 1:
                lt = m[-1]
                target_name = f"{lt.stem}.1"
                res["groups"].append({"base": str(b), "members": [x.name for x in m], "target": target_name})
            else:
                res["singles"].append(m[0].name)
        res["singles"].extend([x.name for x in sings])
    else:
        for b, m in grps.items():
            res["groups"].append({"base": str(b), "members": [x.name for x in m]})
        res["singles"] = [x.name for x in sings]
    return res

def execute(root: Path, keep: int, creo_mode: bool, backup_dir: Path) -> dict:
    grps, sings = get_groups(root)
    rep = {
        "root": str(root), 
        "keep": keep, 
        "было_версий": 0, 
        "перенесено_парами": [], 
        "пропущено_с_причиной": [], 
        "освобождено_байт": 0, 
        "seconds": 0
    }
    st = time.time()
    if creo_mode:
        for b, m in grps.items():
            if len(m) > 1:
                lt = m[-1]
                target_name = f"{lt.stem}.1"
                target_path = b.parent / target_name
                if target_path.exists() and target_path not in m:
                    rep["пропущено_с_причиной"].append(f"{b.name}: target {target_name} busy")
                    continue
                try:
                    for x in m[:-1]:
                        sz = x.stat().st_size
                        dst = backup_dir / x.name
                        backup_dir.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(x), str(dst))
                        rep["перенесено_парами"].append(f"{x.name}->{dst.name}")
                        rep["освобождено_байт"] += sz
                    if lt.name != target_name:
                        shutil.move(str(lt), str(target_path))
                        rep["перенесено_парами"].append(f"{lt.name}->{target_name}")
                except Exception as e:
                    rep["пропущено_с_причиной"].append(f"{b.name}: {e}")
    else:
        for b, m in grps.items():
            rep["было_версий"] += len(m)
            for x in m[:-keep]:
                try:
                    sz = x.stat().st_size
                    dst = backup_dir / x.name
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(x), str(dst))
                    rep["перенесено_парами"].append(f"{x.name}->{dst.name}")
                    rep["освобождено_байт"] += sz
                except Exception as e:
                    rep["пропущено_с_причиной"].append(f"{x.name}: {e}")
    
    rep["seconds"] = time.time() - st
    return rep
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True); p.add_argument("--keep", type=int, default=1)
    p.add_argument("--backup-dir"); p.add_argument("--execute", action="store_true")
    p.add_argument("--creo-mode", action="store_true"); p.add_argument("--preview", action="store_true")
    a = p.parse_args()
    
    root = Path(a.root).resolve()
    ld = LOG_DIR
    ld.mkdir(parents=True, exist_ok=True)
    l = Lock(ld / "purge.lock")
    
    ok, err = l.acq()
    if not ok: print(f"Err: {err}"); sys.exit(1)
    
    try:
        if a.execute:
            bd = Path(a.backup_dir or root / "_purge_backup" / datetime.datetime.now().strftime("%Y%m%d"))
            rep = execute(root, a.keep, a.creo_mode, bd)
            with open(ld / "last_purge.json", "w", encoding="utf-8") as f:
                json.dump(rep, f, ensure_ascii=False, indent=2)
            print(f"Done. Report: {ld / 'last_purge.json'}")
        else:
            res = preview(root, a.keep, a.creo_mode)
            print(json.dumps(res, ensure_ascii=False))
            
    finally: l.rel()

if __name__ == "__main__":
    main()
