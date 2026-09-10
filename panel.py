# -*- coding: utf-8 -*-
"""
РђР“Р•РќРў v12 вЂ” РџРђРќР•Р›Р¬ (panel.py)
РЎРѕР±РёСЂР°РµС‚ Р±РѕРєРѕРІСѓСЋ РїР°РЅРµР»СЊ: СЃРµРєС†РёРё Р±Р»РѕРєРѕРІ, С‡РёРїС‹-Р·Р°РґР°С‡Рё, РєРЅРѕРїРєРё РґРµР№СЃС‚РІРёР№,
РјРѕРґРµР»Рё РР, РїРѕР»Р·СѓРЅРєРё РїРѕРІРµРґРµРЅРёСЏ. Р§РёРїС‹ вЂ” СЂР°Р±РѕС‡РёРµ Р·Р°РґР°С‡Рё, Р±РµР· РїСЂСѓР¶РёРЅ.
"""
import importlib, json, urllib.request
import core
import tools_registry as TR

TITLES = {
    "creo_ops_tools": "рџ”© CREO-РћРџР•Р РђР¦РР", "creo_tools": "рџ¦ѕ CREO", "fleet_tools": "рџљЊ Р¤Р›РћРў",
    "knowledge_tools": "рџ“љ Р—РќРђРќРРЇ", "memory_tools": "рџ§  РџРђРњРЇРўР¬", "one_c_tools": "рџЏў 1РЎ",
    "passport_tools": "рџ“‹ РџРђРЎРџРћР Рў", "scanner_tools": "рџ”Ќ РЎРљРђРќР•Р ", "settings_tools": "вљ™ РќРђРЎРўР РћР™РљР",
    "trail_tools": "рџ§ѕ РўР Р•Р™Р›Р«", "users_tools": "рџ‘Ґ Р”РћРЎРўРЈРџР«", "vision_tools": "рџ‘Ѓ Р’РР—РРЇ",
    "web_tools": "рџЊђ WEB", "diagnostic_tools": "рџ©є Р”РРђР“РќРћРЎРўРРљРђ", "backup_tools": "рџ’ѕ Р‘Р­РљРђРџР«",
    "calc_tools": "рџ§® РљРђР›Р¬РљРЈР›РЇРўРћР ",
}

CHIPS = [
    "СЃС‚Р°С‚СѓСЃ Creo Рё РѕС‚РєСЂС‹С‚С‹Рµ РјРѕРґРµР»Рё",
    "Р°СѓРґРёС‚ СЂР°Р±РѕС‡РµР№ РїР°РїРєРё РїРѕ СЌС‚Р°Р»РѕРЅСѓ РљР‘",
    "СЂР°Р·Р±РѕСЂ С‚СЂРµР№Р»Р°: РѕС€РёР±РєРё, РїСЂРѕСЃС‚РѕР№, РїР°РјСЏС‚СЊ",
    "РіРґРµ СЃРєР»Р°Рґ РІРµСЂСЃРёР№ Рё С‡С‚Рѕ РїРѕС‡РёСЃС‚РёС‚СЊ",
    "РєС‚Рѕ Рё РєРѕРіРґР° СЂР°Р±РѕС‚Р°Р» РІ Creo",
    "РїР°СЃРїРѕСЂС‚ РєРѕРјРїР°РЅРёРё",
    "СЃС‚СЂР°С‚РµРіРёСЏ РљР‘",
    "СЃРїРёСЃРѕРє Р±СЌРєР°РїРѕРІ Р·Р° РЅРµРґРµР»СЋ",
    "СЃРѕСЃС‚РѕСЏРЅРёРµ Р±Р°Р·С‹ Р·РЅР°РЅРёР№",
    "РґРѕСЃС‚СѓРїРЅС‹Рµ РјРѕРґРµР»Рё РР",
    "С‚РµРєСѓС‰РёРµ РЅР°СЃС‚СЂРѕР№РєРё Р°РіРµРЅС‚Р°",
]

ACTIONS = [
    {"label": "РџРµСЂРµРёРЅРґРµРєСЃРёСЂРѕРІР°С‚СЊ Р±Р°Р·Сѓ", "endpoint": "/rescan"},
    {"label": "РЎРєР°РЅ 3D-РјРѕРґРµР»РµР№", "endpoint": "/scan"},
    {"label": "РџРѕРєР°Р·Р°С‚СЊ Р»РѕРі", "endpoint": "/log"},
]

BEHAVIOR = [
    {"key": "creativity", "name": "РљСЂРµР°С‚РёРІ 0-100", "min": 0, "max": 100, "step": 1},
    {"key": "top_p", "name": "Top-p", "min": 0, "max": 1, "step": 0.05},
    {"key": "num_predict", "name": "РњР°РєСЃ С‚РѕРєРµРЅРѕРІ", "min": 256, "max": 4096, "step": 256},
    {"key": "auto_mode", "name": "РђРІС‚РѕСЂРµР¶РёРј", "min": 0, "max": 1, "step": 1},
    {"key": "think_mode", "name": "Р Р°СЃСЃСѓР¶РґРµРЅРёСЏ 0-2", "min": 0, "max": 2, "step": 1},
]

def models():
    try:
        j = json.load(urllib.request.urlopen(core.OLL + "/api/tags", timeout=5))
        return [m.get("name") for m in j.get("models", [])]
    except Exception:
        return []

def build():
    # РљРѕРЅС„РёРіСѓСЂР°С†РёСЏ РїСЂРѕСЃС‚СЂР°РЅСЃС‚РІ (Title, Group Icon, Prefixes)
    group_configs = [
        ("рџ›  Creo", "рџ› ", ["creo_", "copy_", "usage_"]),
        ("рџ§­ РњРѕРґРµР»Рё", "рџ§­", ["models_", "find_", "index_", "family_"]),
        ("рџ“€ РўСЂРµР№Р»С‹ Рё РґРёР°РіРЅРѕСЃС‚РёРєР°", "рџ“€", ["trail_", "diag_", "predict_"]),
        ("рџ“љ Р‘Р°Р·Р° Р·РЅР°РЅРёР№ Рё РїР°РјСЏС‚СЊ", "рџ“љ", ["search_kb", "read_file", "memory_", "learn_", "save_"]),
        ("рџ§® РРЅР¶РµРЅРµСЂРЅРѕРµ", "рџ§®", ["calc_", "vision_", "plm_", "spec_"]),
        ("рџљЂ Р¤Р»РѕС‚ Рё СЃР»СѓР¶Р±Р°", "рџљЂ", ["fleet_", "backup_", "git_", "nightly_", "sync_"]),
        ("рџ‘Ґ РљРѕРјР°РЅРґР° Рё СЃРїСЂР°РІРєР°", "рџ‘Ґ", ["chat_", "help_", "behavior_", "passport_", "role_", "users_"]),
        ("вљ™ РќР°СЃС‚СЂРѕР№РєРё", "вљ™", ["settings_"]),
    ]

    # РљР°СЂС‚Р° РёРєРѕРЅРѕРє РёРЅСЃС‚СЂСѓРјРµРЅС‚РѕРІ
    icon_map = {
        "creo_status": "рџ–Ґ", "creo_session": "рџЄџ", "creo_get_active": "рџЋЇ",
        "creo_pwd": "рџ“Ѓ", "creo_list_files": "рџ“„", "creo_find_model": "рџ”Ќ",
        "creo_get_params": "рџ“‹", "creo_get_relations": "рџ”—", "creo_get_mass": "вљ–",
        "creo_save": "рџ’ѕ", "copy_model": "рџ“‘", "creo_audit_folder": "рџ§№",
        "usage_build": "рџ§©", "trail_analyze": "рџ“€", "trail_problems": "вљ ",
        "trail_predict": "рџ”®", "calc": "рџ§®", "search_kb": "рџ“љ",
        "read_file": "рџ“–", "vision_analyze": "рџ‘Ѓ", "backup_make": "рџ’ј",
        "git_sync": "вЋ‡", "chat_send": "рџ’¬", "help": "вќ“"
    }

    # РРЅРёС†РёР°Р»РёР·Р°С†РёСЏ С…СЂР°РЅРёР»РёС‰Р° РёРЅСЃС‚СЂСѓРјРµРЅС‚РѕРІ РґР»СЏ РєР°Р¶РґРѕР№ РіСЂСѓРїРїС‹
    groups_data = [[] for _ in range(len(group_configs))]

    # РЎРѕР±РёСЂР°РµРј РІСЃРµ РёРЅСЃС‚СЂСѓРјРµРЅС‚С‹ РёР· РІСЃРµС… Р±Р»РѕРєРѕРІ
    for b in TR.BLOCKS:
        try:
            m = importlib.import_module(b)
            ts = getattr(m, "TOOLS", [])
        except Exception:
            ts = []
        
        for t in ts:
            t_name = t["name"]
            # РС‰РµРј, Рє РєР°РєРѕР№ РіСЂСѓРїРїРµ РѕС‚РЅРѕСЃРёС‚СЃСЏ РёРЅСЃС‚СЂСѓРјРµРЅС‚ РїРѕ РµРіРѕ РёРјРµРЅРё (РїСЂРµС„РёРєСЃСѓ)
            for idx, (_, _, prefixes) in enumerate(group_configs):
                if any(t_name.startswith(p) for p in prefixes):
                    groups_data[idx].append(t)
                    break

    # Р¤РѕСЂРјРёСЂСѓРµРј С„РёРЅР°Р»СЊРЅС‹Р№ СЃРїРёСЃРѕРє РіСЂСѓРїРї
    final_groups = []
    for i, (title_base, group_icon, _) in enumerate(group_configs):
        tools_in_group = groups_data[i]
        count = len(tools_in_group)
        
        # Р—Р°РіРѕР»РѕРІРѕРє СЃ РёРєРѕРЅРєРѕР№ Рё СЃС‡С‘С‚С‡РёРєРѕРј
        display_title = f"{title_base} ({count})"
        
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

