# -*- coding: utf-8 -*-
"""plm_settings.py — настройки, миграции, пути."""
import os
import json
import datetime
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "db")
CACHE_FILE = os.path.join(DATA_DIR, "scan_cache.json")
DB_FILE = os.path.join(DATA_DIR, "plm_reader.db")

SETTINGS_DIR = os.path.join(HERE, "settings")
SETTINGS_FILE = os.path.join(SETTINGS_DIR, "settings.json")
LOG_DIR = os.path.join(HERE, "log")
REPORTS_DIR = os.path.join(LOG_DIR, "reports")

CURRENT_SETTINGS_VERSION = 3

DEFAULT_SETTINGS = {
    "max_size_mb": 24,
    "recurse": True,
    "latest_only": True,
    "depth": 0,
    "purge_keep": 2,
    "auto_refresh": True,
    "full": False,
    "columns": ["Файл", "Обозначение", "Наименование", "Материал", "Объём, мм\u00b3",
                "Роль", "Родитель", "Ревизия", "Записей", "Версий", "Дата",
                "Создан", "Изменён", "Пользователь", "Версия Creo"],
    "param_designation": ["ОБОЗНАЧЕНИЕ", "OBOZNACHENIE", "DESIGNATION", "DESIGNATOR", "PART_NUMBER"],
    "param_name": ["НАИМЕНОВАНИЕ", "NAME", "PART_NAME", "DESCRIPTION", "TITLE"],
    "param_material": ["PTC_MASTER_MATERIAL", "MATERIAL", "МАТЕРИАЛ"],
    "folders": [],
}

def log_line(text):
    """Одна строка в общий лог инструмента: D:\\AI\\log\\plm_reader\\plm_reader.log."""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(os.path.join(LOG_DIR, "plm_reader.log"), "a", encoding="utf-8") as f:
            f.write("%s  %s\\n" % (datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"), text))
    except Exception:
        pass

def norm_path(s):
    """Привести вставленный путь к рабочему виду: убрать кавычки/пробелы по краям,
    заменить прямые слэши, отбросить хвостовой слэш; если вставлен файл — взять его папку."""
    s = (s or "").strip().strip('"').strip("'").strip("«»").strip()
    s = s.replace("/", "\\")
    while len(s) > 3 and s.endswith("\\"):
        s = s[:-1]
    if s and os.path.isfile(s):
        s = os.path.dirname(s)
    return s

def _settings_migrations():
    def v1_to_v2(d):
        if not d.get("folders"):
            legacy = []
            if d.get("folder"): legacy.append(d["folder"])
            if d.get("folder2") and d["folder2"] not in legacy: legacy.append(d["folder2"])
            if legacy: d["folders"] = legacy
            d.pop("folder", None); d.pop("folder2", None)
        return d
    def v2_to_v3(d):
        d["db_dir"] = (d.get("db_dir") or "").strip() if isinstance(d.get("db_dir"), str) else ""
        raw = d.get("db_mirror")
        if isinstance(raw, str): raw = [x.strip() for x in raw.split(";") if x.strip()]
        if not isinstance(raw, list): raw = []
        out, seen = [], set()
        for p in raw:
            if isinstance(p, str) and p.strip():
                v = norm_path(p.strip())
                if v.lower() not in seen:
                    seen.add(v.lower()); out.append(v)
        d["db_mirror"] = out
        return d
    return {2: v1_to_v2, 3: v2_to_v3}

def _validate_settings(out):
    def _num(key, caster, fallback):
        try: out[key] = caster(out.get(key, fallback))
        except Exception: out[key] = fallback; log_line("settings: ключ «%s» не число — беру умолчание" % key)
    _num("max_size_mb", float, 24)
    _num("show_limit", int, 50000)
    _num("depth", int, 0)
    _num("purge_keep", int, 2)
    return out

def _rotate_settings_backups(keep=5):
    try:
        bak_dir = os.path.join(SETTINGS_DIR, "backup_settings")
        if not os.path.isdir(bak_dir): return 0
        files = sorted(f for f in os.listdir(bak_dir) if f.endswith(".json"))
        removed = 0
        for old in files[:max(0, len(files) - keep)]:
            try: os.remove(os.path.join(bak_dir, old)); removed += 1
            except Exception: pass
        return removed
    except Exception: return 0



def _archive_old_settings(src):
    try:
        import shutil
        bak_dir = os.path.join(SETTINGS_DIR, "backup_settings")
        os.makedirs(bak_dir, exist_ok=True)
        where = "root" if os.path.dirname(os.path.abspath(src)) == os.path.dirname(os.path.abspath(__file__)) else "db"
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = os.path.join(bak_dir, "settings_from_%s_%s.json" % (where, stamp))
        shutil.move(src, dst)
        _rotate_settings_backups()
    except Exception: pass

def load_settings_file(path=None):
    path = path or SETTINGS_FILE
    src, is_old = "", False
    candidates = [path]
    if path == SETTINGS_FILE:
        candidates.append(os.path.join(HERE, "db", "settings.json"))
        candidates.append(os.path.join(HERE, "settings.json"))
    for c in candidates:
        if os.path.isfile(c):
            src = c
            is_old = (os.path.abspath(c) != os.path.abspath(SETTINGS_FILE))
            break
    out = dict(DEFAULT_SETTINGS)
    try:
        if src:
            with open(src, encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict): out.update(data)
    except Exception as e:
        log_line("settings: чтение не удалось (%s) — работаю на умолчаниях" % e)
    try: v = int(out.get("settings_version", 1))
    except Exception: v = 1
    migs = _settings_migrations()
    while v < CURRENT_SETTINGS_VERSION:
        v += 1
        if v in migs:
            out = migs[v](out)
            log_line("settings: миграция до версии %d (источник %s)" % (v, src or "умолчания"))
    out["settings_version"] = CURRENT_SETTINGS_VERSION
    out = _validate_settings(out)
    if is_old and src: save_settings_file(out)
    for c in candidates:
        if os.path.isfile(c) and os.path.abspath(c) != os.path.abspath(SETTINGS_FILE):
            _archive_old_settings(c)
    return out

def save_settings_file(settings, path=None):
    path = path or SETTINGS_FILE
    tmp = path + ".tmp"
    try:
        out = dict(settings)
        out.pop("folder", None); out.pop("folder2", None)
        out["settings_version"] = CURRENT_SETTINGS_VERSION
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        return True
    except Exception as e:
        log_line("settings: НЕ СОХРАНЕНО (%s): %s" % (path, e))
        try:
            if os.path.isfile(tmp): os.remove(tmp)
        except Exception: pass
        return False

def apply_db_paths(settings, eng, current_data_dir):
    db_dir = (settings.get("db_dir") or "").strip()
    mir = settings.get("db_mirror") or []
    if not isinstance(mir, list): mir = []
    mir = [norm_path(x) for x in mir if isinstance(x, str) and x.strip()]
    new_data_dir = current_data_dir
    new_cache_file = os.path.join(current_data_dir, "scan_cache.json")
    new_db_file = os.path.join(current_data_dir, "plm_reader.db")
    if db_dir:
        new_dir = os.path.abspath(db_dir)
        new_data_dir = new_dir
        new_cache_file = os.path.join(new_dir, "scan_cache.json")
        new_db_file = os.path.join(new_dir, "plm_reader.db")
        try: eng.set_base_dir(new_dir)
        except Exception as e: log_line("база: не удалось увести базу в %s (%s)" % (new_dir, e))
        import shutil as _sh
        old_dir = current_data_dir
        if old_dir and os.path.normcase(old_dir) != os.path.normcase(new_dir):
            try:
                have = [f for f in os.listdir(new_dir) if f.endswith(".db")] if os.path.isdir(new_dir) else []
                if not have:
                    src = None
                    if os.path.isdir(old_dir):
                        ver = sorted(f for f in os.listdir(old_dir) if re.match(r"^plm_reader_\d{8}_\d{6}\.db$", f))
                        if ver: src = os.path.join(old_dir, ver[-1])
                        elif os.path.isfile(os.path.join(old_dir, "plm_reader.db")): src = os.path.join(old_dir, "plm_reader.db")
                    if src:
                        os.makedirs(new_dir, exist_ok=True)
                        _sh.copy2(src, os.path.join(new_dir, os.path.basename(src)))
                        log_line("база: перенесена копией на %s (%s)" % (new_dir, os.path.basename(src)))
                    else:
                        log_line("база: в %s пусто — наполнится после скана" % new_dir)
                else:
                    log_line("база: в %s уже есть файлы — оставляем как есть" % new_dir)
            except Exception as e:
                log_line("база: перенос на %s не удался (%s) — наполнится после скана" % (new_dir, e))
    try: os.makedirs(new_data_dir, exist_ok=True)
    except Exception: pass
    return new_data_dir, new_cache_file, new_db_file, mir

def path_under(path, roots):
    """Путь внутри одного из корней (без учёта регистра, по границам папок).
    roots — путь ИЛИ список путей; безопасно к кривым строкам."""
    if isinstance(roots, str):
        roots = [roots]
    try:
        p = os.path.normcase(os.path.abspath(path))
    except Exception:
        return False
    for r in roots or []:
        try:
            rn = os.path.normcase(os.path.abspath(r)).rstrip("\\/")
        except Exception:
            continue
        if not rn:
            continue
        if p == rn or p.startswith(rn + "\\"):
            return True
    return False

def roots_of(folder, folder2=""):
    """Корни окна: основная папка + «Папка2» — только существующие, без дублей."""
    out = []
    for x in (folder, folder2):
        x = norm_path(x) if x else ""
        if x and x not in out:
            out.append(x)
    return out
