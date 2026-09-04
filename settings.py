# -*- coding: utf-8 -*-
r"""
ТРАНСФОРМЕР v12 — НАСТРОЙКИ (settings.py)
Единственный хозяин config.json. Только ресурсы, ноль поведения.
"""
import json

from core import log, CONFIG_FILE, DATA_DIR

REGISTRY = [
    ("Главное", "llm_model", "Модель чата", "str", "deepseek-r1:14b", "Какая модель думает.", True),
    ("Главное", "creativity", "Креатив 0-100", "int", 40, "0-34 строго, 35-66 нейтрально, 67-100 свободно.", True),
    ("Главное", "auto_temperature", "Температура авто 0–100", "int", 10, "10 = 0.10 — инженерная строгость, без выдумывания.", True),
    ("Главное", "top_p", "Top-p", "float", 0.9, "Разнообразие.", False),
    ("Главное", "num_ctx", "Окно контекста", "int", 8192, "Под <think> рассуждения.", True),
    ("Главное", "num_predict", "Макс токенов ответа", "int", 2048, "Чтобы не резало мысли.", True),
    ("Главное", "admin_password", "Пароль обучения", "str", "1945", "Для админ-действий.", True),
    ("Главное", "auto_mode", "Авторежим", "bool", True, "Вкл: температура 0.1 (инженер). Выкл: температура от креатива.", True),
    ("Главное", "stream_tokens", "Стриминг токенов", "bool", True, "Печатать ответ по токенам по мере генерации.", True),
    ("Флот", "fleet_autocommit", "Авто-коммит решений", "bool", False, "Коммитить новые скиллы/кейсы в creo-repo автоматически.", True),
    ("Расписание", "night_enable", "Ночной прогон", "bool", True, "Автопрогон тяжёлых задач ночью.", True),
    ("Расписание", "night_hour", "Час прогона", "int", 2, "0-23.", True),
    ("Расписание", "night_minute", "Минута прогона", "int", 0, "0-59.", True),
    ("Расписание", "night_tasks", "Задачи ночи", "str", "scan,index,usage", "scan/index/usage/backup через запятую.", True),
    ("Главное", "parallel_tools", "Параллельные инструменты", "bool", False, "Несколько [TOOL] за ход — в потоках.", True),
    ("Главное", "stream_ui", "Стриминг в веб", "bool", False, "Токены в чат по мере генерации.", True),
    ("Главное", "log_mode", "Режим логов 0-3", "int", 1, "0 авто / 1 авто+токены / 2 отладка / 3 полный.", True),
    ("Разум", "log_days", "Дней хранить лог", "int", 14, "Автоочистка логов.", True),
    ("Разум", "verbose_trace", "Подробный trace", "bool", False, "Сырые JSON в trace-файл.", False),
    ("Поиск", "repo_boost", "Буст репозитория", "float", 1.2, "Умножение схожести для repo.", True),
    ("Поиск", "repo_boost_min_sim", "Порог буста", "float", 0.2, "Мин схожесть для буста.", False),
    ("Поиск", "top_chunks", "Топ чанков", "int", 4, "Сколько фрагментов видит модель.", True),
    ("Поиск", "chunk_chars", "Символов в чанке", "int", 900, "Длина фрагмента.", True),
    ("Поиск", "chunk_size", "Размер чанка", "int", 1500, "Нарезка при индексе.", False),
    ("Поиск", "chunk_overlap", "Перекрытие", "int", 200, "Зона перекрытия.", False),
    ("Визия", "vision_backend", "Бэкенд визии", "str", "ollama", "ollama / llamacpp.", True),
    ("Визия", "vision_url", "URL llamacpp", "str", "http://127.0.0.1:8081", "Адрес llama-server.", True),
    ("Визия", "vision_model", "Модель визии", "str", "qwen2-vl:7b", "Vision-модель Ollama.", True),
    ("Визия", "vision_gpu", "GPU-слоёв", "int", 0, "Слоёв на GPU.", False),
    ("Визия", "image_days", "Хранить скрины дней", "int", 7, "Срок хранения.", True),
    ("Creo", "copy_port", "Порт копии", "int", 8000, "Сервер страницы «Копия сборки».", True),
    ("Creo", "audit_limit", "Лимит аудита", "int", 20, "Моделей за аудит.", True),
    ("Creo", "audit_params", "Параметры аудита", "list", ["ОБОЗНАЧЕНИЕ", "НАИМЕНОВАНИЕ", "MASS"], "Что требуем от модели.", True),
    ("Память", "history_days", "Дней хранить историю", "int", 365, "Автоочистка истории.", False),
    ("Память", "client_days", "Дней хранить сессии", "int", 365, "Автоочистка клиентов.", False),
    ("Сканер", "max_file_mb", "Макс файл МБ", "int", 4, "Крупнее — не индексируем.", True),
    ("Сканер", "retention", "Глубина бэкапов", "int", 7, "Копий базы храним.", True),
    ("Web", "web_quick_links", "Бегло: ссылочных страниц", "int", 10, "Беглый проход: сколько ссылок читать.", True),
    ("Web", "web_deep_pages", "Глубоко: страниц", "int", 50, "Глубокий проход: предел страниц.", True),
    ("Web", "web_jina_key", "Ключ r.jina.ai", "str", "", "Если есть ключ — прокси оживает.", True),
    ("Web", "web_render", "Рендер браузером (Playwright)", "bool", False, "Вкл: при сбое fetch — headless Chrome.", True),
    ("Web", "web_test_url", "URL для diag_web", "str", "https://ya.ru", "Внешняя цель для diag_web.", True),
    ("Пути", "creoson_url", "URL CREOSON", "str", "http://127.0.0.1:8080/creoson", "Мост Creo.", True),
    ("Пути", "creoson_dir", "Папка CREOSON", "str", r"D:\AI\creoson\CreosonServer-3.0.2-win64", "Где creoson_run.bat.", True),
    ("Пути", "pdf_out", "Папка PDF", "str", "", "Пусто = рядом с чертежом.", True),
    ("Пути", "backup_dir", "Папка бэкапов", "str", "", "Пусто = agent/data/backups.", True),
    ("Пути", "trail_dirs", "Папки трейлов", "list", [], "Пусто = trail_dir из Creo + CREO-LOCAL-SETUP.", True),
    ("Creo", "bom_sections", "Порядок разделов спецы", "list", ["Документация", "Комплексы", "Сборочные единицы", "Детали", "Стандартные изделия", "Прочие изделия", "Материалы", "Комплекты"], "Порядок ГОСТ-разделов.", True),
    ("Главное", "steps_max", "steps_max", "int", 6, "Из config.json (авто-регистрация).", True),
    ("Сканер", "scan_roots", "scan_roots", "list", ["D:\\PTC\\CREO12\\Creo 12.4.2.0\\creo_help_pma\\russian", "D:\\AI\\repo", "Z:\\PTC\\Work", "Z:\\PTC\\CREO-START"], "Из config.json (авто-регистрация).", True),
    ("Сканер", "scan_exclude", "scan_exclude", "list", [".git\\", "__pycache__\\", "node_modules\\", "venv\\", ".venv\\", "backup\\", "old\\", "temp\\", "tmp\\", "cache\\", ".idea\\", ".vscode\\", "Z:\\PTC\\Work\\000_03 401-LIT Литейное производство\\000_5 401-LIT-MO Модельная оснастка для литья\\000_10 СТОРОННИЕ РАЗРАБОТКИ\\", "Z:\\PTC\\Work\\УЧЕБА\\", "Z:\\PTC\\Work\\хуйня\\", "Thumbs.db", "desktop.ini", "*.tmp", "*.bak", "*~", "*.log", "*.sqlite", "*.db", "*.exe", "*.dll", "*.so", "*.o", "*.obj", "*.pyc", ".DS_Store"], "Из config.json (авто-регистрация).", True),
    ("ИИ-роли", "model_index", "Модель индексации", "str", "nomic-embed-text:latest", "Эмбеддинги, без чата.", True),
    ("ИИ-роли", "model_chat", "Модель чата", "str", "", "Пусто = llm_model.", True),
    ("ИИ-роли", "model_fast", "Модель рутины", "str", "qwen2.5-coder:7b", "Быстрые/простые ходы.", True),
    ("ИИ-роли", "model_creo", "Модель Creo", "str", "", "Пусто = llm_model.", False),
    ("ИИ-роли", "model_vision", "Модель визии", "str", "minicpm-v:8b", "Скриншоты/чертежи.", True),
    ("ИИ-роли", "model_spec", "Модель спец", "str", "", "Пусто = llm_model.", False),
    ("ИИ-роли", "model_trail", "Модель трейлов", "str", "qwen2.5-coder:7b", "Диагностика трейлов.", True),
    ("ИИ-роли", "model_web", "Модель веб", "str", "", "Пусто = llm_model.", False),
    ("ИИ-роли", "model_audit", "Модель аудита", "str", "", "Пусто = llm_model.", False),
]

def _ensure():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        d = {k: defl for _, k, _, _, defl, _, _ in REGISTRY}
        CONFIG_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        log("settings: сейф создан %s" % CONFIG_FILE)
_ensure()

def _raw():
    try: return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception: return {}

def get(key, default=None):
    d = _raw()
    if key in d: return d[key]
    for _, k, _, _, defl, _, _ in REGISTRY:
        if k == key: return defl
    return default

def set_val(key, value):
    d = _raw()
    for _, k, typ, _, _, _, _ in REGISTRY:
        if k == key:
            try:
                if typ == "bool": value = str(value).lower() in ("1", "true", "yes", "on", "да")
                elif typ == "int": value = int(value)
                elif typ == "float": value = float(value)
                elif typ == "list" and isinstance(value, str): value = [x.strip() for x in value.split(",") if x.strip()]
            except Exception: pass
            d[key] = value
    if key == "auto_mode" and str(value).lower() in ("1","true","yes","on","да"):  # auto_reset
        for _, k2, _, _, defl2, _, _ in REGISTRY:
            if k2 in ("creativity","auto_temperature","top_p","num_ctx","num_predict","steps_max"): d[k2] = defl2
    if key == "auto_mode" and str(value).lower() in ("1", "true", "yes", "on", "да"):
        for _, k2, _, _, defl2, _, _ in REGISTRY:
            if k2 in ("creativity", "auto_temperature", "top_p", "num_ctx", "num_predict", "steps_max"):
                d[k2] = defl2
    if key == "auto_mode" and str(value).lower() in ("1", "true", "yes", "on", "да"):
        for _, k2, _, _, defl2, _, _ in REGISTRY:
            if k2 in ("creativity", "auto_temperature", "top_p", "num_ctx", "num_predict", "steps_max"):
                d[k2] = defl2
            CONFIG_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            return True
    CONFIG_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return True

def show_all():
    d = _raw()
    out = []
    for space, k, name, typ, defl, desc, ui in REGISTRY:
        out.append("• [%s] %s = %s — %s" % (space, k, d.get(k, defl), desc))
    return "\n".join(out)

def list_ui():
    d = _raw()
    B = {"log_mode": (0,3,1), "night_hour": (0,23,1), "night_minute": (0,59,1), "log_mode": (0,3,1), "night_hour": (0,23,1), "night_minute": (0,59,1), "night_hour": (0, 23, 1), "night_minute": (0, 59, 1), "log_mode": (0, 3, 1), "creativity": (0, 100, 1), "auto_temperature": (0, 100, 1), "top_p": (0, 1, 0.05),
         "num_ctx": (1024, 32768, 1024), "num_predict": (256, 8192, 256),
         "log_days": (1, 365, 1), "image_days": (1, 60, 1), "history_days": (1, 365, 1),
         "client_days": (1, 365, 1), "top_chunks": (1, 12, 1), "chunk_chars": (200, 2000, 100),
         "chunk_size": (500, 4000, 250), "chunk_overlap": (0, 1000, 50),
         "repo_boost": (0.5, 3, 0.1), "repo_boost_min_sim": (0, 1, 0.05),
         "vision_gpu": (0, 64, 1), "max_file_mb": (1, 100, 1), "retention": (1, 30, 1),
         "audit_limit": (1, 100, 1), "steps_max": (1, 16, 1),
         "web_quick_links": (0, 100, 1), "web_deep_pages": (0, 200, 5)}
    out = []
    for space, k, name, typ, defl, desc, ui in REGISTRY:
        if not ui: continue
        v = d.get(k, defl)
        e = {"space": space, "key": k, "name": name, "type": typ, "value": v, "desc": desc}
        if typ in ("int", "float") and k in B:
            lo, hi, st = B[k]; e["min"], e["max"], e["step"] = lo, hi, st; e["kind"] = "range"
        elif typ == "bool": e["kind"] = "check"
        else: e["kind"] = "text"
        out.append(e)
    return out


def model_for(role):
    v = get("model_" + role)
    return v or get("llm_model")

PERSONAL_KEYS = []
PREF_FILE = DATA_DIR / "user_prefs.json"
def _prefs():
    try: return json.loads(PREF_FILE.read_text(encoding="utf-8"))
    except Exception: return {}
def get_for(login, key, default=None):
    return _prefs().get(login or "", {}).get(key, default)
def set_for(login, key, value):
    d = _prefs(); u = d.setdefault(login or "", {}); u[key] = value
    PREF_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return True
