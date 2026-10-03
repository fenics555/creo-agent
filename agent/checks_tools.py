# -*- coding: utf-8 -*-
"""checks_tools.py — инструменты агента: единый прогон проверок (волна 5, блок *tools).

ПРАВИЛО (из грабли волны 3): модуль блока НЕ переназначает sys.stdout — проба может
его импортировать, и вторая обёртка TextIOWrapper закроет первый поток.
"""
import sys
from pathlib import Path

AGENT = Path(__file__).resolve().parent
if str(AGENT) not in sys.path:
    sys.path.insert(0, str(AGENT))

import checks as CH  # noqa: E402


def tool_checks_list(**kw):
    """Какие проверки есть у дома (паспорт каждой: область, важность)."""
    return CH.registry()


def tool_checks_run(scope="", only="", **kw):
    """ПРОГОН ПРОВЕРОК ДОМА — один отчёт со сводкой и процентом соответствия.

    scope — область (пусто = все: hole_charts/creo/rules/house), only — id через запятую.
    Каждая старая проверка продолжает работать и по-своему; этот прогон их собирает."""
    return CH.checks_run(scope, only)


def tool_checks_report(**kw):
    """Последние отчёты единого прогона."""
    files = sorted(CH.REPORT_DIR.glob("REPORT_checks_run_*.md"))[-10:]
    return "\n".join(str(f) for f in files) or ("отчётов пока нет: %s" % CH.REPORT_DIR)


TOOLS = [
    {"name": "checks_list", "desc": "Список проверок дома: паспорт каждой (область, важность)",
     "params": {}, "fn": tool_checks_list, "kind": "read", "group": "справочник",
     "source": "checks_tools"},
    {"name": "checks_run", "desc": "Прогнать проверки дома: один отчёт, сводка и процент соответствия",
     "params": {"scope": "область или пусто", "only": "id проверок через запятую"},
     "fn": tool_checks_run, "kind": "check", "group": "диагностика", "source": "checks_tools"},
    {"name": "checks_report", "desc": "Последние отчёты единого прогона проверок",
     "params": {}, "fn": tool_checks_report, "kind": "read", "group": "справочник",
     "source": "checks_tools"},
]