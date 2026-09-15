# doctor5.py — ОКНО ДАВЫДОВКИ В ДОМЕ: маршрут /rename, инвентаризация адресов, creoson 8080 остаётся родным
# -*- coding: utf-8 -*-
import os, re, sys, shutil, subprocess, urllib.request
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
AG = r"D:\AI\tools\agent"; BAK = os.path.join(AG, "data", "backup"); os.makedirs(BAK, exist_ok=True)
src = None
for root in (r"D:\AI\repo", r"D:\AI\tools", r"D:\AI"):
    for dp, dn, fn in os.walk(root):
        if dp.count(os.sep) - root.count(os.sep) > 3: continue
        dn[:] = [d for d in dn if d not in (".git", "node_modules")]
        if "index_rename.html" in fn: src = os.path.join(dp, "index_rename.html"); break
    if src: break
print("источник страницы:", src or "НЕ НАЙДЕН")
if not src: print("VERDICT 5: STOP, страницы нет"); sys.exit(1)
dst = os.path.join(AG, "ui", "rename.html")
if os.path.exists(dst): shutil.copy2(dst, dst + ".bak")
shutil.copy2(src, dst); print("страница скопирована:", dst, os.path.getsize(dst), "байт")
t = open(dst, encoding="utf-8", errors="replace").read()
urls = sorted(set(re.findall(r"https?://127\.0\.0\.1:\d+|https?://localhost:\d+", t)))
print("адреса в странице:", urls or "внешних адресов нет")
print("fetch/xhr пути:", sorted(set(re.findall(r"""(?:fetch|open)\(\s*["']([^"']+)["']""", t)))[:20])
# creoson 8080 оставляем как есть: страница говорит с ним напрямую, наш сервер на том же порту
ap = os.path.join(AG, "agent.py"); s = open(ap, encoding="utf-8", errors="replace").read()
ANCH = 'elif p == "/panel":'
if '"/rename"' not in s:
    shutil.copy2(ap, os.path.join(BAK, "pre_d5_agent.py.bak"))
    blk = ('        elif p == "/rename":\n'
           '            _rp = os.path.join(os.path.dirname(UI_FILE), "rename.html")\n'
           '            try: _bd = open(_rp, "rb").read()\n'
           '            except Exception: _bd = "rename.html not found".encode("utf-8")\n'
           '            self.send_response(200)\n'
           '            self.send_header("Content-Type", "text/html; charset=utf-8")\n'
           '            self.end_headers()\n'
           '            self.wfile.write(_bd)\n'
           '            return\n')
    if ANCH not in s: print("VERDICT 5: якорь /panel не найден, STOP"); sys.exit(1)
    s = s.replace(ANCH, blk + "        " + ANCH, 1)
    open(ap, "w", encoding="utf-8", newline="").write(s)
    rc = subprocess.run([sys.executable, "-m", "py_compile", ap]).returncode
    if rc != 0:
        shutil.copy2(os.path.join(BAK, "pre_d5_agent.py.bak"), ap)
        print("VERDICT 5: COMPILE FAIL, ROLLBACK"); sys.exit(1)
    print("маршрут /rename вшит, компиляция чистая")
else:
    print("маршрут /rename уже есть")
try:
    with urllib.request.urlopen("http://127.0.0.1:8765/rename", timeout=10) as r:
        body = r.read().decode("utf-8", "ignore")
    print("проба /rename:", r.status, "байт:", len(body), "| заголовок страницы:", body[:60].replace("\n", " "))
except Exception as e:
    print("проба /rename ОШИБКА (нужен рестарт агента?):", e)
print("VERDICT 5: готово. Открой http://127.0.0.1:8765/rename и нажми «Сканировать папку»:")
print("страница говорит с creoson 8080 напрямую, таблица и граф должны наполниться без правок её кода.")
print("Боевые переименования остаются через витрину и согласование, как договорились.")