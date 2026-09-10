# -*- coding: utf-8 -*-
"""
АГЕНТ v12 — ПАНЕЛЬ (panel.py)
Собирает боковую панель: секции блоков, чипы-задачи, кнопки действий,
модели ИИ, ползунки поведения. Чипы — рабочие задачи, без пружин.
"""
import importlib, json, urllib.request
import core
import tools_registry as TR

TITLES = {
    "creo_ops_tools": "🛠 Creo: сессия и операции",
    "creo_tools": "🛠 Creo: сессия и операции",
    "fleet_tools": "🚀 Флот и служба",
    "knowledge_tools": "📚 База знаний и память",
    "memory_tools": "📚 База знаний и память",
    "one_c_tools": "🚀 Флот и служба",
    "passport_tools": "👥 Команда и справка",
    "scanner_tools": "🧭 Модели",
    "settings_tools": "⚙ Настройки",
    "trail_tools": "📈 Трейлы и диагностика",
    "users_tools": "👥 Команда и справка",
    "vision_tools": "🧮 Инженерное",
    "web_tools": "🚀 Флот и служба",
    "diagnostic_tools": "📈 Трейлы и диагностика",
    "backup_tools": "🚀 Флот и служба",
    "calc_tools": "🧮 Инженерное",
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
    {"key": "think_mode", "name": "Рассуждения 0-2", "min": 0, "max": 2, "step": 1},
]

def models():
    try:
        j = json.load(urllib.request.urlopen(core.OLL + "/api/tags", timeout=5))
        return [m.get("name") for m in j.get("models", [])]
    except Exception:
        return []

def build():
    # Конфигурация пространств (Title, Group Icon, Prefixes)
    group_configs = [
        ("🛠 Creo: сессия и операции", "🛠", ["creo_", "copy_", "usage_", "creoson_"]),
        ("🧭 Модели", "🧭", ["models_", "find_", "index_", "family_", "scan_"]),
        ("📈 Трейлы и диагностика", "📈", ["trail_", "diag_", "predict_", "probe_"]),
        ("📚 База знаний и память", "📚", ["search_kb", "read_file", "memory_", "learn_", "save_"]),
        ("🧮 Инженерное", "🧮", ["calc_", "vision_", "plm_", "spec_"]),
        ("🚀 Флот и служба", "🚀", ["fleet_", "backup_", "git_", "nightly_", "sync_", "web_", "one_c_", "case_"]),
        ("👥 Команда и справка", "👥", ["chat_", "help_", "behavior_", "passport_", "role_", "users_"]),
        ("⚙ Настройки", "⚙", ["settings_"]),
    ]
    # Карта иконок инструментов
    icon_map = {
        "creo_status": "🖥", "creo_session": "🪟", "creo_get_active": "🎯",
        "creo_pwd": "📁", "creo_list_files": "📄", "creo_find_model": "🔍",
        "creo_get_params": "📋", "creo_get_relations": "🔗", "creo_get_mass": "⚖",
        "creo_save": "💾", "copy_model": "📑", "creo_audit_folder": "🧹",
        "usage_build": "🧩", "trail_analyze": "📈", "trail_problems": "⚠",
        "trail_predict": "🔮", "calc": "🧮", "search_kb": "📚",
        "read_file": "📖", "vision_analyze": "👁", "backup_make": "💼",
        "git_sync": "⎇", "chat_send": "💬", "help": "❓"
    }

    # РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ С…СЂР°РЅРёР»РёС‰Р° РёРЅСЃС‚СЂСѓРјРµРЅС‚РѕРІ РґР»СЏ РєР°Р¶РґРѕР№ РіСЂСѓРїРїС‹
    groups_data = [[] for _ in range(len(group_configs))]

    # Собираем все инструменты из всех блоков
    for b in TR.BLOCKS:
        try:
            m = importlib.import_module(b)
            ts = getattr(m, "TOOLS", [])
        except Exception:
            ts = []
        
        for t in ts:
            t_name = t["name"]
            matched = False
            # РС‰РµРј, Рє РєР°РєРѕР№ РіСЂСѓРїРїРµ РѕС‚РЅРѕСЃРёС‚СЃСЏ РёРЅСЃС‚СЂСѓРјРµРЅС‚ РїРѕ РµРіРѕ РёРјРµРЅРё (РїСЂРµС„РёРєСЃСѓ)
            for idx, (_, _, prefixes) in enumerate(group_configs):
                if any(t_name.startswith(p) for p in prefixes):
                    groups_data[idx].append(t)
                    matched = True
                    break
            
            if not matched:
                # Fallback: 🚀 Флот и служба (индекс 5)
                groups_data[5].append(t)

    # Формируем финальный список групп
    final_groups = []
    for i, (title_base, group_icon, _) in enumerate(group_configs):
        tools_in_group = groups_data[i]
        count = len(tools_in_group)
        
        # Заголовок с иконкой и счётчиком
        display_title = title_base
        
        group_tools = []
        for t in tools_in_group:
            t_name = t["name"]
            # РРєРѕРЅРєР° РёРЅСЃС‚СЂСѓРјРµРЅС‚Р° (РёР· РєР°СЂС‚С‹ РёР»Рё РёРєРѕРЅРєР° РїСЂРѕСЃС‚СЂР°РЅСЃС‚РІР°)
            t_icon = icon_map.get(t_name, group_icon)
            
            group_tools.append({
                "name": t_name,
                "desc": t["desc"],
                "approval": bool(t.get("approval")),
                "icon": t_icon
            })
        
        final_groups.append({
            "title": display_title,
            "tools": group_tools
        })

    return {
        "groups": final_groups,
        "chips": CHIPS,
        "actions": ACTIONS,
        "behavior": BEHAVIOR,
        "models": models()
    }

