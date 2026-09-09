# -*- coding: utf-8 -*-
# DOCTOR v29 — /login, /register, admin add и resetpw принимают пароль
# и в ключе "pw", и в ключе "password". Контракт на стороне сервера.
from pathlib import Path

AG = Path(r"D:\AI\tools\agent")
FAILS = []; SKIPS = []

def py_ok(t, n):
    try:
        compile(t, n, "exec"); return True
    except SyntaxError as e:
        print("[SYNTAX] %s: %s" % (n, e)); return False

a = (AG / "agent.py").read_text(encoding="utf-8")

PAIRS = [
    ('users.check_login(b.get("login"), b.get("pw"))',
     'users.check_login(b.get("login"), b.get("pw") or b.get("password"))'),
    ('okf = users.add_user(b.get("login"), b.get("pw"))',
     'okf = users.add_user(b.get("login"), b.get("pw") or b.get("password"))'),
    ('okf = users.add_user(b.get("login") or "", b.get("pw") or "", b.get("role") or "Инженер")',
     'okf = users.add_user(b.get("login") or "", b.get("pw") or b.get("password") or "", b.get("role") or "Инженер")'),
    ('okf, msg = users.admin_reset_password(b.get("login") or "", b.get("pw") or "")',
     'okf, msg = users.admin_reset_password(b.get("login") or "", b.get("pw") or b.get("password") or "")'),
]
for old, new in PAIRS:
    if new in a:
        SKIPS.append(old[:30]); print("[SKIP] уже есть: %s" % old[:40])
    elif old in a:
        a = a.replace(old, new, 1); print("[OK] %s" % old[:40])
    else:
        FAILS.append(old[:30]); print("[FAIL] якорь не найден: %s" % old[:60])

if not FAILS:
    if py_ok(a, "agent.py"):
        (AG / "agent.py").write_text(a, encoding="utf-8")
        print("[OK] agent.py записан")
    else:
        FAILS.append("compile"); print("[FAIL] компиляция, НЕ записан")
else:
    print("[WARN] agent.py НЕ записан из-за FAIL")

print("\n=== CHECK ===")
ax = (AG / "agent.py").read_text(encoding="utf-8")
print("вхождений b.get(\"password\"):", ax.count('b.get("password")'), "(ожидаю 4)")
print()
if FAILS: print("НЕ ПРИМЕНЕНО: " + "; ".join(FAILS))
else: print("ГОТОВО: .\\AI_RESTART.bat")
if SKIPS: print("ПРОПУЩЕНО: " + "; ".join(SKIPS))