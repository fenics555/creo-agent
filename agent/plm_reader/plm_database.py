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
import json
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

# ════════════════════════════════════════════════════════════════════════════════
# ЭТАЛОН СХЕМЫ — ожидаемые таблицы и колонки (для diff-аудита в `check`)
# ═══════════════════════════════════════════════════════════════════════════════
SCHEMA = {
    "snapshots":   ["path", "model", "folder", "size", "mtime", "volume", "material", "name", "designation", "rev", "author", "revdate", "role", "seen", "hist", "creo", "created", "pdata"],
    "params":      ["path", "model", "name", "type", "value"],
    "bodies":      ["path", "model", "folder", "version", "body_id", "seq", "volume", "density", "surfarea", "mass"],
    "materials":   ["path", "model", "name", "description", "mtype", "density", "n_props", "system"],
    "master_mat":  ["path", "model", "current_material", "master_name", "reported_name", "has_master"],
    "matrices":    ["path", "model", "field", "dims", "vals"],
    "components":  ["path", "model", "comp", "count", "kind"],
    "drawing":     ["path", "model", "source_models", "states", "uniq_name", "sheet_size"],
    "features":    ["path", "model", "feat_id", "defs", "typenum", "typename", "symbol_key", "parent_id", "seq"],
    "dimensions":  ["path", "model", "feat_id", "dim_type", "nominal", "tol_class", "tol_type", "bound", "dim_name"],
    "dim_all":     ["path", "model", "feat_id", "nominal", "idx"],
    "equations":   ["path", "model", "kind", "name", "expression", "old_val", "new_val", "feat_id"],
    "health":      ["path", "model", "regen", "reg_status", "inactive", "geom_rev"],
    "history":     ["path", "model", "ts", "user", "computer", "creo", "rev", "action", "ts_int"],
    "changes":     ["id", "item", "rev", "kind", "descr", "who", "ts"],
    "family":      ["generic", "instance", "params", "source"],
    "graph_nodes": ["model", "kind", "folder", "path", "size", "volume", "material", "creo", "rev", "n_down", "n_up", "has_media"],
    "graph_edges": ["from", "to", "kind", "dir", "origin", "qty", "channel"],
    "links":       ["parent", "child", "qty", "source", "origin", "kind"],
    "derived":     ["child", "base", "kind", "source", "origin"],
    "arch_dims":   ["arch_date", "model", "dims"],
}

# Колонки, по которым должны быть индексы (связующие ключи между таблицами)
LINK_COLS = {"model", "path", "item", "instance", "parent", "child", "base", "from", "to"}

# Путь к конфигурации tbls для генерации документации
TBL_CONFIG_PATH = os.path.join(os.path.dirname(HERE), "..", "..", "repo", "Creo", "PLM", "db_schema", ".tbls.yml")
TBL_CONFIG_PATH = os.path.abspath(TBL_CONFIG_PATH)

# ════════════════════════════════════════════════════════════════════════════════
# Г. Защита от сетевых блокировок (connect_safe): timeout + retry, journal_mode=DELETE
# ════════════════════════════════════════════════════════════════════════════════
def connect_safe(p, timeout=30, retries=5):
    """Подключение к SQLite с таймаутом и повторами при 'database is locked'.

    Для совместимости с сетевой шарой SMB используем journal_mode=DELETE (без WAL).
    """
    last_err = None
    for i in range(retries):
        try:
            con = sqlite3.connect(p, timeout=timeout)
            # journal_mode=DELETE — безопаснее на SMB, чем WAL
            try:
                con.execute("PRAGMA journal_mode=DELETE").fetchone()
            except sqlite3.Error:
                pass
            return con
        except sqlite3.OperationalError as e:
            last_err = e
            msg = str(e).lower()
            if "database is locked" in msg or "locked" in msg:
                time.sleep(0.5 * (i + 1))
                continue
            raise
    raise last_err


# ════════════════════════════════════════════════════════════════════════════════
# Д. Снимок схемы перед миграцией (schema_snapshot): DDL -> JSON рядом с БД
# ════════════════════════════════════════════════════════════════════════════════
def schema_snapshot(db_path=None):
    """Сохранить DDL всех объектов из sqlite_master в JSON рядом с базой."""
    p = db_path or _live_db()
    if not p or not os.path.isfile(p):
        print("база не найдена:", p)
        return None
    con = sqlite3.connect(p)
    cur = con.cursor()
    cur.execute("SELECT type, name, sql FROM sqlite_master WHERE sql IS NOT NULL")
    snapshot = {}
    for typ, name, sql in cur.fetchall():
        snapshot.setdefault(typ, []).append({"name": name, "sql": sql})
    con.close()
    snap_path = p + ".schema_snapshot.json"
    with open(snap_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, ensure_ascii=False, indent=2)
    print("снимок схемы:", snap_path)
    return snap_path


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


def _indexes_on(cur, table):
    """Возвращает множество имён колонок, по которым есть индексы (включая составные)."""
    idx_cols = set()
    try:
        for row in cur.execute("PRAGMA index_list(%s)" % table):
            idx_name = row[1]
            for colrow in cur.execute("PRAGMA index_info(%s)" % idx_name):
                idx_cols.add(colrow[2])
    except sqlite3.Error:
        pass
    return idx_cols


def _qcol(name):
    """Экранировать имя колонки в двойные кавычки (для reserved words: from, to)."""
    return '"%s"' % name


def _check_orphan_references(cur, warnings):
    """Подсчёт висячих ссылок: ключи в дочерних таблицах, которых нет в родительской."""
    pairs = [
        ("params", "model", "snapshots", "model"),
        ("params", "path", "snapshots", "path"),
        ("bodies", "model", "snapshots", "model"),
        ("bodies", "path", "snapshots", "path"),
        ("materials", "model", "snapshots", "model"),
        ("materials", "path", "snapshots", "path"),
        ("master_mat", "model", "snapshots", "model"),
        ("master_mat", "path", "snapshots", "path"),
        ("matrices", "model", "snapshots", "model"),
        ("matrices", "path", "snapshots", "path"),
        ("components", "model", "snapshots", "model"),
        ("components", "path", "snapshots", "path"),
        ("drawing", "model", "snapshots", "model"),
        ("drawing", "path", "snapshots", "path"),
        ("features", "model", "snapshots", "model"),
        ("features", "path", "snapshots", "path"),
        ("dimensions", "model", "snapshots", "model"),
        ("dimensions", "path", "snapshots", "path"),
        ("dim_all", "model", "snapshots", "model"),
        ("dim_all", "path", "snapshots", "path"),
        ("equations", "model", "snapshots", "model"),
        ("equations", "path", "snapshots", "path"),
        ("health", "model", "snapshots", "model"),
        ("health", "path", "snapshots", "path"),
        ("history", "model", "snapshots", "model"),
        ("history", "path", "snapshots", "path"),
        ("arch_dims", "model", "snapshots", "model"),
        ("arch_dim_ch", "model", "snapshots", "model"),
        ("graph_nodes", "model", "snapshots", "model"),
        ("graph_nodes", "path", "snapshots", "path"),
        ("changes", "item", "snapshots", "model"),
        ("family", "instance", "snapshots", "model"),
        ("links", "parent", "snapshots", "model"),
        ("links", "child", "snapshots", "model"),
        ("derived", "base", "snapshots", "model"),
        ("derived", "child", "snapshots", "model"),
        ("graph_edges", "from", "graph_nodes", "model"),
        ("graph_edges", "to", "graph_nodes", "model"),
    ]
    for child_t, child_c, parent_t, parent_c in pairs:
        if not _has_table(cur, child_t) or not _has_table(cur, parent_t):
            continue
        try:
            n = cur.execute(
                'SELECT COUNT(*) FROM [%s] WHERE %s IS NOT NULL AND %s != "" '
                'AND %s NOT IN (SELECT %s FROM [%s])'
                % (child_t, _qcol(child_c), _qcol(child_c), _qcol(child_c), _qcol(parent_c), parent_t)
            ).fetchone()[0]
        except sqlite3.Error:
            continue
        if n:
            warnings.append(
                "орфанные ссылки: %s.%s -> %s.%s (%d строк без родителя)"
                % (child_t, child_c, parent_t, parent_c, n)
            )


def _check_duplicate_links(cur, warnings):
    """Поиск дублей связей и само-связей в links / graph_edges."""
    if _has_table(cur, "links"):
        try:
            dups = cur.execute(
                'SELECT parent, child, COUNT(*) FROM links GROUP BY parent, child HAVING COUNT(*) > 1'
            ).fetchall()
            if dups:
                warnings.append("дубли в links: %d пар (parent, child) повторяются" % len(dups))
        except sqlite3.Error:
            pass
        try:
            self_links = cur.execute(
                "SELECT COUNT(*) FROM links WHERE lower(parent) = lower(child)"
            ).fetchone()[0]
            if self_links:
                warnings.append("само-связи в links: %d строк (parent == child)" % self_links)
        except sqlite3.Error:
            pass
    if _has_table(cur, "graph_edges"):
        try:
            dups = cur.execute(
                'SELECT "from", "to", COUNT(*) FROM graph_edges GROUP BY "from", "to" HAVING COUNT(*) > 1'
            ).fetchall()
            if dups:
                warnings.append("дубли в graph_edges: %d пар (from, to) повторяются" % len(dups))
        except sqlite3.Error:
            pass
        try:
            self_links = cur.execute(
                'SELECT COUNT(*) FROM graph_edges WHERE "from" = "to"'
            ).fetchone()[0]
            if self_links:
                warnings.append("само-связи в graph_edges: %d строк (from == to)" % self_links)
        except sqlite3.Error:
            pass


def _check_empty_keys(cur, warnings):
    """Поиск пустых ключевых колонок (model, path) в таблицах-ссылках."""
    for t in ("snapshots", "params", "bodies", "materials", "master_mat", "matrices",
              "components", "drawing", "features", "dimensions", "dim_all", "equations",
              "health", "history", "graph_nodes"):
        if not _has_table(cur, t):
            continue
        for col in ("model", "path"):
            try:
                n = cur.execute(
                    'SELECT COUNT(*) FROM [%s] WHERE %s IS NULL OR %s = ""'
                    % (t, _qcol(col), _qcol(col))
                ).fetchone()[0]
            except sqlite3.Error:
                continue
            if n:
                warnings.append("пустые ключи: %s.%s = NULL/'' (%d строк)" % (t, col, n))


# ════════════════════════════════════════════════════════════════════════════════
# В. Оценка фрагментации (recommend_vacuum): freelist_count / page_count > 30%
# ════════════════════════════════════════════════════════════════════════════════
def recommend_vacuum(db=None):
    """Предупреждение, если доля пустых страниц > 30%."""
    p = _arg_db(db)
    if not p or not os.path.isfile(p):
        return
    con = sqlite3.connect(p)
    cur = con.cursor()
    try:
        free = cur.execute("PRAGMA freelist_count").fetchone()[0]
        page_size = cur.execute("PRAGMA page_size").fetchone()[0]
        page_count = cur.execute("PRAGMA page_count").fetchone()[0]
    except sqlite3.Error:
        con.close()
        return
    con.close()
    if page_count == 0:
        return
    pct = free * 100.0 / page_count
    if pct > 30:
        free_mb = free * page_size / 1024 / 1024
        total_mb = page_count * page_size / 1024 / 1024
        print("[*] РЕКОМЕНДАЦИЯ VACUUM: пустых страниц %.1f%% (%.1f МБ из %.1f МБ)"
              % (pct, free_mb, total_mb))


# ════════════════════════════════════════════════════════════════════════════════
# Б. Автоиндексация (ensure_indexes): CREATE INDEX IF NOT EXISTS на LINK_COLS
# ════════════════════════════════════════════════════════════════════════════════
def ensure_indexes(db=None):
    """Создать индексы на всех связующих колонках (LINK_COLS), где их нет."""
    p = _arg_db(db)
    if not p or not os.path.isfile(p):
        print("база не найдена:", p)
        return
    con = sqlite3.connect(p)
    cur = con.cursor()
    created = 0
    for t in SCHEMA:
        if not _has_table(cur, t):
            continue
        live_cols = [c[1] for c in cur.execute("PRAGMA table_info(%s)" % t)]
        idx_cols = _indexes_on(cur, t)
        for col in live_cols:
            if col in LINK_COLS and col not in idx_cols:
                idx_name = "idx_%s_%s" % (t, col)
                try:
                    cur.execute(
                        'CREATE INDEX IF NOT EXISTS "%s" ON "%s"("%s")' % (idx_name, t, col)
                    )
                    created += 1
                except sqlite3.Error:
                    pass
    con.commit()
    con.close()
    print("создано индексов: %d" % created)


# ════════════════════════════════════════════════════════════════════════════════
# Ж. Кэш проверки схемы (TTL 5 мин): .plm_check_cache.json рядом с БД
# ════════════════════════════════════════════════════════════════════════════════
CHECK_CACHE_TTL = 300  # 5 минут


def _check_cache_path(db_path):
    return db_path + ".plm_check_cache.json"


def _load_check_cache(db_path):
    cp = _check_cache_path(db_path)
    if not os.path.isfile(cp):
        return None
    try:
        with open(cp, "r", encoding="utf-8") as f:
            data = json.load(f)
        db_mtime = os.path.getmtime(db_path)
        v_db = schema_version(db_path)
        if (data.get("db_mtime") == db_mtime
                and data.get("schema_version") == v_db):
            age = time.time() - data.get("ts", 0)
            if age < CHECK_CACHE_TTL:
                return data
    except Exception:
        pass
    return None


def _save_check_cache(db_path, data):
    cp = _check_cache_path(db_path)
    data["ts"] = time.time()
    try:
        data["db_mtime"] = os.path.getmtime(db_path)
    except OSError:
        data["db_mtime"] = None
    data["schema_version"] = schema_version(db_path)
    data["ttl"] = CHECK_CACHE_TTL
    with open(cp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
def check(db=None, full=False, use_cache=True):
    """Проверка целостности: PRAGMA integrity_check + индексы + diff схемы + аудит данных.

    Если full=True — сверяет живые колонки с эталоном SCHEMA,
    проверяет индексы на связующих колонках, запускает аудит данных
    (орфанные ссылки, дубли, само-связи, пустые ключи) и recommend_vacuum.
    Кэшируется в .plm_check_cache.json (TTL 5 мин), если use_cache=True.
    """
    p = db or _live_db()
    if use_cache:
        cached = _load_check_cache(p)
        if cached is not None:
            print("[cache] результат проверки из кэша (TTL %d с):" % CHECK_CACHE_TTL)
            if cached.get("errors"):
                for e in cached["errors"]:
                    print("  [!] ОШИБКА:", e)
            if cached.get("warnings"):
                for w in cached["warnings"]:
                    print("  [*] предупреждение:", w)
            if not cached.get("errors") and not cached.get("warnings"):
                print("проверка пройдена — замечаний нет")
            return cached.get("ok", False)

    con = connect_safe(p)
    cur = con.cursor()
    r = con.execute("PRAGMA integrity_check").fetchone()[0]
    print("integrity_check:", r)
    ok = r == "ok"
    errors = []
    warnings = []

    if full:
        # ── 1. Индексы на связующих колонках ──
        for t in SCHEMA:
            if not _has_table(cur, t):
                continue
            idx_cols = _indexes_on(cur, t)
            live_cols = [c[1] for c in cur.execute("PRAGMA table_info(%s)" % t)]
            missing_idx = [c for c in live_cols if c in LINK_COLS and c not in idx_cols]
            if missing_idx:
                warnings.append(
                    "таблица %s: нет индексов на связующих колонках %s"
                    % (t, missing_idx)
                )

        # ── 2. Diff живой схемы с эталоном SCHEMA ──
        for t, expected_cols in SCHEMA.items():
            if not _has_table(cur, t):
                warnings.append("таблица %s отсутствует в базе" % t)
                continue
            live_cols = [c[1] for c in cur.execute("PRAGMA table_info(%s)" % t)]
            missing = [c for c in expected_cols if c not in live_cols]
            extra = [c for c in live_cols if c not in expected_cols]
            if missing:
                errors.append("таблица %s: отсутствуют колонки %s" % (t, missing))
            if extra:
                warnings.append("таблица %s: лишние колонки %s" % (t, extra))

        # ── 3. Версия схемы ──
        v_db = schema_version(p)
        if v_db != SCHEMA_VERSION:
            warnings.append(
                "версия схемы БД (%d) != версии кода (%d)" % (v_db, SCHEMA_VERSION)
            )

        # ── А. Аудит целостности данных ──
        _check_orphan_references(cur, warnings)
        _check_duplicate_links(cur, warnings)
        _check_empty_keys(cur, warnings)

    con.close()

    # ── В. Оценка фрагментации ──
    if full:
        recommend_vacuum(p)

    result = {"ok": ok, "errors": errors, "warnings": warnings}
    if use_cache:
        _save_check_cache(p, result)

    if errors:
        print("[!] ОШИБКИ СХЕМЫ:")
        for e in errors:
            print("  -", e)
        ok = False
    if warnings:
        print("[*] ПРЕДУПРЕЖДЕНИЯ:")
        for w in warnings:
            print("  -", w)
    if not errors and not warnings:
        print("проверка пройдена — замечаний нет")
    return ok


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


def export_schema_docs(db_path=None, out_dir=None):
    """Генерация schema_passport.md + 4 Mermaid ER-диаграммы по viewpoint.

    Читает конфигурацию .tbls.yml (если есть) и генерирует документацию
    на чистом Python (без внешней программы tbls.exe).
    """
    p = db_path or _live_db()
    if not p or not os.path.isfile(p):
        print("база не найдена:", p)
        return False

    if out_dir is None:
        out_dir = os.path.join(os.path.dirname(HERE), "docs_schema")
    os.makedirs(out_dir, exist_ok=True)

    con = sqlite3.connect(p)
    cur = con.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
    )
    all_tables = [r[0] for r in cur.fetchall()]

    table_cols = {}
    for t in all_tables:
        cur.execute("PRAGMA table_info(%s)" % t)
        table_cols[t] = [r[1] for r in cur.fetchall()]

    relations = []
    viewpoints = []
    comments = {}
    if os.path.isfile(TBL_CONFIG_PATH):
        try:
            import yaml  # type: ignore
            with open(TBL_CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            relations = cfg.get("relations", []) or []
            viewpoints = cfg.get("viewpoints", []) or []
            for c in cfg.get("comments", []) or []:
                comments[c["table"]] = c
        except Exception as _e:
            print("не удалось прочитать .tbls.yml:", _e)

    rel_map = {}
    for rel in relations:
        t = rel["table"]
        cols = rel["columns"]
        pt = rel["parentTable"]
        pcols = rel["parentColumns"]
        for c, pc in zip(cols, pcols):
            rel_map.setdefault(t, []).append((pt, c, pc))

    lines = []
    lines.append("# Паспорт схемы базы PLM Reader")
    lines.append("")
    lines.append("Источник: `%s`" % p)
    lines.append("Всего таблиц: %d" % len(all_tables))
    lines.append("")
    lines.append("## Таблицы")
    lines.append("")
    for t in all_tables:
        cols = table_cols.get(t, [])
        comment = comments.get(t, {})
        tc = comment.get("tableComment", "")
        lines.append("### `%s`" % t)
        if tc:
            lines.append("")
            lines.append(tc)
            lines.append("")
        lines.append("| Колонка |")
        lines.append("|---------|")
        for c in cols:
            lines.append("| `%s` |" % c)
        child_rels = rel_map.get(t, [])
        if child_rels:
            lines.append("")
            lines.append("Связи (из этой таблицы):")
            for pt, cc, pc in child_rels:
                lines.append("- `%s.%s` → `%s.%s`" % (t, cc, pt, pc))
        lines.append("")

    passport_path = os.path.join(out_dir, "schema_passport.md")
    with open(passport_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("паспорт схемы:", passport_path)

    def _mermaid(vp_name, tables):
        out = ["erDiagram", ""]
        for t in tables:
            if t not in table_cols:
                continue
            out.append("    %s {" % t)
            for c in table_cols[t]:
                out.append("        string %s" % c)
            out.append("    }")
            out.append("")
        for t in tables:
            for pt, cc, pc in rel_map.get(t, []):
                if pt in tables:
                    out.append("    %s ||--o{{ %s : \"%s → %s\"" % (t, pt, cc, pc))
        if not any(rel_map.get(t, []) for t in tables):
            out.append("    %% нет связей в этом ракурсе")
        return "\n".join(out)

    for vp in viewpoints:
        name = vp.get("name", "view")
        tables = vp.get("tables", [])
        safe = name.replace(" ", "_").replace("&", "and").replace("/", "_")
        mmd_path = os.path.join(out_dir, "er_%s.mmd" % safe)
        with open(mmd_path, "w", encoding="utf-8") as f:
            f.write(_mermaid(name, tables))
        print("mermaid ER:", mmd_path)

    con.close()
    return True


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "stats"
    arg = sys.argv[2] if len(sys.argv) > 2 else None
    if cmd == "stats":
        stats()
    elif cmd == "check":
        full = "--full" in sys.argv
        check(full=full)
    elif cmd == "check-full":
        check(full=True)
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
    elif cmd == "export-docs":
        export_schema_docs()
    else:
        print(__doc__)
