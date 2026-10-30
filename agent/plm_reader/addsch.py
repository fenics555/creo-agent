import io
# 1) добавить схему доп.таблиц в engine.SCHEMA
P=r"engine.py"
t=io.open(P,encoding="utf-8",newline="").read()
if "CREATE TABLE IF NOT EXISTS items" not in t:
    add='''
-- [V141-ВРЕМЕННО] ДОП. ТАБЛИЦЫ нового сканера (удалить при переходе на scanner_write)
CREATE TABLE IF NOT EXISTS items (item_key TEXT PRIMARY KEY, model TEXT, folder TEXT,
  n_files INTEGER, n_versions INTEGER, exts TEXT, last_mtime REAL);
CREATE INDEX IF NOT EXISTS ix_items_model ON items(model);
CREATE TABLE IF NOT EXISTS item_ver (item_key TEXT, version INTEGER, ext TEXT,
  PRIMARY KEY(item_key, version, ext));
CREATE TABLE IF NOT EXISTS bodies (path TEXT, model TEXT, folder TEXT, version INTEGER,
  body_id INTEGER, seq INTEGER, volume REAL, density REAL, surfarea REAL, mass REAL);
CREATE INDEX IF NOT EXISTS ix_bodies_model ON bodies(model);
CREATE TABLE IF NOT EXISTS materials (path TEXT, model TEXT, name TEXT, description TEXT,
  n_props INTEGER, system INTEGER);
CREATE INDEX IF NOT EXISTS ix_mat_model ON materials(model);
CREATE TABLE IF NOT EXISTS master_mat (path TEXT PRIMARY KEY, model TEXT, current_material TEXT,
  master_name TEXT, reported_name TEXT, has_master INTEGER);
CREATE TABLE IF NOT EXISTS tools (path TEXT, model TEXT, tool_id TEXT, n_params INTEGER, assem TEXT);
CREATE TABLE IF NOT EXISTS unknown_fields (path TEXT, model TEXT, name TEXT, count INTEGER);
CREATE INDEX IF NOT EXISTS ix_uf_path ON unknown_fields(path);
CREATE TABLE IF NOT EXISTS dim_all (path TEXT, model TEXT, feat_id INTEGER, nominal REAL, idx INTEGER);
CREATE TABLE IF NOT EXISTS matrices (path TEXT, model TEXT, field TEXT, dims TEXT, vals TEXT);
CREATE TABLE IF NOT EXISTS drawing (path TEXT PRIMARY KEY, model TEXT, source_models TEXT,
  states TEXT, uniq_name TEXT, sheet_size TEXT);
CREATE TABLE IF NOT EXISTS components (path TEXT, model TEXT, comp TEXT, count INTEGER, kind TEXT);
'''
    # вставить перед закрывающими кавычками SCHEMA
    i=t.find('CREATE INDEX IF NOT EXISTS ix_health_model ON health(model);')
    j=t.find('"""', i)
    t=t[:j]+add+t[j:]
    io.open(P,"w",encoding="utf-8",newline="").write(t)
    print("engine.SCHEMA: +12 таблиц")
else: print("уже есть")
# 2) настройка scanner_extra
import json
sp=r"settings\settings.json"
d=json.load(io.open(sp,encoding="utf-8"))
if "scanner_extra" not in d:
    d["scanner_extra"]=True
    json.dump(d, io.open(sp,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
    print("+ scanner_extra = True")
else: print("scanner_extra:", d["scanner_extra"])
