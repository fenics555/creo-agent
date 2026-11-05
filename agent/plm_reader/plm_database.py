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
SCHEMA_VERSION = 4          # ← версия схемы, которую ждёт ЭТОТ код
                            # V171 (05.11.2026): 3 → 4 — миграция `_mig_3_to_4`: ИНДЕКСЫ по колонкам
                            # очистки (`write_item` делал 17 DELETE без индекса ⇒ полный скан таблиц).
                            # ЗАМЕР: запись 168 мс/файл → 1 мс/файл (ускорение скана в 168 раз).
                            # V170: 2 → 3 — `_mig_2_to_3` чистит следы V167 (дубли связей).
                            # V176 (05.11.2026): 2 → 3 — миграция `_mig_2_to_3` ЧИСТИТ СЛЕДЫ V167
                            # (дубли связей: `child` с расширением 10 107 · само-связи 471 ·
                            # раздутая достройка `built` 28 314 · граф). У ВСЕХ, АВТОМАТИЧЕСКИ
                            # при обновлении. Слово владельца: «программу обновляют ДРУГИЕ ЛЮДИ,
                            # как они что-то почистят?» — вот так: миграцией, а не руками.


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


def _mig_2_to_3(con):
    """V2 → V3: ЧИСТКА СЛЕДОВ V167 (дубли связей) — АВТОМАТИЧЕСКИ, у ВСЕХ.

    🔴 ЗАЧЕМ (живой разбор 05.11.2026, слово владельца): «программу обновляют ДРУГИЕ ЛЮДИ,
    как они что-то почистят?» — верно: чистка руками невозможна, она ОБЯЗАНА быть в коде.

    ЧТО ЧИСТИТСЯ и почему:
      1) `links` со `child` С РАСШИРЕНИЕМ (`.ASM`/`.PRT`/`.DRW`) — 10 107 строк.
         Причина: правка V167 писала `parent` стемом, а `child` — сырым именем с расширением
         ⇒ одна деталь жила ДВУМЯ узлами графа. Замер: 10 107 таких строк.
      2) `links` где `parent == child` (регистр не важен) — 471 строка.
         Это «сборка входит сама в себя» — мусор, в графе даёт петлю.
      3) `links` с `origin='built'` — 28 314 строк. Достройка РАЗДУЛАСЬ в 8.5 раз
         (норма 3 340) из-за тех же двойников. Достройка ИДЕМПОТЕНТНА — её перестроит
         `plm_build_links` после скана уже по ЧИСТЫМ данным.
      4) `graph_edges`/`graph_nodes` — очищаются (перестроит `plm_graph_build`).
         Замер: рёбра выросли 66 365 → 100 938 из-за дублей.

    ⚠️ ДАННЫЕ СКАНОВ (`snapshots`/`params`/`history`/`derived`/…) НЕ ТРОГАЕМ.
    ⚠️ Связи `real` (прочитанные из файлов, без расширения, без петли) НЕ ТРОГАЕМ.
    Итог: `links` 88 170 → ~49 300 (убираем 10 578 дублей + 28 314 раздутой достройки).
    """
    cur = con.cursor()
    if not _has_table(cur, "links"):
        return
    # 1) двойники: child с расширением Creo
    # 🔴🔴 V179 (05.11.2026, владелец: «где же чертежи? связей чертёж→модель нет»):
    # ЖИВОЙ ДЕФЕКТ: этот DELETE снёс СВЯЗИ `dwg` И `mfg`! Сканер пишет их ИМЕНЕМ С РАСШИРЕНИЕМ
    # (`extract_links` даёт `model_names = ['23-1013GRI-M2.ASM']`), т.е. ВСЕ `dwg`-связи попадали
    # под маску `.ASM`/`.PRT` и удалялись. Замер: было 822 `dwg` на 2 687 файлах → в базе осталось 3.
    # ЛЕЧЕНИЕ: НЕ трогаем каналы `dwg`/`mfg` — у них имя с расширением ЗАКОННО (это имя файла модели,
    # как его записал Creo). Чистим двойников ТОЛЬКО среди составных каналов (`plm_tree`, `asm_comp`,
    # `family`, `mentions`) — там расширение действительно лишнее.
    for pat in ("%.ASM", "%.PRT", "%.DRW", "%.asm", "%.prt", "%.drw", "%.m_p", "%.M_P"):
        try:
            cur.execute("DELETE FROM links WHERE child LIKE ? "
                        "AND COALESCE(source,'') NOT IN ('dwg','mfg')", (pat,))
        except sqlite3.Error:
            pass
    # 2) само-связи: сборка «входит сама в себя»
    try:
        cur.execute("DELETE FROM links WHERE LOWER(parent)=LOWER(child)")
    except sqlite3.Error:
        pass
    # 3) раздутая достройка: перестроится из чистых данных
    try:
        cur.execute("DELETE FROM links WHERE COALESCE(origin,'')='built'")
    except sqlite3.Error:
        pass
    # 3б) 🔴 V172: МУСОР НАСЛОЕНИЯ («обратное обратное …») в derived — от зацикливания достройки.
    #     Замер боевой базы: 408 строк с двойным «обратное», 3 049 с любым «обратное».
    #     Все `built` сносим, «обратные» виды — тоже (перестроятся чисто, см. `_pairs_kind` V172).
    try:
        cur.execute("DELETE FROM derived WHERE COALESCE(origin,'')='built'")
    except sqlite3.Error:
        pass
    try:
        cur.execute("DELETE FROM derived WHERE kind LIKE '%обратно%' AND kind LIKE '%обратно%обратно%'")
    except sqlite3.Error:
        pass
    # 4) граф: перестроится построителем
    for t in ("graph_edges", "graph_nodes", "graph_metrics"):
        if _has_table(cur, t):
            try:
                cur.execute("DELETE FROM [%s]" % t)
            except sqlite3.Error:
                pass
    con.commit()


def _mig_3_to_4(con):
    """V3 → V4: ИНДЕКСЫ ПО КОЛОНКАМ ОЧИСТКИ (ускорение скана в 168 раз).

    🔴 ЗАЧЕМ (замер 05.11.2026, владелец: «2 недели назад всё читалось быстро»):
    `plm_scanner.write_item` перед записью делает 17× `DELETE FROM <таблица> WHERE <колонка>=?`.
    У этих таблиц НЕ БЫЛО ИНДЕКСА по колонке удаления ⇒ SQLite сканировал ВСЮ таблицу на КАЖДЫЙ
    файл (matrices 1 068 156 строк · arch_dims 248 572 · snapshots 59 299 · dim_all 45 895 …).
    ЗАМЕР: запись 168.0 мс/файл → 1.0 мс/файл С ИНДЕКСАМИ. 9 719 файлов: 30 минут → 10 секунд.

    ⚠️ Сам `connect()` уже создаёт эти индексы (`SCHEMA` → `CREATE INDEX IF NOT EXISTS`),
    миграция нужна для баз, которые НЕ проходят `connect()` (обслуживание, пробы, аудит),
    и чтобы поднять `schema_version` (видно, что база «догнала»).
    Идемпотентно: `IF NOT EXISTS` — повторный прогон безвреден.
    """
    cur = con.cursor()
    if not _has_table(cur, "snapshots"):
        return
    for sql in (
        "CREATE INDEX IF NOT EXISTS ix_snap_path ON snapshots(path)",
        "CREATE INDEX IF NOT EXISTS ix_matrices_path ON matrices(path)",
        "CREATE INDEX IF NOT EXISTS ix_dimall_path ON dim_all(path)",
        "CREATE INDEX IF NOT EXISTS ix_components_path ON components(path)",
        "CREATE INDEX IF NOT EXISTS ix_bodies_path ON bodies(path)",
        "CREATE INDEX IF NOT EXISTS ix_mastermat_path ON master_mat(path)",
        "CREATE INDEX IF NOT EXISTS ix_drawing_path ON drawing(path)",
        "CREATE INDEX IF NOT EXISTS ix_tools_path ON tools(path)",
        "CREATE INDEX IF NOT EXISTS ix_derived_child ON derived(child)",
        "CREATE INDEX IF NOT EXISTS ix_derived_base ON derived(base)",
        "CREATE INDEX IF NOT EXISTS ix_props_child ON props(child)",
        "CREATE INDEX IF NOT EXISTS ix_archdims_date ON arch_dims(arch_date)",
        "CREATE INDEX IF NOT EXISTS ix_archdimch_date ON arch_dim_ch(arch_date)",
    ):
        try:
            cur.execute(sql)
        except sqlite3.Error:
            pass          # нет таблицы/колонки в этой базе — пропускаем
    con.commit()


MIGRATIONS = [
    (0, _mig_0_to_1),           # 0 → 1
    (1, _mig_1_to_2),           # 1 → 2
    (2, _mig_2_to_3),           # 2 → 3   чистка следов V167 (дубли связей)
    (3, _mig_3_to_4),           # 3 → 4   ИНДЕКСЫ по колонкам очистки (скан ×168 быстрее)
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
