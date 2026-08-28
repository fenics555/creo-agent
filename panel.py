# -*- coding: utf-8 -*-
r"""
АГЕНТ v12 — ПАНЕЛЬ (panel.py)
Собирает боковую панель: секции блоков, чипы-задачи, кнопки действий,
модели ИИ, ползунки поведения. Чипы — рабочие задачи, без пружин.
"""
import importlib, json, urllib.request
import core
import tools_registry as TR

TITLES = {
    "creo_ops_tools": "🔩 CREO-ОПЕРАЦИИ", "creo_tools": "🦾 CREO", "fleet_tools": "🚌 ФЛОТ",
    "knowledge_tools": "📚 ЗНАНИЯ", "memory_tools": "🧠 ПАМЯТЬ", "one_c_tools": "🏢 1С",
    "passport_tools": "📋 ПАСПОРТ", "scanner_tools": "🔍 СКАНЕР", "settings_tools": "⚙ НАСТРОЙКИ",
    "trail_tools": "🧾 ТРЕЙЛЫ", "users_tools": "👥 ДОСТУПЫ", "vision_tools": "👁 ВИЗИЯ",
    "web_tools": "🌐 WEB", "diagnostic_tools": "🩺 ДИАГНОСТИКА", "backup_tools": "💾 БЭКАПЫ",
}
CHIPS = [
    "статус Creo и открытые модели",
    "аудит рабочей папки по эталону КБ",
    "разбор трейла: ошибки, простой, память",
    "где склад версий и что почистить",
    "кто и когда работал в Creo",
    "паспорт компании",
    "стратегия КБ",
    "список бэкапов за неделю",
    "состояние базы знаний",
    "доступные модели ИИ",
    "текущие настройки агента",
]
ACTIONS = [
    {"label": "Переиндексировать базу", "endpoint": "/rescan"},
    {"label": "Скан 3D-моделей", "endpoint": "/scan"},
    {"label": "Показать лог", "endpoint": "/log"},
]
BEHAVIOR = [
    {"key": "creativity", "name": "Креатив 0-100", "min": 0, "max": 100, "step": 1},
    {"key": "top_p", "name": "Top-p", "min": 0, "max": 1, "step": 0.05},
    {"key": "num_predict", "name": "Макс токенов", "min": 256, "max": 4096, "step": 256},
    {"key": "auto_mode", "name": "Авторежим", "min": 0, "max": 1, "step": 1},
]

def models():
    try:
        j = json.load(urllib.request.urlopen(core.OLL + "/api/tags", timeout=5))
        return [m.get("name") for m in j.get("models", [])]
    except Exception:
        return []

def build():
    groups = []
    for b in TR.BLOCKS:
        try:
            m = importlib.import_module(b)
            ts = getattr(m, "TOOLS", [])
        except Exception:
            ts = []
        groups.append({
            "block": b,
            "title": TITLES.get(b, "🧩 " + b.replace("_tools", "").upper()),
            "tools": [{"name": t["name"], "desc": t["desc"], "approval": bool(t.get("approval"))} for t in ts],
        })
    return {"groups": groups, "chips": CHIPS, "actions": ACTIONS,
            "behavior": BEHAVIOR, "models": models()}