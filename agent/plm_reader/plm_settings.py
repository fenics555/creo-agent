# -*- coding: utf-8 -*-
"""plm_settings.py — вынесено из plm_reader.py распилом (см. СПЕКА_РАСПИЛА_PLM_READER.md)."""
from plm_reader import (
    DATA_DIR,
    SETTINGS_DIR,
    SETTINGS_FILE,
    datetime,
    json,
    log_line,
    os,
    re,
)


CURRENT_SETTINGS_VERSION = 3   # увеличивать при КАЖДОМ структурном изменении настроек (см. _settings_migrations)
DEFAULT_SETTINGS = {
    "max_size_mb": 24,
    "recurse": True,
    "latest_only": True,
    "depth": 0,
    "purge_keep": 2,
    "auto_refresh": True,
    "full": False,
    "columns": ["Файл", "Обозначение", "Наименование", "Материал", "Объём, мм³",
                "Роль", "Родитель", "Ревизия", "Записей", "Версий", "Дата",
                "Создан", "Изменён", "Пользователь", "Версия Creo"],
    "param_designation": ["ОБОЗНАЧЕНИЕ", "OBOZNACHENIE", "DESIGNATION", "DESIGNATOR", "PART_NUMBER"],
    "param_name": ["НАИМЕНОВАНИЕ", "NAME", "PART_NAME", "DESCRIPTION", "TITLE"],
    "param_material": ["PTC_MASTER_MATERIAL", "MATERIAL", "МАТЕРИАЛ"],
    "folders": [],          # полный список папок сканирования (первые две = поля «Папка1»/«Папка2»)
    "exclude": [],          # папки-исключения: НЕ читать вовсе
    "db_dir": "",           # рабочая папка БАЗЫ (пусто = рядом, db\); можно увести на другой диск
    "db_mirror": [],        # папки-ЗЕРКАЛА базы: после каждого скана копия уезжает и туда
    "template_folders": [], # 07.10.2026: ПАПКИ шаблонов Creo — их модели служебные (не в связях)
    "service_models": [],   # 07.10.2026: явный список служебных стволов (если папка не намекает)
    "mirror_keep": 3,       # 07.10.2026: сколько свежих баз держать в КАЖДОМ зеркале
    "mirror_full_only": True,  # 07.10.2026: зеркалить только после ПОЛНОГО скана (не на каждый)
    "show_limit": 50000,    # сколько строк показывать за раз (крутилка на главной панели)
    "history_columns": ["Файл", "Путь", "Тип", "Ревизия", "Дата",
                        "Пользователь", "Компьютер", "Версия Creo", "Что изменено"],
}
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
def apply_db_paths(settings, eng):
    """Применить настройки базы ДО первого обращения к ней: рабочая папка + пути зеркал.

    Возвращает (рабочая папка, список зеркал). Пустой db_dir = база рядом, в `db\\`."""
    db_dir = (settings.get("db_dir") or "").strip()
    mir = settings.get("db_mirror") or []
    if not isinstance(mir, list):
        mir = []
    mir = [norm_path(x) for x in mir if isinstance(x, str) and x.strip()]
    if db_dir:
        # рабочая папка уводится на другой диск: и база, и кэш, и бэкапы, и замок
        new_dir = os.path.abspath(db_dir)
        old_dir = globals().get("DATA_DIR")
        globals()["DATA_DIR"] = new_dir
        globals()["CACHE_FILE"] = os.path.join(new_dir, "scan_cache.json")
        globals()["DB_FILE"] = os.path.join(new_dir, "plm_reader.db")
        try:
            eng.set_base_dir(new_dir)
        except Exception as e:
            log_line("база: не удалось увести базу в %s (%s)" % (new_dir, e))
        # база на новом месте есть? если нет — переносим туда свежайшую (КОПИЯ, не перемещение)
        if old_dir and os.path.normcase(old_dir) != os.path.normcase(new_dir):
            try:
                have = [f for f in os.listdir(new_dir) if f.endswith(".db")] if os.path.isdir(new_dir) else []
                if not have:
                    import shutil as _sh
                    src = None
                    if os.path.isdir(old_dir):
                        ver = sorted(f for f in os.listdir(old_dir)
                                     if re.match(r"^plm_reader_\d{8}_\d{6}\.db$", f))
                        if ver:
                            src = os.path.join(old_dir, ver[-1])
                        elif os.path.isfile(os.path.join(old_dir, "plm_reader.db")):
                            src = os.path.join(old_dir, "plm_reader.db")
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
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception:
        pass
    return DATA_DIR, mir
def _settings_migrations():
    """Цепочка миграций: {версия_назначения: функция(данные) -> данные}.
    Добавляй сюда шаг при КАЖДОМ структурном изменении (переименование/смена типа/смысла)."""
    def v1_to_v2(d):
        # v1: отдельные folder/folder2 -> v2: единый список folders
        if not d.get("folders"):
            legacy = []
            if d.get("folder"):
                legacy.append(d["folder"])
            if d.get("folder2") and d["folder2"] not in legacy:
                legacy.append(d["folder2"])
            if legacy:
                d["folders"] = legacy
        d.pop("folder", None)
        d.pop("folder2", None)
        return d
    def v2_to_v3(d):
        # v2 -> v3: путь рабочей папки базы (db_dir) и список зеркал (db_mirror).
        # Чужие/битые значения не роняют окно: приводим к строкам, мусор выбрасываем.
        d["db_dir"] = (d.get("db_dir") or "").strip() if isinstance(d.get("db_dir"), str) else ""
        raw = d.get("db_mirror")
        if isinstance(raw, str):
            raw = [x.strip() for x in raw.split(";")] if ";" in raw else [raw]
        if not isinstance(raw, list):
            raw = []
        out, seen = [], set()
        for p in raw:
            if isinstance(p, str) and p.strip():
                v = norm_path(p.strip())
                if v.lower() not in seen:
                    seen.add(v.lower())
                    out.append(v)
        d["db_mirror"] = out
        return d

    return {2: v1_to_v2, 3: v2_to_v3}
def _validate_settings(out):
    """Мягкая проверка типов: что не число — умолчание + строка в лог (битый файл не роняет окно)."""
    def _num(key, caster, fallback):
        try:
            out[key] = caster(out.get(key, fallback))
        except Exception:
            out[key] = fallback
            log_line("settings: ключ «%s» не число — беру умолчание" % key)
    _num("max_size_mb", float, 24)
    _num("show_limit", int, 50000)
    _num("depth", int, 0)
    _num("purge_keep", int, 2)
    return out
def _rotate_settings_backups(keep=5):
    """Оставить последние `keep` файлов в settings\\backup_settings; старые удалить."""
    try:
        bak_dir = os.path.join(SETTINGS_DIR, "backup_settings")
        if not os.path.isdir(bak_dir):
            return 0
        files = sorted(f for f in os.listdir(bak_dir) if f.endswith(".json"))
        removed = 0
        for old in files[:max(0, len(files) - keep)]:
            try:
                os.remove(os.path.join(bak_dir, old))
                removed += 1
            except Exception:
                pass
        return removed
    except Exception:
        return 0
def _archive_old_settings(src):
    """Старый файл настроек убираем в settings\\backup_settings\\ (не плодим файлы в корне)."""
    try:
        import shutil
        bak_dir = os.path.join(SETTINGS_DIR, "backup_settings")
        os.makedirs(bak_dir, exist_ok=True)
        where = "root" if os.path.dirname(os.path.abspath(src)) == os.path.dirname(os.path.abspath(__file__)) else "db"
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = os.path.join(bak_dir, "settings_from_%s_%s.json" % (where, stamp))
        shutil.move(src, dst)          # ПЕРЕНОС, а не копия
        _rotate_settings_backups()     # окно последних 5 (не копим бесконечно)
        log_line("settings: старый файл убран в %s" % dst)
        return dst
    except Exception as e:
        log_line("settings: не удалось убрать старый файл (%s): %s" % (src, e))
        return ""
def load_settings_file(path=None):
    r"""Настройки окна (файл в settings\). Битый файл не роняет окно — берём умолчания.
    Ищет по старшинству: settings\settings.json -> db\settings.json -> settings.json рядом;
    прогоняет цепочку миграций; старый файл убирает в settings\backup_settings\."""
    path = path or SETTINGS_FILE
    src, is_old = "", False
    candidates = [path]
    if path == SETTINGS_FILE:
        candidates.append(os.path.join(DATA_DIR, "settings.json"))
        candidates.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json"))
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
            if isinstance(data, dict):
                out.update(data)
    except Exception as e:
        log_line("settings: чтение не удалось (%s) — работаю на умолчаниях" % e)

    # Миграция структуры: от версии файла к текущей
    try:
        v = int(out.get("settings_version", 1))
    except Exception:
        v = 1
    migs = _settings_migrations()
    while v < CURRENT_SETTINGS_VERSION:
        v += 1
        if v in migs:
            out = migs[v](out)
            log_line("settings: миграция до версии %d (источник %s)" % (v, src or "умолчания"))
    out["settings_version"] = CURRENT_SETTINGS_VERSION
    out = _validate_settings(out)

    # Перенос из старого места: сохраняем в settings\
    if is_old and src:
        save_settings_file(out)
    # Подчистка: ЛЮБОЙ старый файл (кроме текущего settings\settings.json) уезжает в backup_settings\
    for c in candidates:
        if os.path.isfile(c) and os.path.abspath(c) != os.path.abspath(SETTINGS_FILE):
            _archive_old_settings(c)
    return out
def save_settings_file(settings, path=None):
    """Запись настроек: сначала во временный файл, потом замена (файл не бьётся при сбое).
    Ошибка пишется в лог, а не глотается молча."""
    path = path or SETTINGS_FILE
    tmp = path + ".tmp"
    try:
        out = dict(settings)
        out.pop("folder", None)      # единый источник — folders
        out.pop("folder2", None)
        out["settings_version"] = CURRENT_SETTINGS_VERSION
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
        return True
    except Exception as e:
        log_line("settings: НЕ СОХРАНЕНО (%s): %s" % (path, e))
        try:
            if os.path.isfile(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return False
