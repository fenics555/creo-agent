# -*- coding: utf-8 -*-
"""Р–РёРІР°СЏ РїСЂРѕР±Р° РјР°СЂС€СЂСѓС‚РѕРІ Р°РіРµРЅС‚Р° РџРћРЎР›Р• РІС…РѕРґР° (Р°РґРјРёРЅ РёР· secrets). РўРѕР»СЊРєРѕ С‡С‚РµРЅРёРµ."""
import urllib.request, urllib.error, json, time, os

BASE = "http://127.0.0.1:8765"
sec = json.load(open(r"D:\AI\tools\agent\data\secrets.json", encoding="utf-8"))

def post(path, obj, token=None):
    req = urllib.request.Request(BASE + path, data=json.dumps(obj).encode("utf-8"),
                                headers={"Content-Type": "application/json"}, method="POST")
    if token:
        req.add_header("X-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return "ERR", str(e).encode()

def get(path, token=None):
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header("X-Token", token)
    try:
        t = time.time()
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, len(r.read()), round(time.time() - t, 2)
    except urllib.error.HTTPError as e:
        return e.code, 0, 0
    except Exception as e:
        return "ERR:" + str(e)[:60], 0, 0

code, b = post("/login", {"login": sec.get("admin_login", "admin"), "password": sec["admin_pw"]})
print("login:", code, b[:200])
try:
    tok = json.loads(b).get("token")
except Exception:
    tok = None
if not tok:
    raise SystemExit("РЅРµС‚ С‚РѕРєРµРЅР° вЂ” РґР°Р»СЊС€Рµ РЅРµ РёРґС‘Рј")

for p in ["/health", "/api/programs", "/api/bases", "/api/jobs", "/pdfregistry",
          "/pdfstatus", "/panel", "/fleet/info", "/map", "/graph", "/ui/index.html"]:
    print("%-20s %s" % (p, get(p, tok)))

# РІРёР·Р°СЂРґС‹ СЃ С‚РѕРєРµРЅРѕРј (POST, С‚РѕР»СЊРєРѕ С‡С‚РµРЅРёРµ)
for p, obj in [("/wiz_orphan_preview", {"path": r"D:\AI\tools\agent\data"}),
               ("/wiz_plmtree", {"model": "23-1017gri-01"}),
               ("/wiz_purge_preview", {"folder": r"D:\AI\tools\agent\data"}),
               ("/wiz_preview", {"q": "test"})]:
    c, bb = post(p, obj, tok)
    print("%-22s %s  %s" % (p, c, bb[:180].decode("utf-8", "replace").replace("\n", " ")))

c, bb = post("/admin/users", {}, tok)
print("/admin/users(POST)", c, bb[:300].decode("utf-8", "replace"))
