# -*- coding: utf-8 -*-
"""Живая проба всех маршрутов агента (окно витрины) — только чтение, без /ask."""
import urllib.request, urllib.error, json, time

BASE = "http://127.0.0.1:8765"
ROUTES = ["/status", "/health", "/api/programs", "/api/bases", "/api/jobs",
          "/log", "/settings", "/fleet/info", "/panel",
          "/wiz_orphan_preview?path=D%3A%5CAI%5Ctools%5Cagent%5Cdata",
          "/wiz_plmtree", "/profile", "/admin/users",
          "/map", "/graph", "/pdfregistry", "/pdfstatus"]

def probe(path, data=None):
    url = BASE + path
    try:
        req = urllib.request.Request(url, data=data)
        t = time.time()
        with urllib.request.urlopen(req, timeout=25) as r:
            b = r.read()
            return r.status, len(b), round(time.time() - t, 2), b[:160].decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, 0, 0, "HTTPError " + e.reason
    except Exception as e:
        return "ERR", 0, 0, str(e)[:120]

print("%-38s %6s %9s %7s  %s" % ("маршрут", "код", "байт", "сек", "начало"))
for r_ in ROUTES:
    code, n, sec, head = probe(r_)
    print("%-38s %6s %9s %7s  %s" % (r_, code, n, sec, head.replace("\n", " ")[:120]))

# главная страница окна
code, n, sec, head = probe("/")
print("%-38s %6s %9s %7s  %s" % ("/ (окно витрины)", code, n, sec, head.replace("\n", " ")[:120]))