# -*- coding: utf-8 -*-
"""Живая приёмка экрана «Проверки дома» (волна 11): маршрут /wiz_check_run + фронт витрины.

Ничего не меняет: маршрут только читает (checks_run), пишет лишь отчёт в log\\reports
по галочке «записать отчёт». Проба бьёт по ОДНОЙ лёгкой проверке (only), чтобы не жечь
время ноги полным прогоном 11 проверок.
Запуск: cmd /c "python -X utf8 dev\\wiz_check_live.py > data\\tmp\\wiz_check_live.txt 2>&1"
"""
import json
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8765"
SEC = r"D:\AI\tools\agent\data\secrets.json"
APPJS = r"D:\AI\tools\agent\ui\app.js"
IDX = r"D:\AI\tools\agent\ui\index.html"

ok = [0]
fail = [0]


def crit(cond, text):
    if cond:
        ok[0] += 1
        print("  OK   %s" % text)
    else:
        fail[0] += 1
        print("  ПРОВАЛ %s" % text)


def post(path, obj, token=None, timeout=180):
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


def get(path, token=None, timeout=30):
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header("X-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return "ERR", str(e).encode()


sec = json.load(open(SEC, encoding="utf-8"))
code, dt, b = post("/login", {"login": sec.get("admin_login", "admin"), "password": sec["admin_pw"]})
tok = json.loads(b).get("token")
print("login: %s  %.2f с  токен=%s" % (code, dt, "есть" if tok else "НЕТ"))
crit(bool(tok), "вход админом, токен получен")

print("\n== ФРОНТ ВИТРИНЫ (файлы на диске) ==")
idx = open(IDX, encoding="utf-8").read()
app = open(APPJS, encoding="utf-8").read()
crit('data-act="open_checks"' in idx, "index.html: кнопка open_checks в меню витрины")
crit('id="wiz_checks"' in idx, "index.html: блок окна wiz_checks")
crit('id="ck_scope"' in idx and 'id="ck_only"' in idx, "index.html: поля области и списка проверок")
crit('data-act="wiz_check_run"' in idx, "index.html: кнопка прогона")
crit("a=='open_checks'" in app, "app.js: обработчик открытия экрана")
crit("a=='close_checks'" in app, "app.js: обработчик закрытия экрана")
crit("a=='wiz_check_run'" in app and "'/wiz_check_run'" in app, "app.js: вызов маршрута /wiz_check_run")
crit("document.getElementById('wiz_checks')" in app, "app.js: экран ссылается на wiz_checks")

print("\n== ЖИВОЙ МАРШРУТ /wiz_check_run ==")
c, dt, b = post("/wiz_check_run", {"token": tok, "only": "hol_check", "report": ""}, tok)
print("ответ: код=%s  %.2f с  %d Б" % (c, dt, len(b)))
g = json.loads(b)
crit(g.get("error") in (None, ""), "маршрут ответил без ошибки (error=%r)" % g.get("error"))
r = g.get("result") or {}
crit(isinstance(r, dict) and r.get("checks") == 1, "прогон ограничен одной проверкой (checks=%r)" % r.get("checks"))
rows = r.get("rows") or []
crit(len(rows) == 1 and rows[0]["id"] == "hol_check", "строка проверки вернулась: %s"
     % (rows[0]["id"] if rows else "—"))
crit(all(k in r for k in ("passed", "failed_checks", "items", "percent", "secs", "rows")),
     "в ответе все поля сводки (passed/failed_checks/items/percent/secs/rows)")
crit(isinstance(rows[0].get("items"), list) if rows else False,
     "у строки есть список items (его рисует фронт)")
crit(rows[0].get("ok") in (True, False) if rows else False,
     "у строки есть вердикт ok (%r)" % (rows[0].get("ok") if rows else None))
crit(g.get("report") in (None, ""), "без галочки отчёт не пишется (report=%r)" % g.get("report"))

print("\n== ГАЛКА ОТЧЁТА ==")
c2, dt2, b2 = post("/wiz_check_run", {"token": tok, "only": "hol_check", "report": "true"}, tok)
g2 = json.loads(b2)
rep = g2.get("report")
print("report: %s" % rep)
crit(bool(rep) and rep.endswith(".md"), "отчёт записан в log\\reports")

print("\n== АГЕНТ ОТДАЁТ НОВЫЙ ФРОНТ ==")
c3, body = get("/", tok)
crit(c3 == 200, "главная страница отдаётся (код %s)" % c3)
c4, body4 = get("/app.js", tok)
crit(c4 == 200 and b"wiz_check_run" in body4, "app.js с новым обработчиком отдан по HTTP (код %s)" % c4)

print("\nИТОГ: критериев %d, провалов %d" % (ok[0] + fail[0], fail[0]))
print("ВЕРДИКТ: %s" % ("ГОДЕНО" if not fail[0] else "НЕ ГОДЕНО"))
raise SystemExit(1 if fail[0] else 0)