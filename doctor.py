# -*- coding: utf-8 -*-
"""Полная диагностика и исправление критических ошибок."""
import os, sys, subprocess
from pathlib import Path

AG = Path(r"D:\AI\tools\agent")
print("=" * 80)
print("ПОЛНАЯ ДИАГНОСТИКА CREO-AGENT v14")
print("=" * 80)

# 1) Проверка критических файлов
print("\n[1/6] Проверка критических файлов...")
critical = {
    "agent.py": AG / "agent.py",
    "scanner.py": AG / "scanner.py",
    "core.py": AG / "core.py",
    "settings.py": AG / "settings.py",
    "tools_registry.py": AG / "tools_registry.py",
}
for name, path in critical.items():
    if path.exists():
        size = path.stat().st_size
        print(f"  ✓ {name}: {size // 1024} КБ")
    else:
        print(f"  ✗ {name}: НЕ НАЙДЕН")

# 2) Проверка scanner.py на наличие read_roots
print("\n[2/6] Анализ scanner.py...")
scanner = (AG / "scanner.py").read_text(encoding="utf-8")
if "def read_roots()" not in scanner:
    print("  ✗ scanner.py: отсутствует read_roots()")
    print("  → Исправляю: добавляю read_roots() и _pats()...")
    
    add_code = '''
def read_roots():
    """Список корней для скана из kb_roots.txt или scan_roots из settings."""
    try:
        from pathlib import Path
        import settings
        r = Path(__file__).parent / "kb_roots.txt"
        if r.exists():
            lines = r.read_text(encoding="utf-8").splitlines()
            return [l.strip() for l in lines if l.strip() and not l.strip().startswith("#")]
        raw = settings.get("scan_roots") or []
        return raw if isinstance(raw, list) else [raw]
    except Exception:
        return []

def _pats():
    """Паттерны исключения из kb_exclude.txt."""
    try:
        from pathlib import Path
        p = Path(__file__).parent / "kb_exclude.txt"
        if p.exists():
            return [l.strip() for l in p.read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith("#")]
        return []
    except Exception:
        return []

def is_excluded(path, pats):
    """Проверка исключения по паттернам."""
    p = path.lower()
    return any(pat.lower() in p for pat in (pats or []))
'''
    
    # Вставляем после import'ов
    lines = scanner.split('\n')
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith('import') or line.startswith('from'):
            insert_at = i + 1
    
    scanner = '\n'.join(lines[:insert_at]) + '\n' + add_code + '\n' + '\n'.join(lines[insert_at:])
    (AG / "scanner.py").write_text(scanner, encoding="utf-8")
    print("  ✓ scanner.py: исправлен")
else:
    print("  ✓ scanner.py: read_roots() есть")

# 3) Проверка kb_roots.txt
print("\n[3/6] Проверка конфигурации сканирования...")
kr = AG / "kb_roots.txt"
if not kr.exists():
    print("  ✗ kb_roots.txt не найден, создаю...")
    kr.write_text("""# Корни для скана моделей и индексации
D:\\PTC\\CREO12\\Creo 12.4.2.0\\creo_help_pma\\russian
D:\\AI\\repo
Z:\\PTC\\Work
Z:\\PTC\\CREO-START
""", encoding="utf-8")
    print("  ✓ kb_roots.txt создан")
else:
    roots = kr.read_text(encoding="utf-8").splitlines()
    roots = [r for r in roots if r.strip() and not r.strip().startswith("#")]
    print(f"  ✓ kb_roots.txt: {len(roots)} корней")
    for r in roots:
        exists = "ЕСТЬ" if os.path.exists(r) else "НЕТ"
        print(f"    {r} -> {exists}")

# 4) Проверка kb_exclude.txt
ke = AG / "kb_exclude.txt"
if not ke.exists():
    print("  ✗ kb_exclude.txt не найден, создаю...")
    ke.write_text("""# Паттерны исключения (в нижнем регистре)
__pycache__
.git
node_modules
backup
""", encoding="utf-8")
    print("  ✓ kb_exclude.txt создан")
else:
    print("  ✓ kb_exclude.txt есть")

# 5) Тестирование scanner.py
print("\n[4/6] Тестирование scanner.py...")
sys.path.insert(0, str(AG))
try:
    import scanner
    print("  ✓ scanner импортирован успешно")
    
    # Проверяем функции
    funcs = ["read_roots", "_pats", "is_excluded", "scan_models", "index_all", "state"]
    for fn in funcs:
        if hasattr(scanner, fn):
            print(f"    ✓ {fn}()")
        else:
            print(f"    ✗ {fn}() отсутствует")
    
    # Проверяем состояние
    st = scanner.state()
    print(f"  Состояние: models={st.get('models', '?')}, chunks={st.get('chunks', '?')}, files={st.get('files', '?')}")
    
except Exception as e:
    print(f"  ✗ Ошибка импорта scanner: {e}")
    import traceback
    traceback.print_exc()

# 6) Проверка базы данных
print("\n[5/6] Проверка базы данных...")
import sqlite3
dbf = AG / "data" / "agent.sqlite"
if dbf.exists():
    try:
        c = sqlite3.connect(str(dbf))
        tables = c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        print(f"  Таблиц: {len(tables)}")
        for t in ["models", "chunks", "files", "usage", "history"]:
            try:
                cnt = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                print(f"    {t}: {cnt} записей")
            except:
                print(f"    {t}: таблица не существует")
        c.close()
    except Exception as e:
        print(f"  ✗ Ошибка БД: {e}")
else:
    print("  ✗ agent.sqlite не найден")

# 7) Рекомендации
print("\n[6/6] Рекомендации...")
print("  1. Перезапустить агента: .\\AI_RESTART.bat")
print("  2. Запустить скан моделей: в панели 'Скан 3D-моделей' или 'scan_run'")
print("  3. Запустить индексацию: в панели 'Переиндексировать базу' или 'index_run'")
print("  4. Проверить результат: 'index_state' и 'models_stats'")
print()
print("=" * 80)
print("ГОТОВО. Следуйте рекомендациям выше.")
print("=" * 80)