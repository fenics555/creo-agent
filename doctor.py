# -*- coding: utf-8 -*-
# DOCTOR v22 — удаление пользователей: функция в users.py, op delete в agent.py,
# кнопка «удалить» в админке + чистка тестовых cline_fb / cline_fb2.
# ЗАПУСКАТЬ ОДИН РАЗ. После: .\AI_RESTART.bat + Ctrl+F5
import sys
from pathlib import Path

AG = Path(r"D:\AI\tools\agent")
FAILS = []; SKIPS = []

def py_ok(t, n):
    try:
        compile(t, n, "exec"); return True
    except SyntaxError as e:
        print("[SYNTAX] %s: %s" % (n, e)); return False

def save(p, t):
    if py_ok(t, str(p)):
        p.write_text(t, encoding="utf-8"); return True
    FAILS.append(p.name); return False

# --- 1. users.py: функция admin_delete_user (любая форма users.json) ---
u = (AG / "users.py").read_text(encoding="utf-8")
if "def admin_delete_user" in u:
    SKIPS.append("users.py"); print("[SKIP] users.py: функция уже есть")
else:
    fn = '''

def admin_delete_user(login):
    """Удалить пользователя из users.json (любая форма файла). True, если удалил."""
    import json as _json
    from pathlib import Path as _P
    p = _P(__file__).resolve().parent / "data" / "users.json"
    d = _json.loads(p.read_text(encoding="utf-8"))
    def _hit(x):
        return isinstance(x, dict) and x.get("login") == login
    ch = False
    if isinstance(d, list):
        n = [x for x in d if not _hit(x)]; ch = len(n) != len(d); out = n
    elif isinstance(d, dict) and isinstance(d.get("users"), list):
        n = [x for x in d["users"] if not _hit(x)]; ch = len(n) != len(d["users"]); d["users"] = n; out = d
    elif isinstance(d, dict) and login in d:
        d.pop(login); ch = True; out = d
    else:
        out = d
    if ch:
        p.write_text(_json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return ch
'''
    if save(AG / "users.py", u + fn):
        print("[OK] users.py: admin_delete_user добавлена")

# --- 2. agent.py: операция delete в /admin/users ---
a = (AG / "agent.py").read_text(encoding="utf-8")
if 'op == "delete"' in a:
    SKIPS.append("agent op"); print("[SKIP] agent.py: op delete уже есть")
else:
    anchor = '            elif op == "resetpw":'
    block = '''            elif op == "delete":
                lg = (b.get("login") or "").strip()
                if not lg:
                    self._j({"ok": False, "msg": "логин пустой"}, 400); return
                if lg == cl:
                    self._j({"ok": False, "msg": "нельзя удалить самого себя"}, 400); return
                us = users.list_users()
                tgt = [x for x in us if x.get("login") == lg]
                if not tgt:
                    self._j({"ok": False, "msg": "логин %s не найден" % lg}, 404); return
                adm = [x for x in us if x.get("role") == "Администратор" and x.get("login") != lg]
                if tgt[0].get("role") == "Администратор" and not adm:
                    self._j({"ok": False, "msg": "нельзя удалить последнего администратора"}, 400); return
                okf = users.admin_delete_user(lg)
                self._j({"ok": okf, "msg": ("пользователь %s удалён" % lg) if okf else "ошибка удаления"})
'''
    if anchor in a:
        if save(AG / "agent.py", a.replace(anchor, block + anchor, 1)):
            print("[OK] agent.py: op delete добавлен")
    else:
        FAILS.append("agent op anchor"); print("[FAIL] agent.py: якорь resetpw не найден")

# --- 3. agent.py PAGE: кнопка «удалить» + обработчик клика ---
a = (AG / "agent.py").read_text(encoding="utf-8")
if 'data-act="do_del"' in a:
    SKIPS.append("page"); print("[SKIP] PAGE: кнопка удаления уже есть")
else:
    old_btn = ">сброс pw</button>"
    new_btn = '''>сброс pw</button> <button data-act="do_del" data-login="'+att(u.login)+'" style="background:#6f2b2b;color:#fff;border:0;border-radius:4px;padding:4px 8px;cursor:pointer">удалить</button>'''
    old_h = "else if(a=='do_resetpw'){"
    new_h = '''else if(a=='do_del'){var lgn=el.getAttribute('data-login');if(!confirm('Удалить пользователя '+lgn+'?'))return;J('/admin/users',{token:TK,op:'delete',login:lgn}).then(function(r){alert(r.msg||'ок');if(r.ok){document.getElementById('adm').style.display='none';setTimeout(function(){document.getElementById('adm').style.display='flex';document.querySelector('[data-act="openadm"]').click()},100)}})}
else if(a=='do_resetpw'){'''
    if old_btn in a and old_h in a:
        a2 = a.replace(old_btn, new_btn, 1).replace(old_h, new_h, 1)
        if save(AG / "agent.py", a2):
            print("[OK] PAGE: кнопка и обработчик удаления добавлены")
    else:
        FAILS.append("page anchors"); print("[FAIL] agent.py: якоря кнопки/обработчика не найдены")

# --- 4. чистка тестовых пользователей новой функцией ---
sys.path.insert(0, str(AG))
try:
    import users as US
    if hasattr(US, "admin_delete_user"):
        for lg in ("cline_fb", "cline_fb2"):
            print("[OK] clean %s: %s" % (lg, US.admin_delete_user(lg)))
    else:
        FAILS.append("clean"); print("[FAIL] чистка: функция не появилась")
except Exception as e:
    FAILS.append("clean: %s" % e); print("[FAIL] чистка: %s" % e)

# --- CHECK ---
print("\n=== CHECK ===")
ux = (AG / "users.py").read_text(encoding="utf-8")
ax = (AG / "agent.py").read_text(encoding="utf-8")
print("users fn:", "def admin_delete_user" in ux)
print("op delete:", 'op == "delete"' in ax)
print("btn:", 'data-act="do_del"' in ax)
print("handler:", "a=='do_del'" in ax)
try:
    import users as US2
    print("остались:", [x["login"] for x in US2.list_users()])
except Exception as e:
    print("list err:", e)
print()
if FAILS: print("НЕ ПРИМЕНЕНО: " + "; ".join(FAILS))
else: print("ГОТОВО: .\\AI_RESTART.bat + Ctrl+F5")
if SKIPS: print("ПРОПУЩЕНО: " + "; ".join(SKIPS))