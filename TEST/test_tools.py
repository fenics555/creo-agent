# -*- coding: utf-8 -*-
r"""
АГЕНТ v12 — ЮНИТ-ТЕСТЫ ИНСТРУМЕНТОВ (TEST\test_tools.py)
Запуск:  python D:\AI\tools\agent\TEST\test_tools.py
Критерий: ни один инструмент не бросает исключение и возвращает str.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tools_registry as TR
import agent as AG

G, R, E = "\033[92m", "\033[91m", "\033[0m"
passed = failed = 0

def check(name, fn):
    global passed, failed
    try:
        r = fn()
        if not isinstance(r, str):
            print("%sFAIL %s: вернул не строку (%s)%s" % (R, name, type(r), E))
            failed += 1
            return
        print("%sOK   %s -> %s%s" % (G, name, r[:80].replace("\n", " "), E))
        passed += 1
    except Exception as ex:
        print("%sFAIL %s: ИСКЛЮЧЕНИЕ %s%s" % (R, name, ex, E))
        failed += 1


# ============ РЕЕСТР ============
print("\n=== ТЕСТ РЕЕСТРА ===")
check("реестр: число инструментов >= 25",
      lambda: "ок, %d" % len(TR.TOOLS) if len(TR.TOOLS) >= 25
              else (_ for _ in ()).throw(Exception("мало: %d" % len(TR.TOOLS))))

check("реестр: describe непуст",
      lambda: TR.describe()[:60] or "пусто")

check("реестр: у всех инструментов есть fn и desc",
      lambda: "ок" if all(t.get("fn") and t.get("desc") for t in TR.TOOLS)
              else (_ for _ in ()).throw(Exception("дыра в манифесте")))

check("реестр: у всех инструментов есть params (хотя бы пустой dict)",
      lambda: "ок" if all(isinstance(t.get("params"), dict) for t in TR.TOOLS)
              else (_ for _ in ()).throw(Exception("params не dict у кого-то")))

check("щит: creo_set_param с флагом approval",
      lambda: "ок" if (TR.get("creo_set_param") or {}).get("approval")
              else (_ for _ in ()).throw(Exception("нет флага approval")))

check("щит: creo_set_relations с флагом approval",
      lambda: "ок" if (TR.get("creo_set_relations") or {}).get("approval")
              else (_ for _ in ()).throw(Exception("нет флага approval")))

check("щит: save_skill с флагом approval",
      lambda: "ок" if (TR.get("save_skill") or {}).get("approval")
              else (_ for _ in ()).throw(Exception("нет флага approval")))

check("щит: backup_restore с флагом approval",
      lambda: "ок" if (TR.get("backup_restore") or {}).get("approval")
              else (_ for _ in ()).throw(Exception("нет флага approval")))

check("щит: settings_set с флагом approval",
      lambda: "ок" if (TR.get("settings_set") or {}).get("approval")
              else (_ for _ in ()).throw(Exception("нет флага approval")))

check("execute: неизвестный инструмент возвращает строку ошибки",
      lambda: TR.execute("no_such_tool_xyz_777", {}))


# ============ ПАРСЕР ПРОТОКОЛА ============
print("\n=== ТЕСТ ПАРСЕРА ПРОТОКОЛА ===")
# Используем backup_list — гарантированно живой инструмент (из блока backup_tools)
check("парсер: распознаёт [TOOL: backup_list]",
      lambda: "ок" if AG.parse_model("думаю\n[TOOL: backup_list]\n{}\n[/TOOL]")[0] == "tool"
              else (_ for _ in ()).throw(Exception("не распознал")))

check("парсер: распознаёт [ANSWER]",
      lambda: "ок" if AG.parse_model("[ANSWER]привет, коллега[/ANSWER]")[1] == "привет, коллега"
              else (_ for _ in ()).throw(Exception("не распознал")))

check("парсер: голый текст = answer",
      lambda: "ок" if AG.parse_model("просто текст без тегов")[0] == "answer"
              else (_ for _ in ()).throw(Exception("не распознал")))

check("парсер: фолбэк на строку 'backup_list {}'",
      lambda: "ок" if AG.parse_model('backup_list {}')[0] == "tool"
              else (_ for _ in ()).throw(Exception("фолбэк мёртв")))

check("парсер: извлекает аргументы JSON",
      lambda: "ок" if AG.parse_model('[TOOL: backup_list]\n{"name": "x"}\n[/TOOL]')[2] == {"name": "x"}
              else (_ for _ in ()).throw(Exception("аргументы не извлёк")))


# ============ БЕЗОПАСНЫЕ ВЫЗОВЫ КАЖДОГО ИНСТРУМЕНТА ============
print("\n=== ТЕСТ КАЖДОГО ИНСТРУМЕНТА (безопасные вызовы) ===")
# Все эти инструменты должны вернуть строку (даже «ошибка» или «не найдено»), но НЕ кидать исключение
SAFE_CALLS = {
    "creo_status": {},
    "creo_session": {},
    "creo_find_model": {"mask": "пружина"},
    "creo_get_params": {"model": "несуществующая_модель_xyz_999"},
    "creo_get_relations": {"model": "xyz_999"},
    "creo_get_mass": {"model": "xyz_999"},
    "creo_get_bom": {"model": "xyz_999"},
    "creo_audit_folder": {},
    "creo_read_trail": {"lines": 20},
    "search_kb": {"query": "пружина сжатия"},
    "read_file": {"path": r"D:\AI\repo\net_takogo_faila_xyz.md"},
    "save_skill": {"name": "_test_dummy_do_not_save", "content": "test"},  # approval — НЕ выполнится, вернёт ошибку
    "history_search": {"query": "пружина"},
    "strategy_read": {},
    "proven_show": {},
    "fav_show": {},
    "save_error": {},
    "vision_analyze": {"question": "что на экране"},
    "passport_show": {},
    "passport_build": {},
    "fleet_status": {},
    "fleet_trails": {"machine": "frezer4"},
    "one_c_status": {},
    "settings_show": {},
    "backup_list": {},
}

for name, args in SAFE_CALLS.items():
    check(name, lambda n=name, a=args: TR.execute(n, a))
    # уборка мусора после теста save_skill
import pathlib
_dummy = pathlib.Path(r"D:\AI\repo\SKILL__test_dummy_do_not_save.md")
if _dummy.exists(): _dummy.unlink()


# ============ ИТОГ ============
print("\n=== ИТОГ ===")
print("%sпройдено: %d, провалено: %d%s" % (G if failed == 0 else R, passed, failed, E))
if failed > 0:
    print("%sВНИМАНИЕ: есть провалы. Проверь, что все *_tools.py имеют блок TOOLS в конце.%s" % (R, E))
sys.exit(0 if failed == 0 else 1)