# -*- coding: utf-8 -*-
# doctor6: диагностика входа. Запуск: python doctor6.py
import json, sys, traceback
from pathlib import Path
import urllib.request
AG = Path(r"D:\AI\tools\agent")

uf = AG / "data" / "users.json"
print("1) users.json:", "есть" if uf.exists() else "НЕТ")
if uf.exists():
    try:
        d = json.loads(uf.read_text(encoding="utf-8"))
        print("   ключи:", list(d.keys()) if isinstance(d, dict) else type(d))
        if isinstance(d, dict) and isinstance(d.get("users"), list):
            for u in d["users"]:
                print("   юзер:", u.get("login"), "| роль:", u.get("role"))
    except Exception as e:
        print("   БИТЫЙ JSON:", e)

sys.path.insert(0, str(AG))
try:
    import users
    import importlib; importlib.reload(users)
    r = users.check_login("admin", "admin")
    print("2) check_login(admin,admin):", "ОК, токен выдан" if r else "None (пароль неверный)")
except Exception:
    print("2) check_login УПАЛ:")
    traceback.print_exc()

req = urllib.request.Request("http://127.0.0.1:8765/login",
    data=json.dumps({"login": "admin", "pw": "admin"}).encode(),
    headers={"Content-Type": "application/json"})
try:
    resp = urllib.request.urlopen(req, timeout=10)
    print("3) HTTP /login:", resp.status, resp.read().decode()[:200])
except Exception as e:
    print("3) HTTP /login ОШИБКА:", e)

a = (AG / "agent.py").read_text(encoding="utf-8")
print("4) agent.py: login-обработчик JS:", "есть" if "a=='login'" in a else "НЕТ")
print("   catch на входе:", "есть" if "сервер недоступен" in a else "нет")
print("   модалка профиля:", "есть" if 'id="pro"' in a else "нет")