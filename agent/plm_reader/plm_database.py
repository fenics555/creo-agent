# -*- coding: utf-8 -*-
r"""
plm_database.py — DATABASE: обслуживание базы ПЛМ (владелец схемы).

РОЛЬ (архитектура §0.0):
    Сканер   → ЧИТАЕТ файлы → ЧЕРНОВИК (структура)
    Database → ПРОВЕРЯЕТ черновик → ПУБЛИКУЕТ в боевую базу (атомарно)

ЗАКОНЫ:
    • Прямая запись в боевую ЗАПРЕЩЕНА (только через публикацию!)
    • Схему меняет ТОЛЬКО Database
    • Публикация — через `engine._publish()` (бэкап + versioned + подмена)

КОМАНДЫ:
    python plm_database.py stats                 — статистика боевой базы
    python plm_database.py check                 — проверка целостности
    python plm_database.py validate <draft.db>   — проверка черновика
    python plm_database.py publish <draft.db>    — публикация в боевую
    python plm_database.py indexes               — REINDEX + ANALYZE
    python plm_database.py vacuum                — сжать базу
    python plm_database.py backup                — бэкап боевой базы
"""
import os
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def validate(draft):
    """
    Проверить черновик сканера ПЕРЕД публикацией.

    Возвращает dict: {ok, errors[], warnings[], stats{}}
    """
    res = {"ok": True, "errors": [], "warnings": [], "stats": {}}
    if not os.path.isfile(draft):
        res["ok"] = False
        res["errors"].append("черновик не найден: %s" % draft)
        return res
    con = sqlite3.connect(draft)
    cur = con.cursor()
    tabs = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
    for t in tabs:
        res["stats"][t] = cur.execute("SELECT COUNT(*) FROM [%s]" % t).fetchone()[0]
    # ПРОВЕРКИ (ошибки = блокируют публикацию)
    if res["stats"].get("items", 0) == 0:
        res["errors"].append("items = 0 (ни одного изделия!)")
    if res["stats"].get("bodies", 0) == 0:
        res["warnings"].append("bodies = 0 (нет тел — возможно, все заготовки)")
    try:
        empty = cur.execute("SELECT COUNT(*) FROM items WHERE model IS NULL OR model=''").fetchone()[0]
        if empty:
            res["errors"].append("items с пустым model: %d" % empty)
    except sqlite3.Error:
        pass
    con.close()
    res["ok"] = not res["errors"]
    return res


def publish(draft, force=False):
    """Опубликовать черновик в боевую базу (с валидацией)."""
    v = validate(draft)
    print("=== ВАЛИДАЦИЯ ЧЕРНОВИКА ===")
    for t, n in sorted(v["stats"].items()):
        print(f"  {t:<16} {n}")
    for e in v["errors"]:
        print("  ОШИБКА:", e)
    for w in v["warnings"]:
        print("  предупреждение:", w)
    if not v["ok"] and not force:
        print("\nПУБЛИКАЦИЯ ОТМЕНЕНА (есть ошибки). Для принудительной — force=True")
        return None
    import engine
    print("\n=== ПУБЛИКАЦИЯ ===")
    ver = engine._publish(draft, to_mirror=False)
    print("  опубликовано:", ver)
    return ver


def _live_db():
    import engine
    return engine.active_db()


def stats(db=None):
    """Статистика боевой базы."""
    p = db or _live_db()
    if not p or not os.path.isfile(p):
        print("боевая база не найдена")
        return
    con = sqlite3.connect(p)
    cur = con.cursor()
    print("БАЗА:", p, "|", round(os.path.getsize(p) / 1024 / 1024, 1), "МБ")
    for n in [r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]:
        cnt = cur.execute("SELECT COUNT(*) FROM [%s]" % n).fetchone()[0]
        print(f"  {n:<16} {cnt}")
    con.close()


def check(db=None):
    """Проверка целостности (PRAGMA integrity_check)."""
    p = db or _live_db()
    con = sqlite3.connect(p)
    r = con.execute("PRAGMA integrity_check").fetchone()[0]
    print("integrity_check:", r)
    con.close()
    return r == "ok"


def indexes(db=None):
    """Перестроить индексы + ANALYZE (ускорение запросов)."""
    p = db or _live_db()
    con = sqlite3.connect(p)
    t0 = time.perf_counter()
    con.execute("REINDEX")
    con.execute("ANALYZE")
    con.commit()
    print(f"REINDEX + ANALYZE: {time.perf_counter() - t0:.1f} с")
    con.close()


def vacuum(db=None):
    """Сжать базу (дефрагментация)."""
    p = db or _live_db()
    before = os.path.getsize(p)
    con = sqlite3.connect(p)
    t0 = time.perf_counter()
    con.execute("VACUUM")
    con.close()
    after = os.path.getsize(p)
    print(f"VACUUM: {before/1024/1024:.1f} -> {after/1024/1024:.1f} МБ "
          f"({time.perf_counter() - t0:.1f} с)")


def backup(db=None):
    """Бэкап боевой базы (в db\\backup)."""
    import engine
    import shutil
    import datetime
    p = db or _live_db()
    bdir = engine._backup_dir()
    os.makedirs(bdir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(bdir, "plm_reader_%s.db" % ts)
    shutil.copy2(p, dst)
    print("бэкап:", dst)
    engine._rotate_backups()
    return dst


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    if cmd == "stats":
        stats()
    elif cmd == "check":
        check()
    elif cmd == "validate":
        v = validate(arg)
        print("OK" if v["ok"] else "ОШИБКИ", v["stats"])
        for e in v["errors"]:
            print("  ОШИБКА:", e)
        for w in v["warnings"]:
            print("  предупреждение:", w)
    elif cmd == "publish":
        publish(arg)
    elif cmd == "indexes":
        indexes()
    elif cmd == "vacuum":
        vacuum()
    elif cmd == "backup":
        backup()
    else:
        print(__doc__)
