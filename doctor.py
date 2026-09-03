# -*- coding: utf-8 -*-
import re, sqlite3
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")

# 1) история: вычистить отравленные ответы (модель их копирует)
c = sqlite3.connect(str(AG / "data" / "agent.sqlite"), timeout=30)
n = c.execute("DELETE FROM history WHERE a = 'текст' OR a LIKE 'Извините%'").rowcount
c.commit(); c.close()
print("[+] история: удалено отравленных строк: %d" % n)

# 2) usage_state: фолбэк в базу после рестарта
up = AG / "usage_tools.py"; u = up.read_text(encoding="utf-8")
old = 'return "индекс ещё не строили. Скажи: usage_build full=1"'
if old in u and "из базы" not in u:
    u = u.replace(old,
        'try:\n        _c = _db(); _tot = _c.execute("SELECT COUNT(*) FROM usage").fetchone()[0]; _c.close()\n'
        '        if _tot: return "индекс готов (из базы): ссылок %d (имён %d). Корни: %s" % (_tot, STATE["names"], STATE.get("roots_info", ""))\n'
        '    except Exception: pass\n    ' + old, 1)
    up.write_text(u, encoding="utf-8"); print("[+] usage_state: видит базу после рестарта")

# 3) web_tools: алиас fetch_html
wp = AG / "web_tools.py"; w = wp.read_text(encoding="utf-8")
if "def fetch_html" not in w:
    w += "\ndef fetch_html(u):\n    return fetch(u)\n"
    wp.write_text(w, encoding="utf-8"); print("[+] web_tools: fetch_html = fetch")

# 4) plm: db()->_db(), usage-таблица
pp = AG / "plm_tools.py"; p = pp.read_text(encoding="utf-8"); ch = False
m = len(re.findall(r"c =\s*db\(\)", p))
if m:
    p = re.sub(r"c =\s*db\(\)", "c = _db()", p); ch = True
    print("[+] plm: db()->_db() в %d местах" % m)
if 'CREATE TABLE IF NOT EXISTS usage' not in p and 'CREATE TABLE IF NOT EXISTS items' in p:
    p = p.replace('c.execute("CREATE TABLE IF NOT EXISTS items',
                  'c.execute("CREATE TABLE IF NOT EXISTS usage(child TEXT, parent TEXT, parent_path TEXT)")\n    c.execute("CREATE TABLE IF NOT EXISTS items', 1)
    ch = True; print("[+] plm: usage создаётся заранее")
if ch: pp.write_text(p, encoding="utf-8")

# 5) core: chunker-предохранитель + корни в папку агента
cp = AG / "core.py"; c2 = cp.read_text(encoding="utf-8"); ch = False
if "s += size - ov" in c2:
    c2 = c2.replace("s += size - ov", "s += max(1, size - ov)", 1); ch = True
    print("[+] core: chunker защищён")
for var, fn in (("ROOTS", "kb_roots.txt"), ("EXCLUDE_FILE", "kb_exclude.txt")):
    line = '%s = BASE / "%s"' % (var, fn)
    if line in c2 and ('BASE / "agent" / "%s"' % fn) not in c2:
        c2 = c2.replace(line, line + '\nif not %s.exists(): %s = BASE / "agent" / "%s"' % (var, var, fn), 1)
        ch = True; print("[+] core: %s -> agent/" % var)
if ch: cp.write_text(c2, encoding="utf-8")

# 6) agent: страховки (_log, return)
ap = AG / "agent.py"; a = ap.read_text(encoding="utf-8"); ch = False
if "def _log(line): _log(line);" in a:
    a = a.replace("def _log(line): _log(line); LIVE.setdefault(client, []).append(line)",
                  "def _log(line): steps_log.append(line); LIVE.setdefault(client, []).append(line)", 1)
    ch = True; print("[+] agent: _log")
i = a.find('_SYS_CACHE["v"] = p + ')
if i >= 0 and "return _SYS_CACHE" not in a[i:i+300]:
    j = a.find("\n", i)
    a = a[:j+1] + '    return _SYS_CACHE["v"]\n' + a[j+1:]
    ch = True; print("[+] agent: return в build_system")
if ch: ap.write_text(a, encoding="utf-8")
print("ГОТОВО: .\\AI_RESTART.bat + Ctrl+F5")