# -*- coding: utf-8 -*-
import re
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")

# 1) plm: db() -> _db() (3 мёртвых инструмента)
pp = AG / "plm_tools.py"; u = pp.read_text(encoding="utf-8"); ch = False
n = len(re.findall(r"c =\s*db\(\)", u))
if n:
    u = re.sub(r"c =\s*db\(\)", "c = _db()", u); ch = True
    print("[+] plm: db()->_db() в %d местах" % n)
# 5) usage-таблица в _db
if 'CREATE TABLE IF NOT EXISTS usage' not in u and 'CREATE TABLE IF NOT EXISTS items' in u:
    u = u.replace('c.execute("CREATE TABLE IF NOT EXISTS items',
                  'c.execute("CREATE TABLE IF NOT EXISTS usage(child TEXT, parent TEXT, parent_path TEXT)")\n    c.execute("CREATE TABLE IF NOT EXISTS items', 1)
    ch = True; print("[+] plm: usage создаётся заранее")
# 6) _base: двойной бэкслеш -> одинарный
old_re = 'r"\\\\.(prt|asm|drw)(\\\\.\\d+)?$"'
if old_re in u:
    u = u.replace(old_re, 'r"\\.(prt|asm|drw)(\\.\\d+)?$"', 1); ch = True
    print("[+] plm: _base регекс исправлен")
if ch: pp.write_text(u, encoding="utf-8")

# 2) web_tools: алиас fetch_html для diag_web
wp = AG / "web_tools.py"; w = wp.read_text(encoding="utf-8")
if "def fetch_html" not in w:
    w += "\ndef fetch_html(u):\n    return fetch(u)\n"
    wp.write_text(w, encoding="utf-8"); print("[+] web_tools: fetch_html = fetch (diag_web оживает)")

# 3) core: chunker не зависает
cp = AG / "core.py"; c = cp.read_text(encoding="utf-8"); ch = False
if "s += size - ov" in c:
    c = c.replace("s += size - ov", "s += max(1, size - ov)", 1); ch = True
    print("[+] core: chunker защищён от overlap>=size")
# 4) ROOTS/EXCLUDE: фолбэк в папку агента
for var, fn in (("ROOTS", "kb_roots.txt"), ("EXCLUDE_FILE", "kb_exclude.txt")):
    line = '%s = BASE / "%s"' % (var, fn)
    if line in c and ('if not %s.exists(): %s = BASE / "agent"' % (var, var)) not in c:
        c = c.replace(line, line + '\nif not %s.exists(): %s = BASE / "agent" / "%s"' % (var, var, fn), 1)
        ch = True; print("[+] core: %s смотрит в agent/" % var)
if ch: cp.write_text(c, encoding="utf-8")

# 4b) find_tools: корни от сканера, если core пуст
fp = AG / "find_tools.py"; f = fp.read_text(encoding="utf-8")
if "core.read_roots()" in f and "scanner" not in f.split("core.read_roots()")[1][:60]:
    f = f.replace("roots = core.read_roots()", "roots = core.read_roots() or (__import__('scanner').read_roots())", 1)
    fp.write_text(f, encoding="utf-8"); print("[+] find_tools: корни от сканера")

# CHECK
u2 = (AG / "plm_tools.py").read_text(encoding="utf-8")
print("CHECK plm db():", len(re.findall(r"c =\s*db\(\)", u2)), "| _db():", u2.count("c = _db()"))
print("CHECK fetch_html:", "def fetch_html" in (AG / "web_tools.py").read_text(encoding="utf-8"))
c2 = (AG / "core.py").read_text(encoding="utf-8")
print("CHECK chunker:", "max(1, size - ov)" in c2, "| ROOTS-фолбэк:", 'BASE / "agent" / "kb_roots.txt"' in c2)
print("ГОТОВО: .\\AI_RESTART.bat, затем GIT_SYNC.bat")