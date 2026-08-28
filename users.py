# -*- coding: utf-8 -*-
r"""АГЕНТ v12 — users.py: профили, пароли, роли."""
import json, secrets, hashlib, time
from pathlib import Path
from core import log

UFILE = Path(r"D:\AI\tools\agent\data\users.json")
TOKENS = {}
ROLES = ["Инженер", "CREO-Программист", "Программист", "Технолог", "Оператор 1С", "Руководитель", "Администратор"]

def _load():
    if not UFILE.exists():
        UFILE.parent.mkdir(parents=True, exist_ok=True)
        UFILE.write_text(json.dumps({"users": []}, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        d = json.loads(UFILE.read_text(encoding="utf-8"))
    except Exception:
        d = None
    if not isinstance(d, dict) or not isinstance(d.get("users"), list):
        d = {"users": []}
    return d

def _save(d): UFILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

def _hash(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", (pw or "").encode("utf-8"), salt.encode("utf-8"), 120000).hex()

def _find(d, login):
    for u in d["users"]:
        if u.get("login") == login: return u
    return None

def add_user(login, pw, role="Инженер"):
    login = (login or "").strip()
    if not login: return False
    d = _load()
    if _find(d, login): return False
    salt = secrets.token_hex(8)
    d["users"].append({"login": login, "salt": salt, "hash": _hash(pw, salt),
                       "display_name": login, "role": role,
                       "created": time.strftime("%Y-%m-%d %H:%M"), "last_seen": ""})
    _save(d); log("user add: %s role=%s" % (login, role))
    return True

def check_login(login, pw):
    d = _load(); u = _find(d, login)
    if not u or _hash(pw, u.get("salt", "")) != u.get("hash"): return None
    u["last_seen"] = time.strftime("%Y-%m-%dT%H:%M")
    token = secrets.token_urlsafe(24)
    TOKENS[token] = {"login": login, "ts": time.time()}
    _save(d)
    return {"ok": True, "token": token, "login": login,
            "display_name": u.get("display_name", login), "role": u.get("role", "Инженер")}

def token_info(token): return TOKENS.get(token)

def list_users():
    return [{"login": u["login"], "display_name": u.get("display_name", u["login"]),
             "role": u.get("role", "Инженер"), "created": u.get("created", ""),
             "last_seen": u.get("last_seen", "")} for u in _load()["users"]]

def get_profile(login):
    u = _find(_load(), login)
    if not u: return None
    return {"login": u["login"], "display_name": u.get("display_name", u["login"]), "role": u.get("role", "Инженер")}

def update_display_name(login, new_name):
    new_name = (new_name or "").strip()
    if not new_name or len(new_name) > 40: return False, "имя пустое или слишком длинное"
    d = _load(); u = _find(d, login)
    if not u: return False, "пользователь не найден"
    u["display_name"] = new_name; _save(d); log("user rename: %s -> %s" % (login, new_name))
    return True, new_name

def change_password(login, old_pw, new_pw):
    if len(new_pw or "") < 4: return False, "пароль слишком короткий"
    d = _load(); u = _find(d, login)
    if not u: return False, "пользователь не найден"
    if _hash(old_pw, u.get("salt", "")) != u.get("hash"): return False, "неверный старый пароль"
    u["salt"] = secrets.token_hex(8); u["hash"] = _hash(new_pw, u["salt"])
    _save(d); log("user password change: %s" % login)
    return True, "пароль изменён"

def admin_set_role(login, role):
    if role not in ROLES: return False, "неизвестная роль"
    d = _load(); u = _find(d, login)
    if not u: return False, "пользователь не найден"
    u["role"] = role; _save(d); log("user role: %s -> %s" % (login, role))
    return True, role

def admin_reset_password(login, new_pw):
    if len(new_pw or "") < 4: return False, "пароль слишком короткий"
    d = _load(); u = _find(d, login)
    if not u: return False, "пользователь не найден"
    u["salt"] = secrets.token_hex(8); u["hash"] = _hash(new_pw, u["salt"])
    _save(d); log("admin password reset: %s" % login)
    return True, "пароль сброшен"

def is_admin(login):
    u = _find(_load(), login)
    return bool(u) and u.get("role") == "Администратор"

def can_manage_users(login):
    u = _find(_load(), login)
    return bool(u) and u.get("role") in ("Администратор", "Руководитель")

if not _find(_load(), "admin"):
    add_user("admin", "admin", role="Администратор")
