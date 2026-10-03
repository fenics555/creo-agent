# -*- coding: utf-8 -*-
"""Живая проверка ручек агента, читающих/пишущих в data (вход админом из secrets.json).
Пробы идут на маленькой папке D:\\AI\\log\\urn\\cline — боевую data/ не трогаем."""
import urllib.request, urllib.error, json, time, os, tempfile, pathlib

BASE = "http://127.0.0.1:8765"
sec = json.load(open(r"D:\AI\tools\agent\data\secrets.json", encoding="utf-8"))
TMP = r"D:\AI\log\urn\cline\purge_probe"
os.makedirs(TMP, exist_ok=True)


def post(path, obj, token=None, timeout=120):
    req = urllib.request.Request(BASE + path, data=json.dumps(obj).encode("utf-8"),
                                 headers={"Content-Type": "application/json"}, method="POST")
    if token:
        req.add_header("X-Token", token)
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, round(time.time() - t, 2), r.read()
    except urllib.error.HTTPError as e:
        return e.code, round(time.time() - t, 2), e.read()
    except Exception as e:
        return "ERR", round(time.time() - t, 2), str(e).encode()


def get(path, token=None):
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header("X-Token", token)
    t = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, round(time.time() - t, 2), r.read()
    except urllib.error.HTTPError as e:
        return e.code, round(time.time() - t, 2), e.read()
    except Exception as e:
        return "ERR", round(time.time() - t, 2), str(e).encode()


code, dt, b = post("/login", {"login": sec.get("admin_login", "admin"), "password": sec["admin_pw"]})
tok = json.loads(b).get("token")
print("login: %s  %.2f с  токен=%s" % (code, dt, "есть" if tok else "НЕТ"))

print("\n== ЧТЕНИЕ (хелперы по хранилищу) ==")
for p in ["/health", "/api/bases", "/api/jobs", "/api/programs", "/pdfregistry", "/panel", "/map"]:
    c, dt, bb = get(p, tok)
    print("%-16s %-4s %6.2f с  %7d Б" % (p, c, dt, len(bb)))

print("\n== ОКНА-ПРОБЫ на маленькой папке %s ==" % TMP)
for p, obj in [("/wiz_purge_preview", {"root": TMP, "keep": 1}),
               ("/wiz_orphan_preview", {"folder": TMP}),
               ("/wiz_preview", {"old": "a", "new": "b"}),
               ("/wiz_plmtree", {"model": "23-1017gri-01"})]:
    c, dt, bb = post(p, obj, tok)
    print("%-22s %-4s %6.2f с  %s" % (p, c, dt, bb[:150].decode("utf-8", "replace").replace("\n", " ")))

print("\n== ключевой вопрос: ручка без нужного ключа ==")
c, dt, bb = post("/wiz_purge_preview", {"folder": TMP}, tok)
print("wiz_purge_preview БЕЗ 'root': %s  %.2f с  %s" % (c, dt, bb[:120].decode("utf-8", "replace")))

print("\n== осталось в папке проб ==")
print(os.listdir(TMP))