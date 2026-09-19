def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True); p.add_argument("--keep", type=int, default=1)
    p.add_argument("--backup-dir"); p.add_argument("--execute", action="store_true")
    p.add_argument("--creo-mode", action="store_true"); p.add_argument("--preview", action="store_true")
    a = p.parse_args()
    
    root = Path(a.root).resolve()
    ld = Path(r"D:\AI\log\purge")
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
