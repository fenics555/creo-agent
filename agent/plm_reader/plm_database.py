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
    python plm_database.py check [--full] [--no-cache] — целостность + индексы + diff схемы + аудит данных
    python plm_database.py schema-snapshot          — снимок DDL схемы в JSON (перед миграцией)
    python plm_database.py ensure-indexes           — создать индексы на связующих колонках
    python plm_database.py indexes                  — REINDEX + ANALYZE
    python plm_database.py vacuum                   — сжать базу
    python plm_database.py backup                   — бэкап боевой базы
    python plm_database.py export-docs              — паспорт схемы + 4 Mermaid ER-диаграммы
    python plm_database.py doctor  [--db ПУТЬ]      — ПОДРОБНЫЙ диагноз базы (СТРОГО READ-ONLY)
    python plm_database.py selftest                 — встроенный регресс-тест (временная БД)
    python plm_database.py repair [--apply] [--db ПУТЬ] — ОЧИСТКА связей (dry-run по умолчанию)
    python plm_database.py compact [--apply] [--db ПУТЬ] — ОБРЕЗКА длинных дампов unknown_fields

КОДЫ ВОЗВРАТА `check`: 0 — чисто, 1 — предупреждения, 2 — ошибки.
Флаг `--json` — структурированный вывод с кодами проблем (ORPHAN / DUPLICATE /
SELF_LINK / EMPTY_KEY / MISSING_INDEX / EXTRA_COLUMN).

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
    # 🔴 V192: +4 колонки, которые пишет СКАНЕР и добавляет миграция (`file_name/file_ext/
    # file_version/version`) — раньше давали ложный шум «лишние колонки» в `check`.
    "snapshots":   ["path", "model", "folder", "size", "mtime", "volume", "material", "name", "designation", "rev", "author", "revdate", "role", "seen", "hist", "creo", "created", "pdata", "file_name", "file_ext", "file_version", "version"],
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
    # ══ 🔴🔴 V192 «ЭТАЛОН = РЕАЛЬНОСТЬ»: эти 10 таблиц ПИШУТ сканер/построители, но их НЕ БЫЛО
    # в эталоне ⇒ `check`/`ensure_indexes`/`doctor` их не видели («слепая зона»: 21 из 31).
    # Колонки — замер по живой базе (`PRAGMA table_info`), сверено с DDL в `engine.SCHEMA`.
    "items":          ["item_key", "model", "folder", "n_files", "n_versions", "exts", "last_mtime"],
    "item_ver":       ["item_key", "version", "ext"],
    "props":          ["child", "prop", "value", "source"],
    "folders":        ["path", "parent", "depth", "models", "files", "seen"],
    "tools":          ["path", "model", "tool_id", "n_params", "assem"],
    "mass_props":     ["path", "model", "name", "value"],
    "unknown_fields": ["path", "model", "name", "count"],
    "graph_metrics":  ["k", "v"],
    "meta":           ["k", "v"],
    # `arch_dim_ch`: РЕАЛЬНО 6 колонок (замер + читатели plm_graph/plm_history). DDL в `engine.py`
    # был устаревшим (3 колонки с `ch`) — исправлен синхронно в V192.
    "arch_dim_ch":    ["arch_date", "model", "dim", "old_val", "new_val", "kind"],
}

# Колонки, по которым должны быть индексы (связующие ключи между таблицами)
LINK_COLS = {"model", "path", "item", "instance", "parent", "child", "base", "from", "to",
             # 🔴 V192: связующий ключ изделий (`items`/`item_ver`) — раньше индекса не получал.
             "item_key"}

# ════════════════════════════════════════════════════════════════════════════════
# V187: ЕДИНЫЙ ИСТОЧНИК для аудита висячих ссылок (используют `check` и `doctor`)
# ════════════════════════════════════════════════════════════════════════════════
ORPHAN_PAIRS = [
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

# V187: АРХИВНЫЕ ИСТОРИЧЕСКИЕ таблицы — Purge-safe: удалять НЕЛЬЗЯ (это история).
ARCHIVE_TABLES = ("changes", "history", "arch_dims", "arch_dim_ch")

# V187: машинные коды проблем (для `check --json`)
CHECK_CODES = ("ORPHAN", "DUPLICATE", "SELF_LINK", "EMPTY_KEY", "MISSING_INDEX", "EXTRA_COLUMN")

# V191: потолок значения в `unknown_fields` (как UF_FIELD_MAX в сканере).
# Причина: дамп ~1300 имён полей на файл ≈ 20 КБ/строку → таблица раздулась до 1185 МБ.
UF_VALUE_MAX = 512

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
    p = _arg_db(db_path)
    if not p or not os.path.isfile(p):
        print("база не найдена:", p)
        return None
    con = connect_safe(p)
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
    con = connect_safe(p)
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
    p = _arg_db(db)
    con = connect_safe(p)
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
    # Д. Снимок схемы (DDL -> JSON) ДО миграции — для отката при ошибке
    try:
        schema_snapshot(p)
    except Exception as e:                       # noqa: BLE001
        if not quiet:
            print("снимок схемы не сделан (%s) — продолжаю" % e)
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
    con = connect_safe(p)
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
    # 🔴 V191: ГЕЙТ КАЧЕСТВА `links` — само-связи в черновике БЛОКИРУЮТ публикацию
    # (модель не может состоять сама из себя; такие строки портят входимость и граф).
    try:
        if "links" in tabs:
            self_links = cur.execute(
                "SELECT COUNT(*) FROM links WHERE lower(parent) = lower(child)").fetchone()[0]
            if self_links:
                res["errors"].append(
                    "links: %d само-связей (parent == child) — публикация запрещена" % self_links)
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
    p = _arg_db(db)
    if not p or not os.path.isfile(p):
        print("боевая база не найдена")
        return
    con = connect_safe(p)
    cur = con.cursor()
    print("БАЗА:", p, "|", round(os.path.getsize(p) / 1024 / 1024, 1), "МБ")
    for n in [r[0] for r in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]:
        cnt = cur.execute("SELECT COUNT(*) FROM [%s]" % n).fetchone()[0]
        print(f"  {n:<16} {cnt}")
    con.close()


def _indexes_on(cur, table):
    """Возвращает множество имён колонок, по которым есть индексы (включая составные).

    🔴 V186-фикс: список индексов МАТЕРИАЛИЗУЕТСЯ через fetchall() ДО вложенного
    PRAGMA index_info на ТОМ ЖЕ курсоре. Иначе повторный execute сбрасывает внешний
    курсор, и читается только ПЕРВЫЙ индекс таблицы (грабля: пропуск индексов).
    """
    idx_cols = set()
    try:
        idx_rows = cur.execute("PRAGMA index_list(%s)" % table).fetchall()
        for row in idx_rows:
            idx_name = row[1]
            for colrow in cur.execute("PRAGMA index_info(%s)" % idx_name).fetchall():
                idx_cols.add(colrow[2])
    except sqlite3.Error:
        pass
    return idx_cols


def _qcol(name):
    """Экранировать имя колонки в двойные кавычки (для reserved words: from, to)."""
    return '"%s"' % name


def _check_orphan_references(cur, issues):
    """Подсчёт висячих ссылок: ключи в дочерних таблицах, которых нет в родительской.

    V187: пишет СТРУКТУРИРОВАННЫЕ проблемы (код ORPHAN) в `issues` для `check --json`.
    Список пар — единый источник `ORPHAN_PAIRS` (его же использует `doctor`).
    """
    pairs = ORPHAN_PAIRS
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
            # 🔴 V193: разделяем «регистр» и «реально нет». Замер по базе шары: 910 127 строк
            # `params` и 142 774 строк `links` совпадают со `snapshots` БЕЗ учёта регистра ⇒
            # «висячие» — в основном НЕ потерянные данные, а разный регистр имени модели.
            try:
                n_case = cur.execute(
                    'SELECT COUNT(*) FROM [%s] WHERE %s IS NOT NULL AND %s != "" '
                    'AND upper(%s) IN (SELECT upper(%s) FROM [%s]) '
                    'AND %s NOT IN (SELECT %s FROM [%s])'
                    % (child_t, _qcol(child_c), _qcol(child_c), _qcol(child_c),
                       _qcol(parent_c), parent_t, _qcol(child_c), _qcol(parent_c), parent_t)
                ).fetchone()[0]
            except sqlite3.Error:
                n_case = 0
            n_real = max(0, n - n_case)
            if n_case:
                issues.append({"code": "ORPHAN_CASE", "severity": "warning", "table": child_t,
                               "message": "регистр имён: %s.%s -> %s.%s (%d строк совпадают без учёта регистра)"
                               % (child_t, child_c, parent_t, parent_c, n_case)})
            if n_real:
                issues.append({"code": "ORPHAN", "severity": "warning", "table": child_t,
                               "message": "орфанные ссылки: %s.%s -> %s.%s (%d строк без родителя)"
                               % (child_t, child_c, parent_t, parent_c, n_real)})


def _check_duplicate_links(cur, issues):
    """Поиск дублей связей и само-связей в links / graph_edges (коды DUPLICATE / SELF_LINK)."""
    if _has_table(cur, "links"):
        try:
            # 🔴 V192: ключ дубля = КАК В `repair` (parent,child,source,kind). Раньше считалось
            # по (parent,child) ⇒ ЛОЖНЫЕ «дубли»: одна пара законно живёт в разных КАНАЛАХ
            # (`dwg` + `mentions` + `asm_comp`). Такие пары — не мусор (см. doctor «мультиканальные»).
            _key = []
            try:
                _cols = [c[1] for c in cur.execute("PRAGMA table_info(links)")]
                _key = [c for c in ("parent", "child", "source", "kind") if c in _cols]
                _ke = ", ".join('"%s"' % c for c in _key)
                dups = cur.execute(
                    "SELECT COUNT(*) FROM (SELECT %s FROM links GROUP BY %s HAVING COUNT(*) > 1)"
                    % (_ke, _ke)).fetchone()[0]
            except sqlite3.Error:
                dups = 0
            if dups:
                issues.append({"code": "DUPLICATE", "severity": "warning", "table": "links",
                               "message": "дубли в links: %d групп по (%s) — тем же ключом чистит `repair`"
                               % (dups, ", ".join(_key))})
        except sqlite3.Error:
            pass
        try:
            self_links = cur.execute(
                "SELECT COUNT(*) FROM links WHERE lower(parent) = lower(child)"
            ).fetchone()[0]
            if self_links:
                issues.append({"code": "SELF_LINK", "severity": "warning", "table": "links",
                               "message": "само-связи в links: %d строк (parent == child)" % self_links})
        except sqlite3.Error:
            pass
    if _has_table(cur, "graph_edges"):
        try:
            # 🔴 V192: ключ дубля = КАК В `repair`: ("from","to",kind) — иначе ложные срабатывания
            # на парах с разными видами связи (structure + copy + mfg …).
            _key = []
            try:
                _cols = [c[1] for c in cur.execute("PRAGMA table_info(graph_edges)")]
                _key = [c for c in ("from", "to", "kind") if c in _cols]
                _ke = ", ".join('"%s"' % c for c in _key)
                dups = cur.execute(
                    "SELECT COUNT(*) FROM (SELECT %s FROM graph_edges GROUP BY %s HAVING COUNT(*) > 1)"
                    % (_ke, _ke)).fetchone()[0]
            except sqlite3.Error:
                dups = 0
            if dups:
                issues.append({"code": "DUPLICATE", "severity": "warning", "table": "graph_edges",
                               "message": "дубли в graph_edges: %d групп по (%s) — тем же ключом чистит `repair`"
                               % (dups, ", ".join(_key))})
        except sqlite3.Error:
            pass
        try:
            self_links = cur.execute(
                'SELECT COUNT(*) FROM graph_edges WHERE "from" = "to"'
            ).fetchone()[0]
            if self_links:
                issues.append({"code": "SELF_LINK", "severity": "warning", "table": "graph_edges",
                               "message": "само-связи в graph_edges: %d строк (from == to)" % self_links})
        except sqlite3.Error:
            pass


def _check_empty_keys(cur, issues):
    """Поиск пустых ключевых колонок (model, path) в таблицах-ссылках (код EMPTY_KEY)."""
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
                issues.append({"code": "EMPTY_KEY", "severity": "warning", "table": t,
                               "message": "пустые ключи: %s.%s = NULL/'' (%d строк)" % (t, col, n)})


# ════════════════════════════════════════════════════════════════════════════════
# В. Оценка фрагментации (recommend_vacuum): freelist_count / page_count > 30%
# ════════════════════════════════════════════════════════════════════════════════
def _fragmentation(p):
    """Оценка фрагментации: (доля_пустых_%, пусто_МБ, всего_МБ) либо None.

    V187: вычисление вынесено из `recommend_vacuum`, чтобы `check --json` мог вернуть
    эти данные машинно (без печати).
    """
    if not p or not os.path.isfile(p):
        return None
    con = connect_safe(p)
    cur = con.cursor()
    try:
        free = cur.execute("PRAGMA freelist_count").fetchone()[0]
        page_size = cur.execute("PRAGMA page_size").fetchone()[0]
        page_count = cur.execute("PRAGMA page_count").fetchone()[0]
    except sqlite3.Error:
        con.close()
        return None
    con.close()
    if not page_count:
        return None
    pct = free * 100.0 / page_count
    return (pct, free * page_size / 1024 / 1024, page_count * page_size / 1024 / 1024)


def recommend_vacuum(db=None):
    """Предупреждение, если доля пустых страниц > 30%."""
    f = _fragmentation(_arg_db(db))
    if f and f[0] > 30:
        print("[*] РЕКОМЕНДАЦИЯ VACUUM: пустых страниц %.1f%% (%.1f МБ из %.1f МБ)" % f)


# ════════════════════════════════════════════════════════════════════════════════
# Б. Автоиндексация (ensure_indexes): CREATE INDEX IF NOT EXISTS на LINK_COLS
# ════════════════════════════════════════════════════════════════════════════════
def ensure_indexes(db=None):
    """Создать индексы на всех связующих колонках (LINK_COLS), где их нет."""
    p = _arg_db(db)
    if not p or not os.path.isfile(p):
        print("база не найдена:", p)
        return
    con = connect_safe(p)
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
    # 🔴 V187: СБРОС КЭША ПРОВЕРКИ. Без этого повторный `check --full` в течение TTL (5 мин)
    # отдавал бы из кэша старый вердикт «нет индексов» (флап MISSING_INDEX), хотя индексы
    # уже созданы. Кэш — не данные: удаляем файл проверки, он пересоздастся при нужде.
    cache = _check_cache_path(p)
    if os.path.isfile(cache):
        try:
            os.remove(cache)
            print("кэш проверки сброшен:", os.path.basename(cache))
        except OSError as e:
            print("кэш проверки сбросить не удалось (%s)" % e)


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


def _run_check(db=None, full=False, use_cache=True):
    """Ядро проверки целостности → dict результата (БЕЗ печати; машинные КОДЫ проблем).

    V187. Коды проблем: ORPHAN, DUPLICATE, SELF_LINK, EMPTY_KEY, MISSING_INDEX,
    EXTRA_COLUMN (+ служебные MISSING_COLUMN, MISSING_TABLE, SCHEMA_VERSION,
    INTEGRITY, NO_DB). Каждая проблема — dict: {code, severity, table, message}.
    """
    p = _arg_db(db)
    if not p or not os.path.isfile(p):
        msg = "база не найдена: %s" % p
        return {"db": p, "present": False, "ok": False, "cached": False,
                "integrity": None, "schema_db": None, "schema_code": SCHEMA_VERSION,
                "issues": [{"code": "NO_DB", "severity": "error", "table": None, "message": msg}],
                "errors": [msg], "warnings": [], "fragmentation": None}
    if use_cache:
        cached = _load_check_cache(p)
        if cached is not None and "issues" in cached:
            cached = dict(cached)
            cached["cached"] = True
            return cached

    con = connect_safe(p)
    cur = con.cursor()
    integrity = cur.execute("PRAGMA integrity_check").fetchone()[0]
    issues = []
    if integrity != "ok":
        issues.append({"code": "INTEGRITY", "severity": "error", "table": None,
                       "message": "integrity_check: %s" % integrity})

    if full:
        # ── 1. Индексы на связующих колонках ──
        for t in SCHEMA:
            if not _has_table(cur, t):
                continue
            idx_cols = _indexes_on(cur, t)
            live_cols = [c[1] for c in cur.execute("PRAGMA table_info(%s)" % t)]
            missing_idx = [c for c in live_cols if c in LINK_COLS and c not in idx_cols]
            if missing_idx:
                issues.append({"code": "MISSING_INDEX", "severity": "warning", "table": t,
                               "message": "таблица %s: нет индексов на связующих колонках %s"
                               % (t, missing_idx)})

        # ── 2. Diff живой схемы с эталоном SCHEMA ──
        for t, expected_cols in SCHEMA.items():
            if not _has_table(cur, t):
                issues.append({"code": "MISSING_TABLE", "severity": "error", "table": t,
                               "message": "таблица %s отсутствует в базе" % t})
                continue
            live_cols = [c[1] for c in cur.execute("PRAGMA table_info(%s)" % t)]
            missing = [c for c in expected_cols if c not in live_cols]
            extra = [c for c in live_cols if c not in expected_cols]
            if missing:
                issues.append({"code": "MISSING_COLUMN", "severity": "error", "table": t,
                               "message": "таблица %s: отсутствуют колонки %s" % (t, missing)})
            if extra:
                issues.append({"code": "EXTRA_COLUMN", "severity": "warning", "table": t,
                               "message": "таблица %s: лишние колонки %s" % (t, extra)})

        # ── 3. Версия схемы ──
        v_db = schema_version(p)
        if v_db != SCHEMA_VERSION:
            issues.append({"code": "SCHEMA_VERSION", "severity": "warning", "table": None,
                           "message": "версия схемы БД (%s) != версии кода (%d)" % (v_db, SCHEMA_VERSION)})

        # ── А. Аудит целостности данных ──
        _check_orphan_references(cur, issues)
        _check_duplicate_links(cur, issues)
        _check_empty_keys(cur, issues)

    con.close()

    # ── В. Оценка фрагментации (машинно, без печати) ──
    frag = _fragmentation(p) if full else None

    errors = [i["message"] for i in issues if i["severity"] == "error"]
    warnings = [i["message"] for i in issues if i["severity"] == "warning"]
    result = {"db": p, "present": True, "ok": not errors, "cached": False,
              "integrity": integrity, "schema_db": schema_version(p),
              "schema_code": SCHEMA_VERSION, "issues": issues,
              "errors": errors, "warnings": warnings, "fragmentation": frag}
    if use_cache:
        _save_check_cache(p, result)
    return result


def _print_check(res):
    """Человекочитаемый вывод результата проверки."""
    if not res.get("present"):
        print(res["errors"][0] if res.get("errors") else "база не найдена")
        return
    if res.get("cached"):
        print("[cache] результат проверки из кэша (TTL %d с):" % CHECK_CACHE_TTL)
    else:
        print("integrity_check:", res["integrity"])
    errors = res.get("errors") or []
    warnings = res.get("warnings") or []
    if errors:
        print("[!] ОШИБКИ СХЕМЫ:")
        for e in errors:
            print("  -", e)
    if warnings:
        print("[*] ПРЕДУПРЕЖДЕНИЯ:")
        for w in warnings:
            print("  -", w)
    if not errors and not warnings:
        print("проверка пройдена — замечаний нет")
    frag = res.get("fragmentation")
    if frag and frag[0] > 30:
        print("[*] РЕКОМЕНДАЦИЯ VACUUM: пустых страниц %.1f%% (%.1f МБ из %.1f МБ)" % frag)


def check(db=None, full=False, use_cache=True):
    """Проверка целостности (совместимость: печатает отчёт и возвращает ok).

    Для машинного вида (коды проблем + exit code) CLI использует `_run_check` и
    `check_exit_code`.
    """
    res = _run_check(db=db, full=full, use_cache=use_cache)
    _print_check(res)
    return res["ok"]


def check_exit_code(res):
    """Код возврата CLI: 0 — чисто, 1 — предупреждения, 2 — ошибки."""
    if res.get("errors"):
        return 2
    if res.get("warnings"):
        return 1
    return 0


def _ro_connect(p):
    """READ-ONLY подключение (URI `mode=ro`) — гарантия, что `doctor` НИЧЕГО не меняет.

    Обычный `connect_safe` может переключить `journal_mode` (запись в заголовок БД).
    Для строго read-only диагностики открываем базу в режиме только чтения.
    """
    from pathlib import Path
    uri = Path(p).resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=30)


def _live_tables(cur):
    """Имена пользовательских таблиц базы."""
    return [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]


def _table_row_count(cur, table):
    """Число строк таблицы (или None, если таблицы нет)."""
    try:
        return cur.execute('SELECT COUNT(*) FROM "%s"' % table).fetchone()[0]
    except sqlite3.Error:
        return None


def _estimate_table_mb(cur, table, cols, sample=300):
    """ОЦЕНКА объёма таблицы в МБ → (мб, строк).

    В этой сборке SQLite виртуальная таблица `dbstat` НЕДОСТУПНА (`no such table: dbstat`),
    поэтому объём оценивается как `строк × средняя длина строки по выборке sample`.
    Значение приблизительное (без служебных накладных расходов) — в отчёте помечено «≈».
    """
    cnt = _table_row_count(cur, table)
    if not cnt:
        return 0.0, (cnt or 0)
    try:
        sel = ", ".join('COALESCE(LENGTH("%s"),0)' % c for c in cols)
        rows = cur.execute('SELECT %s FROM "%s" LIMIT %d' % (sel, table, sample)).fetchall()
    except sqlite3.Error:
        return 0.0, cnt
    if not rows:
        return 0.0, cnt
    avg = sum(sum(r) for r in rows) / float(len(rows))
    return (cnt * avg) / 1024.0 / 1024.0, cnt


def _orphan_counts(cur):
    """Висячие записи по парам ORPHAN_PAIRS → [{table,column,parent,parent_column,count}]."""
    out = []
    for child_t, child_c, parent_t, parent_c in ORPHAN_PAIRS:
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
            try:                                  # V193: сколько из них — чисто регистр
                n_case = cur.execute(
                    'SELECT COUNT(*) FROM [%s] WHERE %s IS NOT NULL AND %s != "" '
                    'AND upper(%s) IN (SELECT upper(%s) FROM [%s]) '
                    'AND %s NOT IN (SELECT %s FROM [%s])'
                    % (child_t, _qcol(child_c), _qcol(child_c), _qcol(child_c),
                       _qcol(parent_c), parent_t, _qcol(child_c), _qcol(parent_c), parent_t)
                ).fetchone()[0]
            except sqlite3.Error:
                n_case = 0
            out.append({"table": child_t, "column": child_c, "parent": parent_t,
                        "parent_column": parent_c, "count": n, "case": n_case,
                        "real": max(0, n - n_case)})
    return out


def _links_diag(cur, table):
    """Диагностика связей: НАСТОЯЩИЕ дубли (ключ как в `repair`) + мультиканальные пары.

    🔴 V192: ключ дубля = `links(parent,child,source,kind)` / `graph_edges("from","to",kind)` —
    ТЕМ ЖЕ ключом чистит `repair`. Раньше считалось по 2 колонкам ⇒ ложные «дубли»:
    одна пара законно приходит разными КАНАЛАМИ (`dwg` + `mentions` + `asm_comp`).
    """
    if not _has_table(cur, table):
        return {"present": False}
    a, b = ("parent", "child") if table == "links" else ("from", "to")
    chan = "source" if table == "links" else "kind"
    d = {"present": True}
    try:
        cols = [c[1] for c in cur.execute("PRAGMA table_info(%s)" % table)]
        d["rows"] = _table_row_count(cur, table) or 0
        key = [c for c in (("parent", "child", "source", "kind") if table == "links"
                           else ("from", "to", "kind")) if c in cols]
        d["key"] = key
        if len(key) >= 2:
            kexpr = ", ".join('"%s"' % c for c in key)
            d["dup_pairs"] = cur.execute(
                'SELECT COUNT(*) FROM (SELECT %s FROM "%s" GROUP BY %s HAVING COUNT(*) > 1)'
                % (kexpr, table, kexpr)).fetchone()[0]
            d["distinct_keys"] = cur.execute(
                'SELECT COUNT(*) FROM (SELECT DISTINCT %s FROM "%s")' % (kexpr, table)).fetchone()[0]
            d["dup_extra_rows"] = max(0, d["rows"] - d["distinct_keys"])
        if chan in cols:
            # «мультиканальные»: одна пара в РАЗНЫХ каналах — это НОРМА, а не дубль
            d["multi_channel"] = cur.execute(
                'SELECT COUNT(*) FROM (SELECT "%s", "%s" FROM "%s" GROUP BY "%s", "%s" '
                'HAVING COUNT(DISTINCT "%s") > 1)' % (a, b, table, a, b, chan)).fetchone()[0]
            d["pair_repeats"] = cur.execute(
                'SELECT COUNT(*) FROM (SELECT "%s", "%s" FROM "%s" GROUP BY "%s", "%s" '
                'HAVING COUNT(*) > 1)' % (a, b, table, a, b)).fetchone()[0]
        d["self_links"] = cur.execute(
            'SELECT COUNT(*) FROM "%s" WHERE lower("%s") = lower("%s")' % (table, a, b)
        ).fetchone()[0]
    except sqlite3.Error as e:
        d["error"] = str(e)
    return d



def _doctor_data(db_path=None):
    """Собирает диагноз базы (СТРОГО READ-ONLY, без печати) → dict."""
    p = _arg_db(db_path)
    res = {"db": p, "present": True, "read_only": True,
           "archive_tables": list(ARCHIVE_TABLES),
           "tables": [], "orphans": [], "safe_dedup": [], "archive": [],
           "links": {}, "graph_edges": {}, "meta": {}}
    if not p or not os.path.isfile(p):
        res["present"] = False
        res["error"] = "база не найдена: %s" % p
        return res
    res["file_mb"] = round(os.path.getsize(p) / 1024.0 / 1024.0, 1)
    try:
        con = _ro_connect(p)
    except sqlite3.Error as e:                       # noqa: BLE001
        res["present"] = False
        res["error"] = "база не открылась только для чтения: %s" % e
        return res
    cur = con.cursor()
    try:
        # ── meta / schema_version ──
        has_meta = _has_table(cur, "meta")
        v_db = 0
        if has_meta:
            row = cur.execute("SELECT v FROM meta WHERE k='schema_version'").fetchone()
            v_db = int(row[0]) if row and str(row[0]).isdigit() else 0
        if not has_meta:
            status = "СТОП: таблицы meta нет (старая схема — нужна миграция)"
        elif v_db == SCHEMA_VERSION:
            status = "OK: schema_version=%d совпадает с кодом" % v_db
        elif v_db < SCHEMA_VERSION:
            status = "ВНИМАНИЕ: база старее кода (%d < %d) — нужна миграция" % (v_db, SCHEMA_VERSION)
        else:
            status = "СТОП: база новее программы (%d > %d) — ничего не менять" % (v_db, SCHEMA_VERSION)
        res["meta"] = {"has_table": has_meta, "schema_version": v_db,
                       "schema_version_code": SCHEMA_VERSION, "status": status}

        # ── объём крупных таблиц (ОЦЕНКА) ──
        sizes = []
        for t in _live_tables(cur):
            if t == "meta":
                continue
            cols = [c[1] for c in cur.execute("PRAGMA table_info(%s)" % t)]
            mb, cnt = _estimate_table_mb(cur, t, cols)
            sizes.append({"table": t, "rows": cnt or 0, "est_mb": round(mb, 1)})
        sizes.sort(key=lambda d: d["est_mb"], reverse=True)
        res["tables"] = sizes

        # ── висячие записи ──
        res["orphans"] = _orphan_counts(cur)

        # ── дубли / само-связи ──
        res["links"] = _links_diag(cur, "links")
        res["graph_edges"] = _links_diag(cur, "graph_edges")

        # ── архивные (Purge-safe) — только счёт строк, НЕ удаляем ──
        for t in ARCHIVE_TABLES:
            if _has_table(cur, t):
                res["archive"].append({"table": t, "rows": _table_row_count(cur, t) or 0})
    finally:
        con.close()

    # ── классификация: что можно чистить безопасно ──
    lk = res["links"]
    if lk.get("present"):
        if lk.get("dup_pairs"):
            res["safe_dedup"].append(
                "links: убрать %d дублей пар (parent,child) — сверх %d лишних строк"
                % (lk["dup_pairs"], lk.get("dup_extra_rows", 0)))
        if lk.get("self_links"):
            res["safe_dedup"].append("links: убрать %d само-связей (parent == child)" % lk["self_links"])
    ge = res["graph_edges"]
    if ge.get("present"):
        if ge.get("dup_pairs"):
            res["safe_dedup"].append("graph_edges: убрать %d дублей пар (from,to)" % ge["dup_pairs"])
        if ge.get("self_links"):
            res["safe_dedup"].append("graph_edges: убрать %d само-связей (from == to)" % ge["self_links"])
    return res



def _print_doctor(res):
    """Человекочитаемый отчёт `doctor`."""
    print("=" * 72)
    print("DOCTOR — диагностика базы PLM (СТРОГО READ-ONLY, ничего не меняется)")
    print("=" * 72)
    if not res.get("present"):
        print(res.get("error"))
        return
    print("БАЗА   :", res["db"])
    print("РАЗМЕР : %.1f МБ" % res.get("file_mb", 0.0))
    m = res.get("meta", {})
    print("SCHEMA : база=%s код=%s" % (m.get("schema_version"), m.get("schema_version_code")))
    print("СТАТУС :", m.get("status"))
    print("")
    print("-- КРУПНЫЕ ТАБЛИЦЫ (объём ≈, оценка по выборке) --")
    for d in res.get("tables", [])[:15]:
        print("   %-16s строк %-10d ≈ %.1f МБ" % (d["table"], d["rows"], d["est_mb"]))
    print("")
    print("-- ВИСЯЧИЕ ЗАПИСИ (ключ отсутствует в snapshots) --")
    if not res.get("orphans"):
        print("   нет")
    for o in res.get("orphans", []):
        print("   %s.%s -> %s.%s : %d строк (регистр %s / реально нет %s)"
              % (o["table"], o["column"], o["parent"], o["parent_column"], o["count"],
                 o.get("case", 0), o.get("real", o["count"])))
    print("")
    print("-- СВЯЗИ links / graph_edges (ключ дубля = как в `repair`) --")
    for key in ("links", "graph_edges"):
        d = res.get(key, {})
        if not d.get("present"):
            print("   %s: таблицы нет" % key)
            continue
        print("   %-12s строк %-9s | НАСТОЯЩИХ дублей %-6s | само-связей %-5s | мультиканальных пар %s"
              % (key, d.get("rows"), d.get("dup_pairs"), d.get("self_links"),
                 d.get("multi_channel")))
        if d.get("multi_channel"):
            print("        └ мультиканальные = НОРМА (одна пара связей приходит разными каналами);")
            print("          ключ (%s) ⇒ удалять нечего." % ", ".join(d.get("key") or []))
    print("")
    print("-- КАНДИДАТЫ НА БЕЗОПАСНУЮ ДЕДУПЛИКАЦИЮ (историю НЕ трогают) --")
    if not res.get("safe_dedup"):
        print("   чисто — дублей пар и само-связей нет")
    for s in res.get("safe_dedup", []):
        print("   *", s)
    print("")
    print("-- АРХИВНЫЕ ИСТОРИЧЕСКИЕ ТАБЛИЦЫ (Purge-safe: УДАЛЯТЬ НЕЛЬЗЯ) --")
    if not res.get("archive"):
        print("   (таких таблиц в базе нет)")
    for a in res.get("archive", []):
        print("   %-16s строк %s" % (a["table"], a["rows"]))
    print("=" * 72)


def doctor(db_path=None, as_json=False):
    """ПОДРОБНЫЙ ДИАГНОЗ базы (СТРОГО READ-ONLY) → dict результата.

    Показывает: состояние `meta.schema_version`; объём крупных таблиц (оценка, МБ);
    висячие записи; дубли связей и само-связи; и ЧЁТКО РАЗДЕЛЯЕТ:
      • кандидаты на безопасную дедупликацию (дубли `links`, само-связи),
      • архивные исторические таблицы `Purge-safe`
        (changes/history/arch_dims/arch_dim_ch), которые удалять НЕЛЬЗЯ.
    """
    res = _doctor_data(db_path)
    if as_json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    else:
        _print_doctor(res)
    return res


def cmd_doctor():
    """CLI-обёртка `doctor` (путь читается из `--db`, флаг `--json` поддержан)."""
    return doctor(as_json="--json" in sys.argv)



def cmd_selftest():
    """Встроенный регресс-тест на ВРЕМЕННОЙ БД (без следов на диске).

    Проверяет: `SCHEMA`, `ensure_indexes` (со сбросом кэша проверки), `check --full`
    (наличие машинных кодов проблем), `doctor` (read-only) и `export_schema_docs`.
    Печатает итог `SELFTEST OK` / `SELFTEST FAIL`. Возвращает bool.
    """
    import shutil
    import tempfile
    problems = []
    tmp = tempfile.mkdtemp(prefix="plm_selftest_")
    try:
        dbf = os.path.join(tmp, "t.db")
        con = connect_safe(dbf)
        cur = con.cursor()
        # SCHEMA: создаём все таблицы эталона
        for t, cols in SCHEMA.items():
            cur.execute('CREATE TABLE IF NOT EXISTS "%s" (%s)'
                        % (t, ", ".join('"%s" TEXT' % c for c in cols)))
        cur.executemany('INSERT INTO snapshots(model,path) VALUES(?,?)',
                        [("A", "/a"), ("B", "/b")])
        # дубль пары + само-связь + орфан (C нет в snapshots)
        cur.executemany('INSERT INTO links(parent,child,qty) VALUES(?,?,?)',
                        [("A", "B", 1), ("A", "B", 2), ("A", "A", 5), ("B", "C", 1)])
        # пустой ключ + орфан
        cur.executemany('INSERT INTO params(model,path,name) VALUES(?,?,?)',
                        [("", "/x", "p1"), ("ZZ", "/z", "p2")])
        # V188: засев graph_edges (само-связь + дубль) — для проверки repair
        cur.executemany('INSERT INTO graph_edges("from","to",kind,qty) VALUES(?,?,?,?)',
                        [("X", "X", "k", 1), ("Y", "Z", "k", 1), ("Y", "Z", "k", 2)])
        # V191: засев unknown_fields (длинный дамп) — для проверки compact
        cur.execute('CREATE TABLE IF NOT EXISTS unknown_fields '
                    '(path TEXT, model TEXT, name TEXT, count INTEGER)')
        cur.execute("INSERT INTO unknown_fields(path,model,name,count) VALUES(?,?,?,?)",
                    ("/big", "x" * 2000, "__ALL__", 1300))
        con.commit()
        con.close()
        set_schema_version(SCHEMA_VERSION, dbf)
        if schema_version(dbf) != SCHEMA_VERSION:
            problems.append("SCHEMA: schema_version базы != коду")

        # ensure_indexes + сброс кэша проверки
        cache = _check_cache_path(dbf)
        with open(cache, "w", encoding="utf-8") as f:
            f.write("{}")
        ensure_indexes(dbf)
        if os.path.isfile(cache):
            problems.append("ensure_indexes: кэш проверки НЕ сброшен")

        # check --full: коды данных видны; индексы уже есть (нет флапа MISSING_INDEX)
        res = _run_check(dbf, full=True, use_cache=False)
        codes = set(i["code"] for i in res["issues"])
        if "MISSING_INDEX" in codes:
            problems.append("check --full: индексы не видны после ensure_indexes (флап кэша)")
        for need in ("DUPLICATE", "SELF_LINK", "EMPTY_KEY", "ORPHAN"):
            if need not in codes:
                problems.append("check --full: не найден код %s" % need)

        # doctor: read-only (размер файла не меняется) + видит орфаны
        before = os.path.getsize(dbf)
        doc = _doctor_data(dbf)
        after = os.path.getsize(dbf)
        if before != after:
            problems.append("doctor: база ИЗМЕНИЛАСЬ (не read-only)")
        if not doc.get("orphans"):
            problems.append("doctor: висячие записи не найдены")
        if not doc.get("safe_dedup"):
            problems.append("doctor: кандидаты на дедупликацию не найдены")

        # export_schema_docs в temp
        docs = os.path.join(tmp, "docs")
        if not export_schema_docs(dbf, out_dir=docs):
            problems.append("export_schema_docs: вернул False")
        elif not os.path.isfile(os.path.join(docs, "schema_passport.md")):
            problems.append("export_schema_docs: нет schema_passport.md")

        # V188: repair --dry-run (база НЕ меняется) и --apply (чистит связи)
        def _cnt(sql):
            _c = connect_safe(dbf)
            try:
                return _c.execute(sql).fetchone()[0]
            finally:
                _c.close()

        links0 = _cnt("SELECT COUNT(*) FROM links")
        edges0 = _cnt("SELECT COUNT(*) FROM graph_edges")
        plan = repair(dbf, dry_run=True, quiet=True)
        if (links0, edges0) != (_cnt("SELECT COUNT(*) FROM links"),
                                _cnt("SELECT COUNT(*) FROM graph_edges")):
            problems.append("repair --dry-run: база ИЗМЕНИЛАСЬ (должна быть read-only)")
        lk_plan = (plan or {}).get("plan", {}).get("links") or {}
        if not (lk_plan.get("self_links") or lk_plan.get("dup_groups")):
            problems.append("repair dry-run: не нашёл дублей/само-связей в links")

        rep = repair(dbf, dry_run=False, quiet=True)
        if not rep or rep.get("deleted") is None:
            problems.append("repair --apply: не выполнено")
        else:
            self_l = _cnt("SELECT COUNT(*) FROM links WHERE lower(parent) = lower(child)")
            dup_l = _cnt("SELECT COUNT(*) FROM (SELECT parent,child,source,kind FROM links "
                         "GROUP BY parent,child,source,kind HAVING COUNT(*) > 1)")
            self_g = _cnt('SELECT COUNT(*) FROM graph_edges WHERE "from" = "to"')
            dup_g = _cnt('SELECT COUNT(*) FROM (SELECT "from","to",kind FROM graph_edges '
                         'GROUP BY "from","to",kind HAVING COUNT(*) > 1)')
            if self_l or dup_l or self_g or dup_g:
                problems.append("repair --apply: остались связи (links %s/%s, graph %s/%s)"
                                % (self_l, dup_l, self_g, dup_g))
            if not rep.get("backup"):
                problems.append("repair --apply: не сделан бэкап")

        # V191: compact unknown_fields — dry-run (не меняет) и --apply (обрезает)
        cp_plan = compact_unknown_fields(dbf, dry_run=True, quiet=True)
        if not cp_plan or not cp_plan.get("plan") or cp_plan["plan"]["long_rows"] < 1:
            problems.append("compact: dry-run не нашёл длинных строк unknown_fields")
        before_len = _cnt("SELECT MAX(LENGTH(model)) FROM unknown_fields")
        cp_res = compact_unknown_fields(dbf, dry_run=False, quiet=True)
        if not cp_res or not cp_res.get("truncated"):
            problems.append("compact --apply: строки не обрезаны")
        else:
            after_len = _cnt("SELECT MAX(LENGTH(model)) FROM unknown_fields")
            if after_len > 512 + 40:
                problems.append("compact: значение осталось длинным (%s)" % after_len)
            if before_len <= after_len:
                problems.append("compact: длина не уменьшилась (%s -> %s)" % (before_len, after_len))
            if _cnt("SELECT COUNT(*) FROM unknown_fields WHERE name='__ALL__'") < 1:
                problems.append("compact: потеряны записи unknown_fields")
            if not cp_res.get("backup"):
                problems.append("compact --apply: не сделан бэкап")

        # ── V192 «ЭТАЛОН = РЕАЛЬНОСТЬ» ────────────────────────────────────────
        def _rows(sql):
            _c = connect_safe(dbf)
            try:
                return _c.execute(sql).fetchall()
            finally:
                _c.close()

        names = set(r[0] for r in _rows(
            "SELECT name FROM sqlite_master WHERE type='table'"))
        missing = sorted(set(SCHEMA) - names)
        if missing:
            problems.append("SCHEMA: таблицы эталона не созданы (%d): %s"
                            % (len(missing), ", ".join(missing)))
        if len(SCHEMA) != 31:
            problems.append("SCHEMA: ожидалось 31 таблица, в эталоне %d" % len(SCHEMA))
        if "file_name" not in SCHEMA.get("snapshots", []):
            problems.append("SCHEMA.snapshots: нет колонки file_name (шум EXTRA_COLUMN вернётся)")

        # мультиканальные пары (одна пара, разные source) — НЕ дубли
        _c = connect_safe(dbf)
        _c.executemany('INSERT INTO links(parent,child,qty,source,kind) VALUES(?,?,?,?,?)',
                       [("M", "N", 1, "dwg", "чертёж"), ("M", "N", 1, "mentions", "упоминание")])
        _c.commit()
        _c.close()
        doc2 = _doctor_data(dbf)
        lk2 = doc2.get("links", {})
        if not lk2.get("multi_channel"):
            problems.append("doctor: мультиканальные пары не найдены")
        if lk2.get("dup_pairs"):
            problems.append("doctor: ложные дубли по (parent,child) остались (%s)" % lk2.get("dup_pairs"))

        # индексы в НОВЫХ таблицах эталона (после ensure_indexes)
        have_uf = set()
        for row in _rows("PRAGMA index_list(unknown_fields)"):
            for ic in _rows('PRAGMA index_info("%s")' % row[1]):
                have_uf.add(ic[2])
        if "model" not in have_uf:
            problems.append("ensure_indexes: нет индекса по unknown_fields(model)")

        # MISSING_TABLE: урезанная база (одна таблица) обязана дать код
        dbf2 = os.path.join(tmp, "t2.db")
        _c2 = connect_safe(dbf2)
        _c2.execute("CREATE TABLE snapshots (path TEXT, model TEXT)")
        _c2.commit()
        _c2.close()
        res3 = _run_check(dbf2, full=True, use_cache=False)
        if "MISSING_TABLE" not in set(i["code"] for i in res3["issues"]):
            problems.append("check: MISSING_TABLE не сработал на урезанной базе")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if os.path.isdir(tmp):
        problems.append("не удалось убрать временную папку: %s" % tmp)
    print("=" * 60)
    print("SELFTEST: проблем %d" % len(problems))
    for pb in problems:
        print("  [!]", pb)
    if problems:
        print("SELFTEST FAIL")
        return False
    print("SELFTEST OK")
    return True



def _repair_plan(cur):
    """План очистки: само-связи и дубли в `links` / `graph_edges` (СТРОГО read-only).

    Архивные таблицы (`changes`, `history`, `arch_dims`, `arch_dim_ch`) НЕ рассматриваются —
    они Purge-safe и очистке НЕ подлежат.
    """
    plan = {}
    specs = (("links", ("parent", "child"), "source", ("parent", "child", "source", "kind")),
             ("graph_edges", ('"from"', '"to"'), "kind", ('"from"', '"to"', "kind")))
    for table, self_cols, _extra, key_cols in specs:
        if not _has_table(cur, table):
            plan[table] = None
            continue
        cols = [c[1] for c in cur.execute("PRAGMA table_info(%s)" % table)]
        info = {"rows_before": _table_row_count(cur, table) or 0,
                "self_links": 0, "dup_groups": 0, "dup_extra": 0}
        a = self_cols[0].strip('"')
        b = self_cols[1].strip('"')
        try:
            info["self_links"] = cur.execute(
                'SELECT COUNT(*) FROM "%s" WHERE lower("%s") = lower("%s")' % (table, a, b)
            ).fetchone()[0]
        except sqlite3.Error:
            pass
        # ключ дедупликации — только из реально существующих колонок
        use_cols = [c for c in key_cols if c.strip('"') in cols]
        if len(use_cols) >= 2:
            kexpr = ", ".join('"%s"' % c.strip('"') for c in use_cols)
            try:
                row = cur.execute(
                    "SELECT COUNT(*), COALESCE(SUM(cnt - 1), 0) FROM ("
                    "SELECT COUNT(*) AS cnt FROM \"%s\" GROUP BY %s HAVING COUNT(*) > 1)"
                    % (table, kexpr)
                ).fetchone()
                info["dup_groups"] = row[0] or 0
                info["dup_extra"] = int(row[1] or 0)
            except sqlite3.Error:
                pass
        plan[table] = info
    return plan


def _dedupe_table(cur, table, key_cols, qty_col=None):
    """Удалить дубли по `key_cols`, оставив ОДНУ строку с МАКСИМАЛЬНЫМ `qty`.

    Возвращает число удалённых строк. Через оконную функцию ROW_NUMBER (SQLite ≥ 3.25).
    """
    cols = [c[1] for c in cur.execute("PRAGMA table_info(%s)" % table)]
    key = [c for c in key_cols if c in cols]
    if len(key) < 2:
        return 0
    kexpr = ", ".join('"%s"' % c for c in key)
    if qty_col and qty_col in cols:
        order = 'CAST(COALESCE("%s", 0) AS INTEGER) DESC, rowid' % qty_col
    else:
        order = "rowid"
    before = _table_row_count(cur, table) or 0
    try:
        cur.execute(
            'DELETE FROM "%s" WHERE rowid NOT IN ('
            '  SELECT rowid FROM ('
            '    SELECT rowid, ROW_NUMBER() OVER (PARTITION BY %s ORDER BY %s) AS rn FROM "%s"'
            '  ) WHERE rn = 1)' % (table, kexpr, order, table))
    except sqlite3.Error as e:
        print("  дубли %s не удалены (%s)" % (table, e))
        return 0
    after = _table_row_count(cur, table) or 0
    return max(0, before - after)



def _print_repair_plan(plan, dry_run=True, title="REPAIR — очистка связей"):
    """Печать плана/итога очистки."""
    print("=" * 68)
    print("%s (%s)" % (title, "DRY-RUN: план, ничего не меняется" if dry_run else "ИТОГ"))
    print("=" * 68)
    for t in ("links", "graph_edges"):
        d = plan.get(t)
        if not d:
            print("  %-12s: таблицы нет" % t)
            continue
        print("  %-12s строк %-9s | само-связей %-7s | дублей групп %-7s (лишних строк %s)"
              % (t, d.get("rows_before"), d.get("self_links"),
                 d.get("dup_groups"), d.get("dup_extra")))
    print("  Архивные таблицы (changes · history · arch_dims · arch_dim_ch) НЕ трогаются (Purge-safe).")
    print("=" * 68)


def repair(db_path=None, dry_run=True, quiet=False):
    """ОЧИСТКА СВЯЗЕЙ: само-связи и дубли в `links` / `graph_edges`.

    🔴 ПО УМОЛЧАНИЮ `dry_run=True` — только показывает план, базу НЕ меняет.
    При `dry_run=False` (`--apply`): обязательный БЭКАП + `schema_snapshot`, затем:
      • удаляются само-связи (`parent == child`) в `links`;
      • удаляются дубли `(parent, child, source, kind)` в `links`, остаётся 1 строка
        с максимальным `qty`;
      • удаляются само-связи (`from == to`) и дубли `(from, to, kind)` в `graph_edges`;
      • АРХИВНЫЕ таблицы (`changes`, `history`, `arch_dims`, `arch_dim_ch`) и орфаны
        в них — НЕ трогаются (Purge-safe).
    Возвращает dict с планом, итогом и числом удалённых строк.
    """
    p = _arg_db(db_path)
    if not p or not os.path.isfile(p):
        print("база не найдена:", p)
        return None
    con = connect_safe(p)
    cur = con.cursor()
    plan = _repair_plan(cur)
    if not quiet:
        _print_repair_plan(plan, dry_run=dry_run)
    if dry_run:
        con.close()
        return {"dry_run": True, "db": p, "plan": plan, "deleted": None}

    # ── APPLY: бэкап обязателен ──
    try:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        bdir = os.path.join(os.path.dirname(p), "backup")
        os.makedirs(bdir, exist_ok=True)
        bpath = os.path.join(bdir, "pre_repair_%s.db" % ts)
        shutil.copy2(p, bpath)
        if not quiet:
            print("бэкап перед repair:", bpath)
    except Exception as e:                       # noqa: BLE001
        print("БЭКАП НЕ СДЕЛАН (%s) — repair ОТМЕНЁН" % e)
        con.close()
        return {"dry_run": False, "db": p, "plan": plan, "deleted": None, "error": str(e)}
    try:
        schema_snapshot(p)
    except Exception as e:                       # noqa: BLE001
        if not quiet:
            print("снимок схемы не сделан (%s) — продолжаю" % e)

    deleted = {}
    if _has_table(cur, "links"):
        cur.execute('DELETE FROM links WHERE lower(parent) = lower(child)')
        deleted["links_self"] = cur.rowcount
        deleted["links_dup"] = _dedupe_table(cur, "links",
                                             ["parent", "child", "source", "kind"], "qty")
    if _has_table(cur, "graph_edges"):
        cur.execute('DELETE FROM graph_edges WHERE "from" = "to"')
        deleted["graph_self"] = cur.rowcount
        deleted["graph_dup"] = _dedupe_table(cur, "graph_edges",
                                             ["from", "to", "kind"], "qty")
    con.commit()
    after = _repair_plan(cur)
    con.close()
    if not quiet:
        _print_repair_plan(after, dry_run=False)
        print("УДАЛЕНО:", deleted)
    return {"dry_run": False, "db": p, "plan": plan, "after": after,
            "deleted": deleted, "backup": bpath}



def _uf_plan(cur):
    """План сжатия `unknown_fields`: сколько строк длиннее потолка и сколько байт освободится."""
    if not _has_table(cur, "unknown_fields"):
        return None
    cols = [c[1] for c in cur.execute("PRAGMA table_info(unknown_fields)")]
    if "model" not in cols:
        return None
    try:
        row = cur.execute(
            "SELECT COUNT(*), COALESCE(SUM(LENGTH(model)), 0) FROM unknown_fields "
            "WHERE model IS NOT NULL AND LENGTH(model) > ?", (UF_VALUE_MAX,)).fetchone()
    except sqlite3.Error:
        return None
    n = row[0] or 0
    total = int(row[1] or 0)
    freed = max(0, total - n * UF_VALUE_MAX)
    return {"rows_total": _table_row_count(cur, "unknown_fields") or 0,
            "long_rows": n, "bytes_long": total, "freed_bytes": freed,
            "freed_mb": round(freed / 1024.0 / 1024.0, 1)}


def compact_unknown_fields(db_path=None, dry_run=True, quiet=False):
    """ОБРЕЗАТЬ старые длинные хвосты `unknown_fields` (столбец `model`) до `UF_VALUE_MAX`.

    🔴 ЗАЧЕМ: дамп всех имён полей ≈ 20 КБ/строку → таблица раздулась до 1185 МБ
    (59 447 строк). Ключи (`path`, `name`) и счётчики (`count`) СОХРАНЯЮТСЯ — теряется
    лишь обрезанный хвост JSON, полное ЧИСЛО полей остаётся в `count`.

    По умолчанию `dry_run=True` — только показывает план. При `dry_run=False`:
    обязательный БЭКАП + `schema_snapshot`, затем обрезка. Освобождённое место в файле
    вернёт `vacuum` (SQLite не уменьшает файл сам).
    Архивные таблицы (`changes/history/arch_dims/arch_dim_ch`) НЕ затрагиваются.
    """
    p = _arg_db(db_path)
    if not p or not os.path.isfile(p):
        print("база не найдена:", p)
        return None
    con = connect_safe(p)
    cur = con.cursor()
    plan = _uf_plan(cur)
    if plan is None:
        if not quiet:
            print("таблица unknown_fields не найдена — нечего сжимать")
        con.close()
        return {"dry_run": dry_run, "db": p, "plan": None}
    if not quiet:
        print("=" * 68)
        print("COMPACT unknown_fields (%s)" % ("DRY-RUN: план, ничего не меняется"
                                               if dry_run else "ИТОГ"))
        print("=" * 68)
        print("  строк всего %-9s | длиннее %d символов: %-7s | освободится ≈ %.1f МБ"
              % (plan["rows_total"], UF_VALUE_MAX, plan["long_rows"], plan["freed_mb"]))
    if dry_run:
        if not quiet:
            print("  Место в файле вернёт команда VACUUM (запустить после сжатия).")
        con.close()
        return {"dry_run": True, "db": p, "plan": plan}
    if not plan["long_rows"]:
        if not quiet:
            print("  нечего обрезать")
        con.close()
        return {"dry_run": False, "db": p, "plan": plan, "truncated": 0}

    # ── APPLY: бэкап обязателен ──
    try:
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        bdir = os.path.join(os.path.dirname(p), "backup")
        os.makedirs(bdir, exist_ok=True)
        bpath = os.path.join(bdir, "pre_compact_%s.db" % ts)
        shutil.copy2(p, bpath)
        if not quiet:
            print("бэкап перед compact:", bpath)
    except Exception as e:                       # noqa: BLE001
        print("БЭКАП НЕ СДЕЛАН (%s) — compact ОТМЕНЁН" % e)
        con.close()
        return None
    try:
        schema_snapshot(p)
    except Exception as e:                       # noqa: BLE001
        if not quiet:
            print("снимок схемы не сделан (%s) — продолжаю" % e)

    cur.execute("UPDATE unknown_fields SET model = substr(model, 1, ?) || ? "
                "WHERE model IS NOT NULL AND LENGTH(model) > ?",
                (UF_VALUE_MAX, "…(обрезано V191)", UF_VALUE_MAX))
    truncated = cur.rowcount
    con.commit()
    after = _uf_plan(cur)
    con.close()
    if not quiet:
        print("обрезано строк: %d" % truncated)
        if after:
            print("  после сжатия: строк всего %s | длиннее потолка %s"
                  % (after["rows_total"], after["long_rows"]))
        print("  Теперь нажмите «Сжать файл базы (Vacuum)», чтобы вернуть ≈ %.1f МБ на диске."
              % (plan["freed_bytes"] / 1024.0 / 1024.0))
        print("=" * 68)
    return {"dry_run": False, "db": p, "plan": plan, "after": after,
            "truncated": truncated, "backup": bpath}



def indexes(db=None):
    """Перестроить индексы + ANALYZE (ускорение запросов)."""
    p = _arg_db(db)
    con = connect_safe(p)
    t0 = time.perf_counter()
    con.execute("REINDEX")
    con.execute("ANALYZE")
    con.commit()
    print(f"REINDEX + ANALYZE: {time.perf_counter() - t0:.1f} с")
    con.close()


def vacuum(db=None):
    """Сжать базу (дефрагментация)."""
    p = _arg_db(db)
    before = os.path.getsize(p)
    con = connect_safe(p)
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
    p = _arg_db(db)
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
    p = _arg_db(db_path)
    if not p or not os.path.isfile(p):
        print("база не найдена:", p)
        return False

    if out_dir is None:
        out_dir = os.path.join(os.path.dirname(HERE), "docs_schema")
    os.makedirs(out_dir, exist_ok=True)

    con = connect_safe(p)
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
    elif cmd in ("check", "check-full"):
        full = (cmd == "check-full") or ("--full" in sys.argv)
        use_cache = "--no-cache" not in sys.argv
        res = _run_check(full=full, use_cache=use_cache)
        if "--json" in sys.argv:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            _print_check(res)
        sys.exit(check_exit_code(res))
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
    elif cmd == "ensure-indexes":
        ensure_indexes(arg if (arg and not arg.startswith("--")) else None)
    elif cmd == "vacuum":
        vacuum()
    elif cmd == "backup":
        backup()
    elif cmd == "schema-snapshot":
        schema_snapshot(arg if (arg and not arg.startswith("--")) else None)
    elif cmd == "export-docs":
        export_schema_docs()
    elif cmd == "doctor":
        cmd_doctor()
    elif cmd == "selftest":
        sys.exit(0 if cmd_selftest() else 1)
    elif cmd == "repair":
        repair(dry_run=("--apply" not in sys.argv))
    elif cmd == "compact":
        compact_unknown_fields(dry_run=("--apply" not in sys.argv))
    else:
        print(__doc__)
