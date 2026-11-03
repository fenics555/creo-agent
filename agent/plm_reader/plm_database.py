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
    python plm_database.py schema                — ВЕРСИЯ СХЕМЫ (база / код) + список миграций
    python plm_database.py migrate [--db ПУТЬ]   — ПРИВЕСТИ БАЗУ К СХЕМЕ (шаг за шагом)
    python plm_database.py validate <draft.db>   — проверка черновика
    python plm_database.py publish <draft.db>    — публикация в боевую
    python plm_database.py indexes               — REINDEX + ANALYZE
    python plm_database.py vacuum                — сжать базу
    python plm_database.py backup                — бэкап боевой базы

МИГРАЦИИ (ЗАКОН, живое состояние схемы):
    Схема ВЕРСИОНИРУЕТСЯ: `meta.schema_version` (в базе) ↔ `SCHEMA_VERSION` (в коде).
      N == M  → всё в порядке;
      N <  M  → Database мигрирует ШАГ ЗА ШАГОМ (N→N+1→…→M), каждый шаг в транзакции;
      N >  M  → СТОП «база новее программы» — НИЧЕГО не ломать (правило README §1).

    🔴 ЗАПРЕЩЕНО: `DROP`/переименование колонок и таблиц без прямого слова владельца.
       Разрешено: `ALTER TABLE ... ADD COLUMN` (данные НЕ теряются).
    🔴 БЭКАП ПЕРЕД МИГРАЦИЕЙ — обязателен.
    🔴 Данные (заполнение новых колонок) — ОТДЕЛЬНЫМ проходом (сканер), не в миграции.
"""
import datetime
import os
import shutil
import sqlite3
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


# ═══════════════════════════════════════════════════════════════════════════════
# РЕЕСТР МИГРАЦИЙ — ОДНО МЕСТО (добавлять ТОЛЬКО сюда)
#   Каждая запись: (версия_ОТ, функция). Функция переводит схему РОВНО на +1.
#   Функция получает коннект и ОБЯЗАНА быть безопасной:
#   только ADD COLUMN / CREATE TABLE / CREATE INDEX. Данные не трогаем.
# ═══════════════════════════════════════════════════════════════════════════════
SCHEMA_VERSION = 2          # ← версия схемы, которую ждёт ЭТОТ код


def _has_col(cur, table, col):
    """Есть ли колонка `col` в таблице `table` (без падения на отсутствии)."""
    try:
        return col in [r[1] for r in cur.execute("PRAGMA table_info(%s)" % table)]
    except sqlite3.Error:
        return False


def _has_table(cur, table):
    return bool(cur.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone())


def _mig_0_to_1(con):
    """V0 → V1: завести `meta.schema_version` + индексы паспорта.

    Ничего не удаляем: только `CREATE TABLE IF NOT EXISTS` и `CREATE INDEX IF NOT EXISTS`.
    """
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
    for s in (
        "CREATE INDEX IF NOT EXISTS ix_snap_model ON snapshots(model)",
        "CREATE INDEX IF NOT EXISTS ix_snap_folder ON snapshots(folder)",
        "CREATE INDEX IF NOT EXISTS ix_snap_des ON snapshots(designation)",
    ):
        try:
            cur.execute(s)
        except sqlite3.Error:
            pass          # нет таблицы `snapshots` — пропускаем (база ещё пустая)
    con.commit()


def _mig_1_to_2(con):
    """V1 → V2: колонки ФАЙЛА в `snapshots` + `file_*` в `items`.

    ЗАЧЕМ: «прям ИМЯ ФАЙЛА писать первым! тогда будет понятно что есть что,
    а где реально дубли» (слово владельца 03.11.2026). Имя файла С РАСШИРЕНИЕМ,
    БЕЗ номера версии (`.prt.1` → `.prt`).

    🔴 Только ADD COLUMN — данные целы (старые строки: новые поля = NULL,
    заполняются следующим сканом).
    """
    cur = con.cursor()
    # snapshots: файл как первичное
    for col, typ in (("file_name", "TEXT"), ("file_ext", "TEXT"), ("file_version", "INTEGER")):
        if not _has_col(cur, "snapshots", col):
            cur.execute("ALTER TABLE snapshots ADD COLUMN %s %s" % (col, typ))
    # items: расширение — часть КЛЮЧА изделия (file ≠ деталь/сборка/чертёж)
    # ⚠️ ЖИВОЙ ФАКТ: в СТАРОЙ базе (V0, 14 таблиц) `items` ЕЩЁ НЕТ — она появилась в V141.
    #    Поэтому колонки добавляем ТОЛЬКО если таблица есть (иначе пропускаем — сканер создаст).
    if _has_table(cur, "items"):
        for col, typ in (("file_exts", "TEXT"), ("n_files", "INTEGER")):
            if not _has_col(cur, "items", col):
                cur.execute("ALTER TABLE items ADD COLUMN %s %s" % (col, typ))
    for s in ("CREATE INDEX IF NOT EXISTS ix_snap_fname ON snapshots(file_name)",
              "CREATE INDEX IF NOT EXISTS ix_snap_fext ON snapshots(file_ext)"):
        try:
            cur.execute(s)
        except sqlite3.Error:
            pass
    con.commit()


MIGRATIONS = [
    (0, _mig_0_to_1),           # 0 → 1
    (1, _mig_1_to_2),           # 1 → 2
]


# ═══════════════════════════════════════════════════════════════════════════════
# ВЕРСИЯ СХЕМЫ + МИГРАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════════
def _arg_db(db=None):
    """Какая база: явный `db` → `--db ПУТЬ` из argv → активная (боевая).

    🔴 ВАЖНО (V160): раньше функции звали `_live_db()` напрямую, и `--db` ИГНОРИРОВАЛСЯ —
    проба на КОПИИ молча шла в БОЕВУЮ базу (на шаре!). Теперь путь берётся явно.
    """
    if db:
        return db
    if "--db" in sys.argv:
        i = sys.argv.index("--db")
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return _live_db()


def schema_version(db=None):
    """Версия схемы В БАЗЕ. Нет `meta`/записи → 0 (старая схема)."""
    p = _arg_db(db)
    if not p or not os.path.isfile(p):
        return None
    con = sqlite3.connect(p)
    try:
        if not _has_table(con.cursor(), "meta"):
            return 0
        r = con.execute("SELECT v FROM meta WHERE k='schema_version'").fetchone()
        return int(r[0]) if r and str(r[0]).isdigit() else 0
    except sqlite3.Error:
        return 0
    finally:
        con.close()


def set_schema_version(v, db=None):
    p = db or _live_db()
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT)")
    con.execute("INSERT OR REPLACE INTO meta VALUES ('schema_version', ?)", (str(int(v)),))
    con.commit()
    con.close()


def schema(db=None):
    """Показать версию схемы (база / код) и реестр миграций."""
    p = _arg_db(db)
    v_db = schema_version(p)
    print("БАЗА          :", p)
    print("ВЕРСИЯ В БАЗЕ :", v_db)
    print("ВЕРСИЯ В КОДЕ :", SCHEMA_VERSION)
    if v_db is None:
        print("СТАТУС        : база не найдена")
    elif v_db == SCHEMA_VERSION:
        print("СТАТУС        : OK — схема актуальна")
    elif v_db < SCHEMA_VERSION:
        print("СТАТУС        : ВНИМАНИЕ — база СТАРЕЕ кода, нужна миграция (migrate)")
    else:
        print("СТАТУС        : СТОП — БАЗА НОВЕЕ ПРОГРАММЫ, ничего не менять (откат кода?)")
    print("РЕЕСТР МИГРАЦИЙ:")
    for frm, fn in MIGRATIONS:
        print("   %d -> %d  %s" % (frm, frm + 1, fn.__name__))
    return v_db


def migrate(db=None, quiet=False):
    """Привести базу к `SCHEMA_VERSION`, ШАГ ЗА ШАГОМ. Возвращает (было, стало).

    Правила: бэкап ПЕРЕД первым шагом; `N > M` → СТОП; каждая миграция в транзакции.
    """
    p = _arg_db(db)
    if not p or not os.path.isfile(p):
        print("база не найдена")
        return None, None
    v = schema_version(p)
    if v is None:
        return None, None
    if v > SCHEMA_VERSION:
        print("СТОП: база новее программы (база %d > код %d) — НИЧЕГО НЕ МЕНЯЮ"
              % (v, SCHEMA_VERSION))
        return v, v
    if v == SCHEMA_VERSION:
        if not quiet:
            print("схема актуальна (версия %d) — миграция не нужна" % v)
        return v, v
    # БЭКАП (обязательно!)
    try:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        bdir = os.path.join(os.path.dirname(p), "backup")
        os.makedirs(bdir, exist_ok=True)
        bpath = os.path.join(bdir, "pre_migrate_%s_v%d.db" % (ts, v))
        shutil.copy2(p, bpath)
        if not quiet:
            print("бэкап перед миграцией:", bpath)
    except Exception as e:                       # noqa: BLE001
        print("БЭКАП НЕ СДЕЛАН (%s) — миграция ОТМЕНЕНА" % e)
        return v, v
    v0 = v
    con = sqlite3.connect(p)
    for frm, fn in sorted(MIGRATIONS):
        if v <= frm < SCHEMA_VERSION:
            try:
                fn(con)
                v = frm + 1
                set_schema_version(v, p)
                if not quiet:
                    print("  миграция %d -> %d : %s OK" % (frm, v, fn.__name__))
            except Exception as e:               # noqa: BLE001
                print("  миграция %d -> %d : ОШИБКА %s" % (frm, frm + 1, e))
                break
    con.close()
    if not quiet:
        print("ИТОГ: схема %s -> %s" % (v0, v))
    return v0, v


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
    elif cmd == "schema":
        schema()
    elif cmd == "migrate":
        # migrate [--db ПУТЬ]
        _db = None
        if "--db" in sys.argv:
            i = sys.argv.index("--db")
            if i + 1 < len(sys.argv):
                _db = sys.argv[i + 1]
        migrate(_db)
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
