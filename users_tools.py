# -*- coding: utf-8 -*-
r"""АГЕНТ v12 — БЛОК ПОЛЬЗОВАТЕЛЕЙ (users_tools.py). Направление: доступы."""
import users as US

def tool_add(login="", pw="", role="user", **kw):
    return "пользователь создан" if US.add_user(login, pw, role) else "ошибка: логин пустой или уже есть"

def tool_list(**kw):
    us = US.list_users()
    return "\n".join("• %s — роль: %s — был: %s" % (u["login"], u["role"], str(u["last_seen"])[:16]) for u in us) or "пусто"

def tool_role(login="", role="user", **kw):
    return "роль %s → %s" % (login, role) if US.set_role(login, role) else "логин %s не найден" % login

TOOLS = [
    {"name": "user_add", "desc": "Создать пользователя системы", "params": {"login": "логин", "pw": "пароль", "role": "роль"}, "approval": True, "fn": tool_add},
    {"name": "users_list", "desc": "Список пользователей системы (логин + роль + последний вход)", "params": {}, "approval": False, "fn": tool_list},
    {"name": "user_role", "desc": "Сменить роль пользователя (user/admin)", "params": {"login": "логин", "role": "user или admin"}, "approval": True, "fn": tool_role},
]