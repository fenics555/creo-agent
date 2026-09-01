# -*- coding: utf-8 -*-
import io
p = r"D:\AI\tools\agent\usage_tools.py"
s = io.open(p, encoding="utf-8").read()

NEW_BUILD = '''def build_usage(full=False):
    if STATE["busy"]:
        return
    STATE.update(busy=True, done=0, total=0, links=0, error="")
    trace("USAGE build", "START", 0, "полный" if full else "инкремент")
    try:
        c = _db()
        names = set()
        for (n,) in c.execute("SELECT name FROM models WHERE ext IN ('prt','asm')"):
            names.add(re.sub(r"\\.(prt|asm)(\\.\\d+)?$", "", n).upper())
        c.execute("DROP TABLE IF EXISTS usage_new")
        c.execute("CREATE TABLE usage_new(child TEXT, parent TEXT, parent_path TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS usage_meta(path TEXT PRIMARY KEY, mtime REAL)")
        has_old = c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='usage'").fetchone()
        old_meta = {}
        if has_old and not full:
            c.execute("CREATE INDEX IF NOT EXISTS ix_usage_pp ON usage(parent_path)")
            old_meta = dict(c.execute("SELECT path, mtime FROM usage_meta").fetchall())
        pats = SC._pats()
        tasks = []
        for root in SC.read_roots():
            if not os.path.exists(root):
                continue
            for dp, dn, fns in os.walk(root):
                dn[:] = [d for d in dn if not SC.is_excluded(os.path.join(dp, d) + "/", pats)]
                tasks += [os.path.join(dp, fn) for fn in fns if re.search(r"\\.asm(?:\\.\\d+)?$", fn.lower())]
        STATE["total"] = len(tasks)
        rows, new_meta, reused = [], {}, 0
        for path in tasks:
            try:
                mt = os.path.getmtime(path)
            except Exception:
                mt = 0.0
            new_meta[path] = mt
            parent = re.sub(r"\\.\\d+$", "", os.path.basename(path)).upper()
            if has_old and not full and old_meta.get(path) == mt:
                rows += c.execute("SELECT child, parent, parent_path FROM usage WHERE parent_path=?", (path,)).fetchall()
                reused += 1
            else:
                try:
                    data = open(path, "rb").read()
                except Exception:
                    data = b""
                found = set()
                for mm in RUN.finditer(data):
                    ref = mm.group(0).decode().upper()
                    if ref in names and ref != parent:
                        found.add(ref)
                rows += [(ref.lower(), parent.lower(), path) for ref in found]
            STATE["done"] += 1
            STATE["links"] = len(rows)
        c.executemany("INSERT INTO usage_new(child,parent,parent_path) VALUES(?,?,?)", rows)
        c.execute("DELETE FROM usage_meta")
        c.executemany("INSERT INTO usage_meta(path,mtime) VALUES(?,?)", list(new_meta.items()))
        c.execute("DROP TABLE IF EXISTS usage_old")
        if has_old:
            c.execute("ALTER TABLE usage RENAME TO usage_old")
        c.execute("ALTER TABLE usage_new RENAME TO usage")
        c.execute("DROP TABLE IF EXISTS usage_old")
        c.execute("CREATE INDEX IF NOT EXISTS ix_usage_child ON usage(child)")
        c.commit(); c.close()
        STATE["links"] = len(rows)
        STATE["finished"] = time.strftime("%d.%m %H:%M")
        trace("USAGE build", "OK", 0, "%d ссылок, без перечитывания %d файлов" % (len(rows), reused))
    except Exception as e:
        STATE["error"] = str(e)[:200]
        trace("USAGE build", "ERR", 0, str(e)[:120])
    finally:
        STATE["busy"] = False
'''

NEW_TOOL = '''def tool_usage_build(full=0, **kw):
    threading.Thread(target=build_usage, args=(str(full) in ("1", "true", "True"),), daemon=True).start()
    return "индекс строится в фоне: старое работает до swap, неизменное не перечитывается; прогресс — usage_state; full=1 — полная пересборка"
'''

def splice(src, head, new):
    i = src.find(head)
    if i < 0:
        print("[x] не найдено: %s" % head); return src, False
    j = src.find("\ndef ", i + 10)
    if j < 0: j = len(src)
    return src[:i] + new + src[j:], True

if "usage_new" in s:
    print("[~] build_usage уже инкрементальный")
else:
    s, ok1 = splice(s, "def build_usage(", NEW_BUILD)
    if ok1: print("[+] build_usage: инкремент + атомарный swap")

if "args=(str(full)" in s:
    print("[~] tool_usage_build уже с full")
else:
    s, ok2 = splice(s, "def tool_usage_build(", NEW_TOOL)
    if ok2: print("[+] tool_usage_build: параметр full")

io.open(p, "w", encoding="utf-8").write(s)
print("ГОТОВО: .\\AI_RESTART.bat, затем usage_build")