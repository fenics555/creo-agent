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
    "purge_backup_dir": "",  # V99: куда класть старые версии Purge (пусто = <папка>\_purge_backup\ГГГГММДД)
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
    # --- V100: PDM-Консоль (HTML-граф). ПРАВИЛО ДОМА: ничего не зашивать в код — всё здесь.
    "graph_depth": 3,          # на сколько уровней строить граф (вниз/вверх от выбранного)
    "graph_nodes_max": 120,    # предел узлов на графе (защита от «хаба» на 1000 детей)
    "graph_children_max": 25,  # сколько связей брать у одного узла
    "graph_list_max": 800,     # сколько строк списка показывать
    "graph_links_max": 120,    # сколько связей показывать в карточке
    "graph_card_h": 230,       # высота верхнего окна (КАРТОЧКА), px
    "graph_thumb": 40,         # размер миниатюры в списке, px
    "graph_media": True,       # собирать превью (SHA-256 дедупликация)
    # ЧТО ПОКАЗЫВАТЬ: "auto" — по типу файла (.prt/.asm картинка, .drw чертёж);
    #                 "pict" — всегда картинку модели (JPEG); "draw" — всегда чертёж (BMP);
    #                 "none" — без изображений
    "graph_image_mode": "auto",
    # V104: 12000 → 60000. На боевой базе 21 868 моделей СО СВЯЗЯМИ: при 12000 ~10 000 связанных
    # моделей вообще не попадали в страницу (владелец не находил их). Ленивые порции держат скорость.
    "graph_page_nodes": 60000,    # сколько узлов кладём в страницу (лениво, порциями)
    # V107: 25000 → 0 (без предела). Потолок оставлял 22 000 файлов БЕЗ картинок, хотя превью
    # в файлах есть (владелец: «вместо картинки 0»). Кэш инкрементальный — повторный прогон
    # дочитывает недостающее, уже собранное не перечитывает.
    "graph_media_limit": 0,       # предел числа собираемых превью за прогон (0 = без предела)
    "graph_scan_budget": 120,     # бюджет времени на чтение файлов, сек (сеть Z: — медленная)
    "graph_open_browser": True,  # открывать страницу в браузере после сборки
    # V103 (24.10.2026) ЛЕНИВАЯ ЗАГРУЗКА:
    "lazy_first_chunk": 1500,    # сколько строк списка показать СРАЗУ (остальное — в фоне)
    "graph_chunk_nodes": 1200,   # сколько узлов в одной порции данных для HTML-страницы
    # V111: КАК РАСКЛАДЫВАТЬ СВЯЗИ В КАРТОЧКЕ (запрос владельца: «сохрани горизонтальный строй,
    # хочется и вертикальный»):
    #   "row" — ВАРИАНТ 1: Состав / Куда входит / История — ТРИ КОЛОНКИ В РЯД (горизонтально);
    #   "col" — ВАРИАНТ 2: те же блоки ДРУГ ПОД ДРУГОМ (вертикально), удобно на узком экране.
    "graph_card_layout": "row",
    # V112: КАК РАСКЛАДЫВАТЬ САМ ГРАФ (запрос владельца: «не нашёл настройку, чтобы граф/связи
    # строились не в горизонталь, а в вертикаль»). Речь об ОТОБРАЖЕНИИ:
    #   "row" — уровни идут СЛЕВА НАПРАВО (горизонтальный строй, текущий вид);
    #   "col" — уровни идут СВЕРХУ ВНИЗ (вертикальный строй), узлы уровня — в ряд.
    "graph_graph_layout": "row",
    # V120 (26.10.2026) ГРАБЛЯ (владелец: «библиотечные файлы не выдаёт HTML страница»):
    # фильтр страницы требовал «есть связь ИЛИ превью», и модели-ЭТАЛОНЫ библиотеки (на них
    # никто не ссылается — `links` пусто) навсегда выпадали из страницы: 333 из 618.
    # True — показывать «одиночек» из папок библиотек (и модели с превью без связей).
    "graph_show_loose": True,
}

# ═══════════════ V107: ЕДИНЫЙ РЕЕСТР НАСТРОЕК (ОДНО место для ВСЕХ) ═══════════════
# Владелец: «все настройки должны быть вместе в одном месте и иметь возможность настраиваться;
# в коде настройки — ошибка». Здесь описан КАЖДЫЙ параметр: ключ, подпись, тип, границы, группа.
# Из этого реестра строятся ОБА интерфейса: окно «⚙ НАСТРОЙКИ…» и панель «НАСТРОЙКИ» в HTML.
# Добавил параметр здесь — он появится и в окне, и в HTML, и в settings.json (см. DEFAULT_SETTINGS).
# type: "int" | "bool" | "text" | "list" | "choice"
SETTINGS_SPEC = [
    # --- группа: СКАН ---
    ("СКАН", "max_size_mb", "макс. размер файла, МБ", "int", 0, 1000),
    ("СКАН", "recurse", "читать подпапки", "bool", None, None),
    ("СКАН", "latest_only", "только последние версии", "bool", None, None),
    ("СКАН", "depth", "глубина подпапок (0 = все)", "int", 0, 50),
    ("СКАН", "full", "перечитать всё (полный скан)", "bool", None, None),
    ("СКАН", "auto_refresh", "автообновление при новой базе", "bool", None, None),
    ("СКАН", "show_limit", "строк в списке за раз", "int", 100, 1000000),
    ("СКАН", "purge_keep", "сколько версий оставлять (Purge)", "int", 0, 100),
    # --- группа: ПОКАЗ ---
    # V113: СТРОЙ — ПЕРВЫМ ДЕЛОМ (владелец не находил настройку: она была В КОНЦЕ списка,
    # а панель прокручивается — «не нашёл переключение горизонтальная связь или вертикальная»).
    # Подписи явные, по-русски: «горизонтально / вертикально».
    ("ПОКАЗ", "graph_graph_layout", "СТРОЙ ГРАФА: горизонтально (слева-направо) / вертикально (сверху-вниз)",
     "choice", ["row", "col"], None),
    ("ПОКАЗ", "graph_card_layout", "СТРОЙ СВЯЗЕЙ: горизонтально (в ряд) / вертикально (друг под другом)",
     "choice", ["row", "col"], None),
    ("ПОКАЗ", "graph_depth", "граф: уровней вглубь/вверх", "int", 1, 12),
    ("ПОКАЗ", "graph_nodes_max", "граф: узлов на экране", "int", 20, 20000),
    ("ПОКАЗ", "graph_children_max", "граф: связей у узла", "int", 1, 1000),
    ("ПОКАЗ", "graph_list_max", "граф: строк в списке", "int", 50, 100000),
    ("ПОКАЗ", "graph_links_max", "граф: связей в карточке", "int", 5, 10000),
    ("ПОКАЗ", "graph_card_h", "граф: высота карточки, px", "int", 80, 2000),
    ("ПОКАЗ", "graph_thumb", "граф: миниатюра, px", "int", 16, 200),
    ("ПОКАЗ", "graph_page_nodes", "HTML: узлов на странице", "int", 100, 200000),
    ("ПОКАЗ", "graph_chunk_nodes", "HTML: узлов в порции (лениво)", "int", 100, 50000),
    ("ПОКАЗ", "lazy_first_chunk", "HTML: строк сразу при старте", "int", 100, 100000),
    ("ПОКАЗ", "graph_open_browser", "HTML: открывать браузер", "bool", None, None),
    # V120: библиотечные модели-эталоны не входят ни в одну сборку — раньше выпадали из страницы.
    ("ПОКАЗ", "graph_show_loose", "HTML: показывать одиночек (библиотека без связей)", "bool",
     None, None),
    # --- группа: ПРЕВЬЮ ---
    ("ПРЕВЬЮ", "graph_media", "собирать превью (картинка+чертёж)", "bool", None, None),
    ("ПРЕВЬЮ", "graph_image_mode", "что показывать", "choice",
     ["auto", "pict", "draw", "none"], None),
    ("ПРЕВЬЮ", "graph_media_limit", "предел превью за прогон (0 = без предела)", "int", 0, 500000),
    ("ПРЕВЬЮ", "graph_scan_budget", "бюджет чтения превью, сек", "int", 1, 3600),
    # --- группа: БАЗА ---
    ("БАЗА", "db_dir", "папка базы (пусто = рядом)", "text", None, None),
    ("БАЗА", "purge_backup_dir", "куда класть бэкап Purge", "text", None, None),
    ("БАЗА", "mirror_keep", "свежих баз в зеркале", "int", 1, 50),
    ("БАЗА", "mirror_full_only", "зеркалить только после полного скана", "bool", None, None),
]


def settings_spec_json():
    """Реестр настроек для HTML-панели «НАСТРОЙКИ» (одно место — два интерфейса)."""
    return [{"group": g, "key": k, "label": lab, "type": t, "lo": lo, "hi": hi}
            for (g, k, lab, t, lo, hi) in SETTINGS_SPEC]


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
    """Мягкая проверка типов: что не число — умолчание + строка в лог (битый файл не роняет окно).

    V116 ГЛАВНАЯ ГРАБЛЯ: проверялись только 4 ключа, а настройки графа — НЕТ. На шаре в файле
    лежало `"graph_media_limit": "25000"` (СТРОКА, старый формат) → `int("25000")` = 25000 →
    включался ЖЁСТКИЙ ПОТОЛОК 25 000 превью (хотя в коде стоит 0 = без предела), и 8 494 файла
    оставались без картинок. Теперь нормализация идёт ПО ВСЕМУ РЕЕСТРУ `SETTINGS_SPEC`:
    строка «25000» → число 25000, «true» → True, и т.д.
    """
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

    # V116: нормализуем ВСЕ параметры по единому реестру (тип из SETTINGS_SPEC).
    try:
        spec = SETTINGS_SPEC
    except NameError:
        spec = []
    for item in spec:
        try:
            key, typ = item[1], item[3]
        except Exception:
            continue
        if key in ("db_dir", "purge_backup_dir") or typ in ("text", "list"):
            continue
        val = out.get(key)
        if typ == "int":
            try:
                out[key] = int(float(str(val).replace(",", ".")))
            except Exception:
                out[key] = DEFAULT_SETTINGS.get(key, 0)
                log_line("settings: «%s» не число (%r) — умолчание" % (key, val))
        elif typ == "bool":
            if isinstance(val, str):
                out[key] = val.strip().lower() in ("1", "true", "да", "yes", "on")
            else:
                out[key] = bool(val)
        elif typ == "choice":
            allowed = item[4] if len(item) > 4 and isinstance(item[4], list) else None
            if allowed and str(val) not in allowed:
                out[key] = DEFAULT_SETTINGS.get(key, allowed[0])
                log_line("settings: «%s»=%r не из списка — умолчание" % (key, val))
            else:
                out[key] = str(val)

    # V116: ЛЕЧИМ УСТАРЕВШИЙ ПОТОЛОК ПРЕВЬЮ. В файлах осталось `graph_media_limit=25000`
    # (умолчание до V107) — оно МОЛЧА возвращает жёсткий потолок, и «хвост» базы остаётся без
    # картинок: на шаре так остались 8 494 модели БЕЗ превью, хотя превью в файлах ЕСТЬ.
    # Теперь это значение переводится в 0 = без предела (как и задумано в V107).
    try:
        if int(out.get("graph_media_limit") or 0) == 25000:
            out["graph_media_limit"] = 0
            log_line("settings: graph_media_limit 25000 (устаревший потолок) → 0 (без предела)")
    except Exception:
        pass
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
