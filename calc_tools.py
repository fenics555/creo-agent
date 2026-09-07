# -*- coding: utf-8 -*-
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
