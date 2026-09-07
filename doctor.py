# -*- coding: utf-8 -*-
# DOCTOR v21 — НОВЫЕ ФИЧИ: calc_tools, SKILL_tool_routing, panel.
# ЗАПУСКАТЬ ОДИН РАЗ. После: .\AI_RESTART.bat + Ctrl+F5

from pathlib import Path

AG = Path(r"D:\AI\tools\agent")
REPO = Path(r"D:\AI\repo")
FAILS = []
SKIPS = []

def py_ok(text, name):
    try:
        compile(text, name, "exec")
        return True
    except SyntaxError as e:
        print("[SYNTAX] %s: %s" % (name, e))
        return False

# ============================================================
# N1: Создать calc_tools.py
# ============================================================
CALC = r'''# -*- coding: utf-8 -*-
r"""АГЕНТ — ИНЖЕНЕРНЫЙ КАЛЬКУЛЯТОР с единицами измерения."""
import re, math

UNITS = {
    "мм": ("m", 0.001), "мм2": ("m2", 1e-6), "мм3": ("m3", 1e-9), "мм4": ("m4", 1e-12),
    "см": ("m", 0.01), "см2": ("m2", 1e-4), "см3": ("m3", 1e-6), "см4": ("m4", 1e-8),
    "м": ("m", 1.0), "м2": ("m2", 1.0), "м3": ("m3", 1.0), "м4": ("m4", 1.0),
    "км": ("m", 1000.0), "in": ("m", 0.0254), "inch": ("m", 0.0254), "ft": ("m", 0.3048),
    "г": ("kg", 0.001), "кг": ("kg", 1.0), "т": ("kg", 1000.0),
    "mg": ("kg", 1e-6), "g": ("kg", 0.001), "kg": ("kg", 1.0), "t": ("kg", 1000.0),
    "мс": ("s", 0.001), "с": ("s", 1.0), "мин": ("s", 60.0), "ч": ("s", 3600.0),
    "ms": ("s", 0.001), "s": ("s", 1.0), "min": ("s", 60.0), "h": ("s", 3600.0),
    "Н": ("N", 1.0), "кН": ("N", 1000.0), "кгс": ("N", 9.80665), "MN": ("N", 1e6),
    "Па": ("Pa", 1.0), "кПа": ("Pa", 1000.0), "МПа": ("Pa", 1e6), "ГПа": ("Pa", 1e9),
    "бар": ("Pa", 1e5), "атм": ("Pa", 101325.0),
    "Нм": ("Nm", 1.0), "Н*м": ("Nm", 1.0), "кгсм": ("Nm", 0.0980665), "кгс*м": ("Nm", 9.80665),
    "Вт": ("W", 1.0), "кВт": ("W", 1000.0), "МВт": ("W", 1e6),
}

FORMULAS = {
    "круг_площадь": ("π·d²/4", lambda d: math.pi * d**2 / 4, "d в мм"),
    "круг_момент": ("π·d⁴/64", lambda d: math.pi * d**4 / 64, "d в мм"),
    "круг_W": ("π·d³/32", lambda d: math.pi * d**3 / 32, "d в мм"),
    "цилиндр_объем": ("π·d²·h/4", lambda d, h: math.pi * d**2 * h / 4, "d,h в мм"),
    "напряжение": ("F/A", lambda F, A: F / A if A > 0 else 0, "F в Н, A в мм²"),
}

def tool_calc(expr="", unit="", **kw):
    e = (expr or "").strip()
    if not e:
        return "укажи выражение. Примеры: 'перевести 150 Нм в кгсм', 'круг_площадь 50', 'цилиндр_объем 50 120'"
    m = re.match(r"перевести\s+([\d.]+)\s*([A-Za-zА-Яа-я0-9*_²³]+)\s+в\s+([A-Za-zА-Яа-я0-9*_²³]+)", e, re.I)
    if m:
        val, u_from, u_to = float(m.group(1)), m.group(2), m.group(3)
        if u_from not in UNITS or u_to not in UNITS:
            return "неизвестные единицы. Доступные: " + ", ".join(sorted(UNITS.keys()))
        base_from, k_from = UNITS[u_from]
        base_to, k_to = UNITS[u_to]
        if base_from != base_to:
            return "нельзя перевести %s в %s (разные базы)" % (u_from, u_to)
        return "%.6g %s = %.6g %s" % (val, u_from, val * k_from / k_to, u_to)
    for name, (formula, fn, hint) in FORMULAS.items():
        if e.startswith(name):
            parts = e[len(name):].strip().split()
            try:
                r = fn(*[float(x) for x in parts])
                return "%s(%s) = %.6g  [%s]" % (name, ", ".join(parts), r, formula)
            except Exception as ex:
                return "ошибка: %s. Использование: %s <числа> (%s)" % (ex, name, hint)
    return "не распознано. Примеры: 'перевести 150 Нм в кгсм', 'круг_площадь 50'"

def tool_calc_units(**kw):
    return "Единицы: " + ", ".join(sorted(UNITS.keys()))

def tool_calc_formulas(**kw):
    out = ["Формулы:"]
    for name, (formula, fn, hint) in FORMULAS.items():
        out.append("- %s = %s (%s)" % (name, formula, hint))
    return "\n".join(out)

TOOLS = [
    {"name": "calc", "desc": "Инженерный калькулятор с единицами и формулами", "params": {"expr": "выражение", "unit": "желаемая единица"}, "approval": False, "fn": tool_calc},
    {"name": "calc_units", "desc": "Список единиц калькулятора", "params": {}, "approval": False, "fn": tool_calc_units},
    {"name": "calc_formulas", "desc": "Список формул калькулятора", "params": {}, "approval": False, "fn": tool_calc_formulas},
]
'''
if (AG / "calc_tools.py").exists():
    SKIPS.append("N1")
    print("[SKIP] N1: calc_tools.py уже существует")
else:
    if py_ok(CALC, "calc_tools.py"):
        (AG / "calc_tools.py").write_text(CALC, encoding="utf-8")
        print("[OK] N1: calc_tools.py создан")
    else:
        FAILS.append("N1")

# ============================================================
# N2: Создать SKILL_tool_routing.md
# ============================================================
ROUTING = r'''---
name: tool_routing
description: Маршрутизация запросов пользователя к инструментам агента. Правила выбора, антипримеры, разграничение похожих инструментов.
when: Всегда перед выбором инструмента. При любом запросе пользователя.
priority: critical
---

# МАРШРУТИЗАЦИЯ ИНСТРУМЕНТОВ

## Принцип выбора

1. Сначала пойми намерение пользователя, потом выбирай инструмент.
2. Нормализуй запрос в короткую рабочую команду.
3. Если данных не хватает — уточни, не гадай.
4. Если инструментов подходит несколько — выбери самый безопасный (чтение вместо записи).
5. После результата проверь: отвечает ли он исходному намерению.

## Карта инструментов по намерениям

### Активная модель и сессия
| Намерение | Инструмент |
|---|---|
| Какая модель открыта сейчас | creo_get_active |
| Что открыто в сессии | creo_session |
| Работает ли Creo | creo_status |
| Рабочая папка Creo | creo_pwd |
| Файлы в рабочей папке | creo_list_files |

### Поиск моделей
| Намерение | Инструмент |
|---|---|
| Найди модель по имени в базе | models_find |
| Найди модель в индексе | creo_find_model |
| Статистика базы моделей | models_stats |
| Прочитать содержимое файла | read_file |

### Использование моделей (где применяется)
| Намерение | Инструмент |
|---|---|
| В каких сборках используется деталь | models_where |
| Статус индекса использования | usage_state |
| Построить индекс использования | usage_build |

### Параметры и свойства модели
| Намерение | Инструмент |
|---|---|
| Все параметры модели | creo_get_params |
| Масса / объём / площадь | creo_get_mass |
| Отношения модели | creo_get_relations |
| Дерево компонентов сборки | creo_get_bom |
| Ошибки открытия модели | creo_open_errors |

### Трейлы и диагностика
| Намерение | Инструмент |
|---|---|
| Накопленные проблемы из трейлов | trail_problems |
| Прогноз проблем | trail_predict |
| Разбор конкретного трейла | trail_analyze |
| Диагноз с мнением ИИ | trail_diagnose |

### База знаний и файлы
| Намерение | Инструмент |
|---|---|
| Поиск по смыслу в базе знаний | search_kb |
| Прочитать конкретный файл | read_file |
| Сохранить новый скилл | save_skill |

### Настройки и модели
| Намерение | Инструмент |
|---|---|
| Показать все настройки | settings_show |
| Изменить настройку | settings_set |
| Список моделей Ollama | settings_models |

### Справка
| Намерение | Инструмент |
|---|---|
| Общая справка по агенту | guide |
| Подробное описание блока | tools_help |

## Антипримеры выбора инструментов

| Запрос пользователя | НЕ делать | Делать |
|---|---|---|
| «посмотри деталь» без имени | models_find наугад | creo_get_active или уточнить |
| «где используется деталь» | models_find | models_where |
| «найди файл» | models_find | creo_list_files или read_file |
| «что в файле» | search_kb | read_file |
| «что в папке» | models_find | creo_list_files |
| «какая модель открыта» | models_find | creo_get_active |
| «проверь настройки» | creo_status | settings_show |
| «помощь» | search_kb | guide |
| «проблемы трейлов» | trail_analyze | trail_problems |
| «индекс использования» | models_where | usage_state |

## Нормализация запроса

| Живая фраза | Нормализация |
|---|---|
| «глянь деталь» | проверить объект |
| «что там с ней» | проверить состояние |
| «где эта штука» | найти использование |
| «почему тормозит» | диагностика |
| «посмотри что изменилось» | проверить изменения |
| «разберись с проектом» | диагностика проекта |

## Уточнение при нехватке данных

Если критических данных нет, уточни одним вопросом. Не гадай.

- «посмотри деталь» → «Какую деталь: активную в Creo или по имени?»
- «проверь файл» → «Какой файл? Укажи путь.»

## Многозадачные запросы

Если запрос содержит несколько действий:
1. Разбей на этапы в [THINK].
2. Выполни один этап за ход.
3. После результата проверь: нужен ли следующий этап.

Пример: «найди корпус_А, проверь где используется и посмотри параметры»
→ Этапы: 1) models_find, 2) models_where, 3) creo_get_params, 4) итог.
'''
if (REPO / "SKILL_tool_routing.md").exists():
    SKIPS.append("N2")
    print("[SKIP] N2: SKILL_tool_routing.md уже существует")
else:
    (REPO / "SKILL_tool_routing.md").write_text(ROUTING, encoding="utf-8")
    print("[OK] N2: SKILL_tool_routing.md создан")

# ============================================================
# N3: Обновить SKILL_index.md
# ============================================================
idx = REPO / "SKILL_index.md"
if idx.exists():
    t = idx.read_text(encoding="utf-8")
    if "SKILL_tool_routing" in t:
        SKIPS.append("N3")
        print("[SKIP] N3: уже в index")
    else:
        anchor = "| SKILL_agent_protocol | протокол инженера-напарника (critical) |"
        if anchor in t:
            new = t.replace(anchor, "| SKILL_tool_routing | маршрутизация запросов к инструментам (critical) |\n" + anchor, 1)
            idx.write_text(new, encoding="utf-8")
            print("[OK] N3: SKILL_index обновлён")
        else:
            FAILS.append("N3")
            print("[FAIL] N3: якорь не найден")
else:
    FAILS.append("N3")
    print("[FAIL] N3: SKILL_index.md не найден")

# ============================================================
# N4: panel.py — think_mode в BEHAVIOR
# ============================================================
p = (AG / "panel.py").read_text(encoding="utf-8")
if '"think_mode"' in p:
    SKIPS.append("N4")
    print("[SKIP] N4: think_mode уже в panel")
else:
    anchor = '{"key": "auto_mode", "name": "Авторежим", "min": 0, "max": 1, "step": 1}'
    if anchor in p:
        new = p.replace(anchor, anchor + ',\n    {"key": "think_mode", "name": "Рассуждения 0-2", "min": 0, "max": 2, "step": 1}', 1)
        if py_ok(new, "panel.py"):
            (AG / "panel.py").write_text(new, encoding="utf-8")
            print("[OK] N4: think_mode добавлен в panel")
        else:
            FAILS.append("N4")
    else:
        FAILS.append("N4")
        print("[FAIL] N4: якорь не найден")

# ============================================================
# N5: panel.py — calc в TITLES
# ============================================================
p = (AG / "panel.py").read_text(encoding="utf-8")
if '"calc_tools"' in p:
    SKIPS.append("N5")
    print("[SKIP] N5: calc_tools уже в TITLES")
else:
    anchor = '"backup_tools": "💾 БЭКАПЫ"'
    if anchor in p:
        new = p.replace(anchor, anchor + ',\n    "calc_tools": "🧮 КАЛЬКУЛЯТОР"', 1)
        if py_ok(new, "panel.py"):
            (AG / "panel.py").write_text(new, encoding="utf-8")
            print("[OK] N5: calc_tools добавлен в TITLES")
        else:
            FAILS.append("N5")
    else:
        FAILS.append("N5")
        print("[FAIL] N5: якорь не найден")

# ============================================================
print("\n=== CHECK ===")
print("N1 calc_tools.py:", (AG / "calc_tools.py").exists())
print("N2 SKILL_tool_routing.md:", (REPO / "SKILL_tool_routing.md").exists())
if idx.exists():
    print("N3 SKILL_index:", "SKILL_tool_routing" in idx.read_text(encoding="utf-8"))
px = (AG / "panel.py").read_text(encoding="utf-8")
print("N4 think_mode panel:", '"think_mode"' in px)
print("N5 calc TITLES:", '"calc_tools"' in px)
print()
if FAILS: print("НЕ ПРИМЕНЕНО: " + "; ".join(FAILS))
else: print("ГОТОВО: .\\AI_RESTART.bat + Ctrl+F5")
if SKIPS: print("ПРОПУЩЕНО: " + "; ".join(SKIPS))