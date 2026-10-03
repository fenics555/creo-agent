# -*- coding: utf-8 -*-
"""creo_boot.py — единая точка входа «найти Creo и подготовить пути» (волна 2).

ЗАЧЕМ: программы класса Р импортировали `creo_path` напрямую, и перенос падал с
`ModuleNotFoundError` (найдено приёмкой волны 1). Теперь программа зовёт `creo_boot`,
а ТОТ решает, где искать модуль: рядом с собой, в папке агента или в PYTHONPATH.
Ничего не дублирует: все пути по-прежнему даёт `creo_path`.

ИСПОЛЬЗОВАНИЕ (config_audit):
    import creo_boot as BOOT
    cfg = BOOT.config_path()          # путь к config.pro (или None)
    paths = BOOT.config_paths()       # известные места
    ok = BOOT.available()             # Creo найден или нет
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
# порядок поиска: рядом с программой → папка агента → уже в sys.modules
for _p in (HERE, HERE.parent):
    if str(_p) not in sys.path and _p.exists():
        sys.path.insert(0, str(_p))

try:
    import creo_path  # noqa: E402
except ImportError as e:          # программа остаётся живой, но честно говорит
    creo_path = None
    IMPORT_ERR = str(e)
else:
    IMPORT_ERR = None


def available():
    """Creo найден через единый поиск дома?"""
    if creo_path is None:
        return False
    try:
        return bool(creo_path.find())
    except Exception:
        return False


def find():
    """(common_files, parametric, откуда) — прокси к единому поиску дома."""
    if creo_path is None:
        return None, None, "модуль creo_path не найден (%s)" % IMPORT_ERR
    try:
        return creo_path.find()
    except Exception as e:
        return None, None, "сбой поиска Creo: %s" % e


def config_path(prefer=None):
    """Путь к config.pro для проверки: prefer → найденный движком → первый известный."""
    if creo_path is None:
        return None
    try:
        return creo_path.find_config(prefer)[0]
    except Exception:
        return None


def config_paths():
    """Известные места config.pro (пустые и мёртвые отсеяны самим поиском)."""
    if creo_path is None:
        return []
    try:
        return list(creo_path.config_paths() or [])
    except Exception:
        return []


def deps_for(prog_dir):
    """Какие модули агента надо положить рядом с программой при переносе.

    Читает контракт программы (`tool.json`) и возвращает существующие файлы."""
    import tool_contract as TC
    out = []
    for dep in TC.deps_of(prog_dir):
        src = HERE / ("%s.py" % dep)
        out.append((dep, str(src) if src.exists() else "НЕТ ФАЙЛА %s" % src))
    return out


def status():
    """Строка состояния для журнала окна и для приёмки."""
    if creo_path is None:
        return "creo_boot: модуль creo_path НЕ НАЙДЕН (%s)" % IMPORT_ERR
    return "creo_boot: пути %d, config.pro=%s, Creo=%s" % (
        len(config_paths()), config_path(), "найден" if available() else "не найден")


if __name__ == "__main__":
    print(status())
    for d, p in deps_for(HERE / "config_audit"):
        print("  dep %-12s %s" % (d, p))