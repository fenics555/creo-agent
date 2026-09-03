# -*- coding: utf-8 -*-
import re, shutil
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")

# 1) протокол: убрать SKILL без грамматики -> включится DEFAULT_PROTO
p = Path(r"D:\AI\repo\SKILL_agent_protocol.md")
if p.exists():
    t = p.read_text(encoding="utf-8", errors="ignore")
    print("ГОЛОВА SKILL:", t[:250].replace("\n", " | "))
    if "[TOOL:" not in t:
        shutil.move(str(p), str(p) + ".bak")
        print("[+] SKILL без грамматики [TOOL:] -> .bak; включится DEFAULT_PROTO")
    else:
        print("[=] грамматика в SKILL на месте")

# 2) web_tools: алиас fetch_html (чинит diag_web/probe_run)
wp = AG / "web_tools.py"; w = wp.read_text(encoding="utf-8")
if "def fetch_html" not in w:
    w += "\ndef fetch_html(u):\n    return fetch(u)\n"
    wp.write_text(w, encoding="utf-8"); print("[+] web_tools: fetch_html = fetch")

# 3) plm: db()->_db(), usage-таблица, регекс _base
pp = AG / "plm_tools.py"; u = pp.read_text(encoding="utf-8"); ch = False
n = len(re.findall(r"c =\s*db\(\)", u))
if n:
    u = re.sub(r"c =\s*db\(\)", "c = _db()", u); ch = True
    print("[+] plm: db()->_db() в %d местах" % n)
if 'CREATE TABLE IF NOT EXISTS usage' not in u and 'CREATE TABLE IF NOT EXISTS items' in u:
    u = u.replace('c.execute("CREATE TABLE IF NOT EXISTS items',
                  'c.execute("CREATE TABLE IF NOT EXISTS usage(child TEXT, parent TEXT, parent_path TEXT)")\n    c.execute("CREATE TABLE IF NOT EXISTS items', 1)
    ch = True; print("[+] plm: usage создаётся заранее")
bad_re = 'r"\\\\.(prt|asm|drw)(\\\\.\\d+)?$"'
if bad_re in u:
    u = u.replace(bad_re, 'r"\\.(prt|asm|drw)(\\.\\d+)?$"', 1); ch = True
    print("[+] plm: _base регекс")
if ch: pp.write_text(u, encoding="utf-8")

# 4) core: chunker-предохранитель + корни в папку агента
cp = AG / "core.py"; c = cp.read_text(encoding="utf-8"); ch = False
if "s += size - ov" in c:
    c = c.replace("s += size - ov", "s += max(1, size - ov)", 1); ch = True
    print("[+] core: chunker защищён")
for var, fn in (("ROOTS", "kb_roots.txt"), ("EXCLUDE_FILE", "kb_exclude.txt")):
    line = '%s = BASE / "%s"' % (var, fn)
    if line in c and ('BASE / "agent" / "%s"' % fn) not in c:
        c = c.replace(line, line + '\nif not %s.exists(): %s = BASE / "agent" / "%s"' % (var, var, fn), 1)
        ch = True; print("[+] core: %s -> agent/" % var)
if ch: cp.write_text(c, encoding="utf-8")

print("ГОТОВО: .\\AI_RESTART.bat + Ctrl+F5")