# -*- coding: utf-8 -*-
"""plm_schema.py — DDL-схема единой базы PLM (V199: вынесена из engine.py).

Единая точка правды схемы; в `engine.py` подключается как `engine.SCHEMA` (совместимо).
"""

SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
  path TEXT PRIMARY KEY, model TEXT, folder TEXT, size INTEGER, mtime REAL, volume REAL,
  material TEXT, name TEXT, designation TEXT, rev TEXT, author TEXT, revdate TEXT,
  role TEXT, seen TEXT, hist INTEGER, creo TEXT, created REAL,
  file_name TEXT, file_ext TEXT, file_version INTEGER, version INTEGER);
CREATE TABLE IF NOT EXISTS changes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, rev TEXT, kind TEXT, descr TEXT,
  who TEXT, ts TEXT);
-- 🔴 V140 (28.10.2026, решение владельца): РАЗЛИЧАТЬ РЕАЛЬНЫЕ И ПОСТРОИТЕЛЬНЫЕ СВЯЗИ.
-- Владелец: «связи строятся не в базу, а ПО БАЗЕ! Где-то запись связи вниз (сборки: сколько каких
-- деталей входит — обратной связи НЕТ, нужно достраивать!), где-то вверх (при наследовании/зеркале/
-- булевых операциях потомок знает родителя, а родитель не в курсе — нужно достроить!). В базе должны
-- быть РАЗНЫЕ КОЛОНКИ "реальные связи" и "построительные", чтобы видеть, где ошибка: в чтении файлов
-- или в построителе связей» + «РЕАЛ можно писать в базу сразу как и все параметры; БУИЛТ — в ту же
-- базу, одной обойдёмся» + «ГЛАВНОЕ: либо одно править, либо другое!»
--
-- `origin` = 'real'  — связь ПРОЧИТАНА из файла (работа СКАНЕРА; неверно — правим сканер);
-- `origin` = 'built' — связь ДОСТРОЕНА из базы (работа ДОСТРОИТЕЛЯ; неверно — правим достроитель).
-- Миграция колонки — в `connect()` ПОСЛЕ `executescript(SCHEMA)` (на новой базе таблиц ещё нет —
-- живой прогон 28.10.2026 дал `no such table: main.links`, если миграция шла раньше).
CREATE TABLE IF NOT EXISTS links (parent TEXT, child TEXT, qty INTEGER, source TEXT, kind TEXT, origin TEXT);
CREATE TABLE IF NOT EXISTS derived (child TEXT, base TEXT, kind TEXT, source TEXT);
-- V139 (28.10.2026, скилл §7 + ЗАМЕР): НАСЛЕДОВАНИЕ СВОЙСТВА (не геометрии).
-- 🔴 ЗАМЕР ДОКАЗАЛ (1 500 живых файлов): слова `nasled` в файлах Creo НЕТ ВООБЩЕ (0 вхождений) —
-- `nasled.PTC_*` это формат БАЗЫ PLM (значение колонки role), а НЕ байты файла. Поэтому в `props`
-- пишем ТОЛЬКО то, что РЕАЛЬНО прочитано из файла: имя материала (`mat_name_ptr`), усадка
-- (`Z_SHRINK_FACTOR`), таблица семейства и т.п. Схемные имена (`PTC_*`) в базу НЕ идут — это мусор.
CREATE TABLE IF NOT EXISTS props (child TEXT, prop TEXT, value TEXT, source TEXT);
-- V125: ВСЕ ПАРАМЕТРЫ МОДЕЛИ «как в Creo» (имя + тип + значение). Владелец: «хранить нужно
-- как все параметры детали, так и все параметры исполнения — тогда связи будут реальные».
CREATE TABLE IF NOT EXISTS params (path TEXT, model TEXT, name TEXT, type TEXT, value TEXT);
-- V125: ТАБЛИЦА СЕМЕЙСТВА (генерик ↔ исполнения) — ОТДЕЛЬНО от физических связей `links`.
-- Владелец: «давай попробуем отдельную family, ну а вдруг чего — переделаем».
CREATE TABLE IF NOT EXISTS family (generic TEXT, instance TEXT, params TEXT, source TEXT);
-- V126: ИСТОРИЯ ПРАВОК «КТО И КОГДА» — КОМПЬЮТЕР + ПОЛЬЗОВАТЕЛЬ + ВРЕМЯ + ВЕРСИЯ CREO.
-- Владелец: «+ что когда правилось и кем (имя компьютера + юзер)». Creo пишет это в файл
-- (`user_name`, `comment` → «Наименование компьютера: 'X'», `modif_time`, `Proe_version`).
CREATE TABLE IF NOT EXISTS history (path TEXT, model TEXT, ts TEXT, user TEXT, computer TEXT,
  creo TEXT, rev TEXT, action TEXT, ts_int INTEGER);
CREATE TABLE IF NOT EXISTS folders (path TEXT PRIMARY KEY, parent TEXT, depth INTEGER,
  models INTEGER, files INTEGER, seen TEXT);
-- V135: ЗДОРОВЬЕ ФАЙЛА — вынесено ИЗ `try` (грабля 28.10.2026: таблица создавалась внутри
-- `try/except`, исключение гасилось, и в боевой базе таблицы `health` НЕ БЫЛО — «no such table:
-- health», история/здоровье файлов не выводились). Теперь создаётся здесь, в `connect()`.
-- Владелец: «Нужно знать историю и ЗДОРОВЬЕ файлов крео».
CREATE TABLE IF NOT EXISTS health (path TEXT PRIMARY KEY, model TEXT, regen TEXT,
  reg_status TEXT, inactive INTEGER, geom_rev TEXT);
-- 🔴 V141 (30.10.2026, слово владельца): «каждый параметр — в своей ячейке». Нормализация по СУЩНОСТЯМ.
-- Причина: `params` (1 135 928 строк) — «солянка»: обозначение, масса, единицы, материал в одной куче.
-- Теперь: внутренние PRO_MP_* → mass_props; размеры → dimensions; дерево → features;
-- уравнения (ДВА места) → equations; материал → materials. `params` остаётся для ПРОЧИХ
-- (у каждого человека свои имена — правила в settings.json, НЕ в коде).
-- Владелец — SCANNER (engine.py). Схему меняет только Database (plm_database.py).
CREATE TABLE IF NOT EXISTS mass_props (path TEXT, model TEXT, name TEXT, value REAL);
CREATE TABLE IF NOT EXISTS dimensions (path TEXT, model TEXT, feat_id INTEGER, dim_type INTEGER,
  nominal REAL, tol_class INTEGER, tol_type INTEGER, bound INTEGER, dim_name TEXT);
CREATE TABLE IF NOT EXISTS features (path TEXT, model TEXT, feat_id INTEGER, defs INTEGER,
  typenum INTEGER, typename TEXT, symbol_key INTEGER, parent_id INTEGER, seq INTEGER);
CREATE TABLE IF NOT EXISTS equations (path TEXT, model TEXT, kind TEXT, name TEXT,
  expression TEXT, old_val TEXT, new_val TEXT, feat_id INTEGER);
-- 🔴🔴 V154 ШАГ B: ОДНА `materials` (объединение двух прежних объявлений!).
-- Было ДВЕ таблицы с тем же именем (`mtype`/`density` и `n_props`/`system`) — SQLite создавал
-- первую, и `scanner_write` падал `no column named n_props` ⇒ таблица ПУСТАЯ.
-- Теперь колонки ОБЪЕДИНЕНЫ: окно читает `mtype`/`density`, новый сканер пишет `n_props`/`system`.
CREATE TABLE IF NOT EXISTS materials (path TEXT, model TEXT, name TEXT, description TEXT,
  mtype TEXT, density REAL, n_props INTEGER, system INTEGER);
-- V141: индекс на `changes` (569 225 строк БЕЗ индексов — любой запрос = скан всей таблицы).

-- [V141-ВРЕМЕННО] ДОП. ТАБЛИЦЫ нового сканера (удалить при переходе на scanner_write)
CREATE TABLE IF NOT EXISTS items (item_key TEXT PRIMARY KEY, model TEXT, folder TEXT,
  n_files INTEGER, n_versions INTEGER, exts TEXT, last_mtime REAL);
CREATE TABLE IF NOT EXISTS item_ver (item_key TEXT, version INTEGER, ext TEXT,
  PRIMARY KEY(item_key, version, ext));
CREATE TABLE IF NOT EXISTS bodies (path TEXT, model TEXT, folder TEXT, version INTEGER,
  body_id INTEGER, seq INTEGER, volume REAL, density REAL, surfarea REAL, mass REAL);
-- 🔴🔴 V154 ШАГ B: ДВЕ РАЗНЫХ `materials` БЫЛИ ОБЪЯВЛЕНЫ В ОДНОЙ SCHEMA (стр. выше — с
-- `mtype`/`density`, и здесь — с `n_props`/`system`). SQLite создавал ПЕРВУЮ, поэтому
-- `scanner_write` падал: `table materials has no column named n_props` ⇒ таблица оставалась
-- ПУСТОЙ. Теперь ОДНА таблица со ВСЕМИ колонками (объединение), запись совместима с обоими
-- потребителями (окно читает mtype/density, новый сканер пишет n_props/system).
-- ⚠️ Первое объявление (стр. 1219) помечено `_materials_legacy` и в SCHEMA не создаётся.
CREATE TABLE IF NOT EXISTS master_mat (path TEXT PRIMARY KEY, model TEXT, current_material TEXT,
  master_name TEXT, reported_name TEXT, has_master INTEGER);
CREATE TABLE IF NOT EXISTS tools (path TEXT, model TEXT, tool_id TEXT, n_params INTEGER, assem TEXT);
CREATE TABLE IF NOT EXISTS unknown_fields (path TEXT, model TEXT, name TEXT, count INTEGER);
CREATE TABLE IF NOT EXISTS dim_all (path TEXT, model TEXT, feat_id INTEGER, nominal REAL, idx INTEGER);
CREATE TABLE IF NOT EXISTS matrices (path TEXT, model TEXT, field TEXT, dims TEXT, vals TEXT);
-- 🔴🔴 V171 (05.11.2026): ИНДЕКСЫ ПО `path` ДЛЯ ТАБЛИЦ, КОТОРЫЕ ЧИСТИТ `write_item`.
-- ЖИВАЯ ПРИЧИНА ТОРМОЗА СКАНА (замер 05.11.2026): `plm_scanner.write_item` перед записью делает
-- 17× `DELETE FROM <таблица> WHERE path=?` (закон «перескан ЗАМЕНЯЕТ, а не НАКАПЛИВАЕТ»).
-- БЕЗ индекса по `path` SQLite выполняет ПОЛНЫЙ СКАН таблицы на КАЖДЫЙ файл. Замер:
--   matrices 1 068 156 строк · arch_dims 248 572 · arch_dim_ch 224 845 · snapshots 59 299 ·
--   dim_all 45 895 · derived 44 712 · components 13 195 — ВСЕ без индекса по path.
-- ИТОГ БЕЗ ИНДЕКСОВ: запись 184.9 мс/файл (при разборе 12.6 мс) ⇒ 9 719 файлов = ~30 минут.
-- СТАЛО: индекс превращает полный скан в поиск по B-tree (доли мс).
-- ⚠️ У этих таблиц колонки `path` НЕТ (проверено 05.11.2026) — индексы по ИХ колонкам:
--   arch_dims/arch_dim_ch — по `arch_date` (write_item их чистит по path ВПУСТУЮ — отдельная тема);
--   derived — по `child`; props — по `child`.
-- `derived`/`props` чистятся в `do_scan` по `child`, поэтому индекс по `child` ускоряет и это.
CREATE TABLE IF NOT EXISTS drawing (path TEXT PRIMARY KEY, model TEXT, source_models TEXT,
  states TEXT, uniq_name TEXT, sheet_size TEXT);
CREATE TABLE IF NOT EXISTS components (path TEXT, model TEXT, comp TEXT, count INTEGER, kind TEXT);

-- 🔴🔴 V142 (30.10.2026, слово владельца): ГРАФ-ПОСТРОИТЕЛЬ — СВОИ ТАБЛИЦЫ.
-- «ГРАФ-построитель по единой базе по системе ЧИТАЕТ ВСЁ, ПИШЕТ ТОЛЬКО В СВОЁ. Делает полный
--  граф связей всей базы. Далее ХТМЛ окно подключить к этой базе». Раньше граф СОБИРАЛСЯ НА ЛЕТУ
-- (`collect_by_path` — с чтением файлов Creo!), поэтому HTML «строил заново» и работал минуты.
-- Теперь: граф ОДИН РАЗ строится в эти таблицы (`plm_graph_build.py`), а показ только ЧИТАЕТ.
-- Виды и направления — из единого словаря `plm_links.KINDS/DIRS` (structure/inherit/derive/copy/variant).
CREATE TABLE IF NOT EXISTS graph_nodes (model TEXT PRIMARY KEY, kind TEXT, folder TEXT,
  path TEXT, size INTEGER, volume REAL, material TEXT, creo TEXT, rev TEXT,
  n_down INTEGER, n_up INTEGER, has_media INTEGER);
CREATE TABLE IF NOT EXISTS graph_edges ("from" TEXT, "to" TEXT, kind TEXT, dir TEXT,
  origin TEXT, qty INTEGER, channel TEXT);
CREATE TABLE IF NOT EXISTS graph_metrics (k TEXT PRIMARY KEY, v TEXT);

CREATE TABLE IF NOT EXISTS arch_dims (model TEXT, arch_date TEXT, dims TEXT);
CREATE TABLE IF NOT EXISTS arch_dim_ch (arch_date TEXT, model TEXT, dim TEXT, old_val TEXT, new_val TEXT, kind TEXT);

-- 🔴 V209 (P2): `meta` — 31-я таблица. Раньше создавалась только миграцией `_mig_0_to_1` и
-- движком (do_scan/publish) ⇒ на свежей базе из `connect()` её НЕ было (31/31 не сходилось).
-- Теперь DDL == эталон `plm_database.SCHEMA` (31 таблица) с первой же секунды.
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);

-- 🔴 V209 (P3): ИНДЕКСЫ — В САМОЙ СХЕМЕ (было: только миграции `_mig_*` и схема черновика сканера;
-- в DDL их не было, хотя комментарий обещал). Все `IF NOT EXISTS` ⇒ накат на ЛЮБУЮ старую базу
-- безопасен (данные и архивы changes/history/arch_* не трогаются). Гарантируют, что база, поднятая
-- только через `engine.connect()`, сразу имеет индексы (иначе `write_item` делал 17 DELETE без
-- индекса — замедление скана ×168, см. V171).
CREATE INDEX IF NOT EXISTS ix_snap_model     ON snapshots(model);
CREATE INDEX IF NOT EXISTS ix_snap_folder    ON snapshots(folder);
CREATE INDEX IF NOT EXISTS ix_snap_des       ON snapshots(designation);
CREATE INDEX IF NOT EXISTS ix_snap_fname     ON snapshots(file_name);
CREATE INDEX IF NOT EXISTS ix_snap_fext      ON snapshots(file_ext);
CREATE INDEX IF NOT EXISTS ix_snap_path      ON snapshots(path);
CREATE INDEX IF NOT EXISTS ix_bodies_model   ON bodies(model);
CREATE INDEX IF NOT EXISTS ix_bodies_path    ON bodies(path);
CREATE INDEX IF NOT EXISTS ix_mat_model      ON materials(model);
CREATE INDEX IF NOT EXISTS ix_mat_name       ON materials(name);
CREATE INDEX IF NOT EXISTS ix_mastermat_path ON master_mat(path);
CREATE INDEX IF NOT EXISTS ix_tools_path     ON tools(path);
CREATE INDEX IF NOT EXISTS ix_uf_path        ON unknown_fields(path);
CREATE INDEX IF NOT EXISTS ix_uf_name        ON unknown_fields(name);
CREATE INDEX IF NOT EXISTS ix_dima_path      ON dim_all(path);
CREATE INDEX IF NOT EXISTS ix_dimall_path    ON dim_all(path);
CREATE INDEX IF NOT EXISTS ix_mx_path        ON matrices(path);
CREATE INDEX IF NOT EXISTS ix_mx_field       ON matrices(field);
CREATE INDEX IF NOT EXISTS ix_matrices_path  ON matrices(path);
CREATE INDEX IF NOT EXISTS ix_drw_model      ON drawing(model);
CREATE INDEX IF NOT EXISTS ix_drawing_path   ON drawing(path);
CREATE INDEX IF NOT EXISTS ix_cmp_path       ON components(path);
CREATE INDEX IF NOT EXISTS ix_cmp_comp       ON components(comp);
CREATE INDEX IF NOT EXISTS ix_components_path ON components(path);
CREATE INDEX IF NOT EXISTS ix_items_model    ON items(model);
CREATE INDEX IF NOT EXISTS ix_items_folder   ON items(folder);
CREATE INDEX IF NOT EXISTS ix_derived_child  ON derived(child);
CREATE INDEX IF NOT EXISTS ix_derived_base   ON derived(base);
CREATE INDEX IF NOT EXISTS ix_props_child    ON props(child);
CREATE INDEX IF NOT EXISTS ix_archdims_date  ON arch_dims(arch_date);
CREATE INDEX IF NOT EXISTS ix_archdimch_date ON arch_dim_ch(arch_date);
"""
