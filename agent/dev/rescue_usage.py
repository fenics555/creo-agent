# -*- coding: utf-8 -*-
"""Перед удалением бэкака 6,38 ГБ спасаем единственное, чего нет в текущей базе.
Сверка показала: usage (2400) и usage_meta (53) в старом бэкапе, в текущей — 0.
Выгружаем их в компактный JSON рядом с бэкапом — восстановимо при需要的."""
import json, sqlite3, time

OLD = r"D:\AI\tools\agent\data\backup\pre_kbclean_20260923_agent.sqlite"
NEW = r"D:\AI\tools\agent\data\agent.sqlite"
OUT = r"D:\AI\tools\agent\data\backup\pre_kbclean_rescue_usage.json"

def snap(p):
    c = sqlite3.connect("file:%s?mode=ro" % p.replace("\\", "/"), uri=True)
    out = {}
    for t in ("usage", "usage_meta", "trail_scans", "history"):
        try:
            cur = c.execute("select * from %s" % t)
            cols = [d[0] for d in cur.description]
            out[t] = {"cols": cols, "rows": cur.fetchall()}
        except Exception as e:
            out[t] = {"error": str(e)}
    c.close()
    return out

old, new = snap(OLD), snap(NEW)
rescued = {}
for t in old:
    o = len(old[t].get("rows", []))
    n = len(new.get(t, {}).get("rows", []))
    print("%-12s старый=%-6d текущий=%-6d %s" % (t, o, n, "СПАСАТЬ" if o > n else "покрыто"))
    if o > n:
        rescued[t] = old[t]

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(rescued, f, ensure_ascii=False, indent=1)
print("\nспасено таблиц: %d -> %s (%.1f КБ)" % (len(rescued), OUT, __import__("os").path.getsize(OUT) / 1024.0))