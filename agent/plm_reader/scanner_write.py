# -*- coding: utf-8 -*-
r"""
scanner_write.py — ЗАПИСЬ в базу ПЛМ (долг 5). ЗАКОН: черновик → публикация.

ПРАВИЛА ДОМА:
  • ПРЯМАЯ ЗАПИСЬ В БОЕВУЮ БАЗУ ЗАПРЕЩЕНА: скан пишет в ЛОКАЛЬНЫЙ ЧЕРНОВИК
    (`%TEMP%\plm_reader_draft_<pid>.db`), затем ПУБЛИКАЦИЯ.
  • ВСЁ пишем (закон «в файлах мусора НЕТ»): включая `unknown_fields`.
  • Владелец таблиц: SCANNER. Чужие — только чтение.

НОВЫЕ ТАБЛИЦЫ (V141): bodies · materials · master_mat · tools · unknown_fields · dim_all
"""
import os
import sqlite3
import tempfile
import time

SCHEMA_V141 = """
CREATE TABLE IF NOT EXISTS bodies (
  path TEXT, model TEXT, folder TEXT, version INTEGER, body_id INTEGER, seq INTEGER,
  volume REAL, density REAL, surfarea REAL, mass REAL);
CREATE INDEX IF NOT EXISTS ix_bodies_model ON bodies(model);
CREATE INDEX IF NOT EXISTS ix_bodies_path  ON bodies(path);

CREATE TABLE IF NOT EXISTS materials (
  path TEXT, model TEXT, name TEXT, description TEXT, n_props INTEGER, system INTEGER);
CREATE INDEX IF NOT EXISTS ix_mat_model ON materials(model);
CREATE INDEX IF NOT EXISTS ix_mat_name  ON materials(name);

CREATE TABLE IF NOT EXISTS master_mat (
  path TEXT PRIMARY KEY, model TEXT, current_material TEXT,
  master_name TEXT, reported_name TEXT, has_master INTEGER);

CREATE TABLE IF NOT EXISTS tools (
  path TEXT, model TEXT, tool_id TEXT, n_params INTEGER, assem TEXT);
CREATE INDEX IF NOT EXISTS ix_tools_path ON tools(path);

-- ЗАКОН «в файлах мусора НЕТ»: всё непонятное — сюда, НЕ отбрасывать!
CREATE TABLE IF NOT EXISTS unknown_fields (path TEXT, model TEXT, name TEXT, count INTEGER);
CREATE INDEX IF NOT EXISTS ix_uf_path ON unknown_fields(path);
CREATE INDEX IF NOT EXISTS ix_uf_name ON unknown_fields(name);

-- ВСЕ номиналы размера (не только «основной»)
CREATE TABLE IF NOT EXISTS dim_all (
  path TEXT, model TEXT, feat_id INTEGER, nominal REAL, idx INTEGER);
CREATE INDEX IF NOT EXISTS ix_dima_path ON dim_all(path);

-- МАТРИЦЫ И ГАБАРИТЫ (§181): field · dims · values (JSON)
CREATE TABLE IF NOT EXISTS matrices (
  path TEXT, model TEXT, field TEXT, dims TEXT, vals TEXT);
CREATE INDEX IF NOT EXISTS ix_mx_path ON matrices(path);
CREATE INDEX IF NOT EXISTS ix_mx_field ON matrices(field);

-- ЧЕРТЁЖ (.drw): связь с моделью + состояния
CREATE TABLE IF NOT EXISTS drawing (
  path TEXT PRIMARY KEY, model TEXT, source_models TEXT, states TEXT,
  uniq_name TEXT, sheet_size TEXT);
CREATE INDEX IF NOT EXISTS ix_drw_model ON drawing(model);

-- СОСТАВ СБОРКИ (компоненты) — дополняет links
CREATE TABLE IF NOT EXISTS components (
  path TEXT, model TEXT, comp TEXT, count INTEGER, kind TEXT);
CREATE INDEX IF NOT EXISTS ix_cmp_path ON components(path);
CREATE INDEX IF NOT EXISTS ix_cmp_comp ON components(comp);

-- ЗДОРОВЬЕ (заполняем!)
CREATE TABLE IF NOT EXISTS health (
  path TEXT PRIMARY KEY, model TEXT, regen TEXT, reg_status TEXT, inactive INTEGER);

-- 🔴 ИЗДЕЛИЕ (уникальность!): «модель в конкретной папке» — РАЗНЫЕ ПАПКИ = РАЗНЫЕ ИЗДЕЛИЯ
-- Замер: 47 389 файлов → 24 267 имён (23 122 «лишних» = версии + одноимённые в др. папках)
CREATE TABLE IF NOT EXISTS items (
  item_key TEXT PRIMARY KEY,     -- folder + '\\' + model (УНИКАЛЬНЫЙ ключ изделия)
  model TEXT, folder TEXT,
  n_files INTEGER, n_versions INTEGER, exts TEXT, last_mtime REAL);
CREATE INDEX IF NOT EXISTS ix_items_model ON items(model);
CREATE INDEX IF NOT EXISTS ix_items_folder ON items(folder);

-- ВЕРСИИ ИЗДЕЛИЯ (для подсчёта n_versions)
CREATE TABLE IF NOT EXISTS item_ver (
  item_key TEXT, version INTEGER, ext TEXT, PRIMARY KEY(item_key, version, ext));
"""


def model_of(path):
    """Имя модели из пути (без .prt.N/.asm.N/.drw.N/.mfg.N)."""
    f = os.path.basename(path)
    for ext in (".prt", ".asm", ".drw", ".mfg", ".frm", ".lay", ".sec"):
        i = f.lower().find(ext)
        if i > 0:
            return f[:i]
    return f.rsplit(".", 1)[0]


def path_parts(path):
    """
    🔴 УНИКАЛЬНОСТЬ ОДНОИМЁННЫХ ФАЙЛОВ (замер 30.10.2026: 47 389 файлов → 24 267 имён!).

    Возвращает dict: folder · model · ext · version · item_key
      folder    — папка (РАЗНЫЕ ПАПКИ = РАЗНЫЕ ФАЙЛЫ!)
      model     — имя модели (без версии/расширения)
      ext       — тип (.prt/.asm/.drw/.mfg)
      version   — номер версии (.prt.2 → 2)
      item_key  — КЛЮЧ ИЗДЕЛИЯ = folder + '\\' + model (уникален для «модели в папке»)
    """
    d = os.path.dirname(path)
    f = os.path.basename(path)
    low = f.lower()
    ext = ""
    for e in (".prt", ".asm", ".drw", ".mfg", ".frm", ".lay", ".sec"):
        i = low.find(e)
        if i > 0:
            ext = e.lstrip(".")
            break
    ver = None
    parts = f.rsplit(".", 2)
    if len(parts) == 3:
        try:
            ver = int(parts[2])
        except ValueError:
            ver = None
    m = model_of(path)
    return {"folder": d, "model": m, "ext": ext, "version": ver,
            "item_key": (d + "\\" + m) if d else m}


def draft_path():
    """Путь ЧЕРНОВИКА (запись идёт ТОЛЬКО сюда, не в боевую!)."""
    return os.path.join(tempfile.gettempdir(), "plm_reader_draft_%d.db" % os.getpid())


def open_draft(db=None):
    """Открыть черновик + создать схему. Возвращает (con, path)."""
    p = db or draft_path()
    con = sqlite3.connect(p, timeout=30)
    con.executescript(SCHEMA_V141)
    con.commit()
    return con, p


def write_item(con, path, boxes):
    """
    Записать ОДИН разобранный файл в черновик (одна транзакция).

    ПИШЕМ ВСЁ, что вернул сканер (закон: ничего не отбрасывать).
    """
    if not boxes:
        return 0
    pp = path_parts(path)
    m = pp["model"]
    n = 0

    # --- ИЗДЕЛИЕ (уникальность: «модель в папке») ---
    con.execute("INSERT OR IGNORE INTO items(item_key,model,folder,n_files,n_versions,exts,last_mtime) "
                "VALUES (?,?,?,0,0,'',0)", (pp["item_key"], m, pp["folder"]))
    # СЧИТАЕМ: файлов · УНИКАЛЬНЫХ расширений · УНИКАЛЬНЫХ версий
    con.execute("UPDATE items SET n_files=n_files+1 WHERE item_key=?", (pp["item_key"],))
    # exts: без дублей (проверяем, есть ли уже)
    row = con.execute("SELECT exts FROM items WHERE item_key=?", (pp["item_key"],)).fetchone()
    cur_exts = (row[0] or "") if row else ""
    if ("," + pp["ext"] + ",") not in ("," + cur_exts):
        con.execute("UPDATE items SET exts=exts||?||',' WHERE item_key=?",
                    (pp["ext"], pp["item_key"]))
    # версии: считаем уникальные (таблица item_ver)
    if pp["version"] is not None:
        con.execute("INSERT OR IGNORE INTO item_ver(item_key,version,ext) VALUES (?,?,?)",
                    (pp["item_key"], pp["version"], pp["ext"]))
        nv = con.execute("SELECT COUNT(DISTINCT version) FROM item_ver WHERE item_key=?",
                         (pp["item_key"],)).fetchone()[0]
        con.execute("UPDATE items SET n_versions=? WHERE item_key=?", (nv, pp["item_key"]))
    n += 1

    # --- ТЕЛА (у каждого свои volume/density/mass) ---
    # ⚠️ ЗАМЕР: `gen_mass_prop_data` бывает и БЕЗ данных (vol=None) — это СХЕМА, не тело.
    #    Пишем ТОЛЬКО записи С ДАННЫМИ (пустая = данных нет — это ФАКТ, не «фильтр мусора»).
    for t in boxes.get("bodies") or []:
        if t.get("volume") is None and t.get("mass") is None:
            continue                       # данных нет — писать нечего
        con.execute("INSERT INTO bodies(path,model,folder,version,body_id,seq,volume,density,"
                    "surfarea,mass) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (path, m, pp["folder"], pp["version"], t.get("body_id"), t.get("seq"),
                     t.get("volume"), t.get("density"), t.get("surfarea"), t.get("mass")))
        n += 1

    # --- МАТЕРИАЛЫ: карточки (из master_mat.materials) ---
    mm = boxes.get("master_mat") or {}
    for mat in mm.get("materials") or []:
        con.execute("INSERT INTO materials(path,model,name,description,n_props,system) "
                    "VALUES (?,?,?,?,?,?)",
                    (path, m, mat.get("name"), mat.get("description"), mat.get("n_props"), 0))
        n += 1
    # МАТЕРИАЛЫ из extract_materials (системный — ПОМЕЧАЕМ, не отбрасываем!)
    for mat in boxes.get("materials") or []:
        con.execute("INSERT INTO materials(path,model,name,description,n_props,system) "
                    "VALUES (?,?,?,?,?,?)",
                    (path, m, mat.get("name"), mat.get("description"),
                     mat.get("n_props"), 1 if mat.get("system") else 0))
        n += 1

    # --- МАСТЕР-МАТЕРИАЛ (один на деталь) ---
    con.execute("INSERT OR REPLACE INTO master_mat"
                "(path,model,current_material,master_name,reported_name,has_master) "
                "VALUES (?,?,?,?,?,?)",
                (path, m, mm.get("current_material"), mm.get("master_name"),
                 mm.get("reported_name"), 1 if mm.get("has_master") else 0))
    n += 1

    # --- ИНСТРУМЕНТЫ (.mfg) ---
    for t in boxes.get("tools") or []:
        con.execute("INSERT INTO tools(path,model,tool_id,n_params,assem) VALUES (?,?,?,?,?)",
                    (path, m, t.get("tool_id"), t.get("n_params"), t.get("assem")))
        n += 1

    # --- ВСЕ номиналы размеров ---
    for d in boxes.get("dimensions") or []:
        for i, nom in enumerate(d.get("nominals_all") or []):
            con.execute("INSERT INTO dim_all(path,model,feat_id,nominal,idx) VALUES (?,?,?,?,?)",
                        (path, m, d.get("feat_id"), nom, i))
            n += 1

    # --- «НЕ ИЗУЧЕНО» (закон!) ---
    for name, cnt in (boxes.get("unknown_fields") or {}).items():
        con.execute("INSERT INTO unknown_fields(path,model,name,count) VALUES (?,?,?,?)",
                    (path, m, name, cnt))
        n += 1

    # --- МАТРИЦЫ / ГАБАРИТЫ (§181) ---
    import json as _json
    for mx in boxes.get("matrices") or []:
        con.execute("INSERT INTO matrices(path,model,field,dims,vals) VALUES (?,?,?,?,?)",
                    (path, m, mx.get("field"), _json.dumps(mx.get("dims")),
                     _json.dumps(mx.get("values"))))
        n += 1

    # --- ЧЕРТЁЖ (.drw) ---
    dr = boxes.get("drawing") or {}
    if dr and pp["ext"] == "drw":   # ТОЛЬКО для чертежей!
        con.execute("INSERT OR REPLACE INTO drawing"
                    "(path,model,source_models,states,uniq_name,sheet_size) "
                    "VALUES (?,?,?,?,?,?)",
                    (path, m, _json.dumps(dr.get("source_models")),
                     _json.dumps(dr.get("states")), dr.get("uniq_name"),
                     dr.get("sheet_size")))
        n += 1

    # --- СОСТАВ СБОРКИ (компоненты) ---
    for c in (boxes.get("links") or {}).get("components") or []:
        con.execute("INSERT INTO components(path,model,comp,count,kind) VALUES (?,?,?,?,?)",
                    (path, m, c.get("name"), c.get("count"), "model_ref"))
        n += 1

    # --- ЗДОРОВЬЕ ---
    h = boxes.get("health") or {}
    if h:
        con.execute("INSERT OR REPLACE INTO health(path,model,regen,reg_status,inactive) "
                    "VALUES (?,?,?,?,?)",
                    (path, m, h.get("regen"), h.get("reg_status"),
                     int(h.get("inactive") or 0)))
        n += 1

    con.commit()
    return n


def write_folder(folder, limit=100):
    """Прочитать папку сканером → записать в ЧЕРНОВИК."""
    import scanner_plm as S
    con, draft = open_draft()
    files = []
    for dp, _, fs in os.walk(folder):
        for f in fs:
            if f.lower().endswith((".prt.1", ".asm.1", ".drw.1", ".mfg.1")):
                files.append(os.path.join(dp, f))
        if len(files) >= limit * 3:
            break
    files = files[:limit]
    t0 = time.perf_counter()
    ok = rows = 0
    for p in files:
        try:
            b = S.scan_item_new(p, S.FEATTYPE)
            rows += write_item(con, p, b)
            ok += 1
        except Exception as ex:
            print("  ОШИБКА:", os.path.basename(p), str(ex)[:80])
    dt = time.perf_counter() - t0
    con.close()
    return draft, {"files": ok, "rows": rows, "sec": round(dt, 2)}


if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else r"Z:\PTC\Work\001_15 ЦТКД Электон"
    draft, st = write_folder(root, 30)
    print(f"ЧЕРНОВИК: {draft}")
    print(f"  файлов: {st['files']} · строк: {st['rows']} · время: {st['sec']} с")
    con = sqlite3.connect(draft)
    for t in ("items", "bodies", "materials", "master_mat", "tools", "dim_all", "unknown_fields",
              "matrices", "drawing", "components", "health"):
        n = con.execute("SELECT COUNT(*) FROM [%s]" % t).fetchone()[0]
        print(f"  {t:<16} {n}")
    print("\nПРИМЕР (bodies):")
    for r in con.execute("SELECT model,body_id,volume,mass FROM bodies LIMIT 5"):
        print("   ", r)
    print("ПРИМЕР (materials):")
    for r in con.execute("SELECT model,name,description,n_props FROM materials LIMIT 5"):
        print("   ", r)
    print("ПРИМЕР (master_mat):")
    for r in con.execute("SELECT model,current_material,has_master FROM master_mat LIMIT 5"):
        print("   ", r)
    print("ТОП-10 «НЕ ИЗУЧЕНО»:")
    for r in con.execute("SELECT name,SUM(count) c FROM unknown_fields "
                         "GROUP BY name ORDER BY c DESC LIMIT 10"):
        print("   ", r)
    con.close()
