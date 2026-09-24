# -*- coding: utf-8 -*-
r"""
ТРАНСФОРМЕР v15 — НАСТРОЙКИ (settings.py)
Единственный хозяин config.json. Только ресурсы, ноль поведения.
"""
import json

from core import log, CONFIG_FILE, DATA_DIR

REGISTRY = [
    ("Главное", "llm_model", "Модель чата", "str", "gemma4:26b", "Какая модель думает.", True),
    ("Главное", "creativity", "Креатив 0-100 (когда авторежим ВЫКЛ)", "int", 40, "0-34 строго, 35-66 нейтрально, 67-100 свободно. Значение хранится отдельно: переключение авторежима его НЕ сбрасывает.", True),
    ("Главное", "auto_temperature", "Температура при АВТОРЕЖИМЕ 0-100", "int", 10, "10 = 0.10 — инженерная строгость. Хранится отдельно от креатива.", True),
    ("Главное", "top_p", "Top-p", "float", 0.9, "Разнообразие.", True),
    ("Главное", "num_ctx", "Окно контекста (цифрой)", "int", 131072, "Впиши цифру. 0 = как в модели (агент сам подставит её окно; без этого Ollama по умолчанию даёт всего 4096!).", True),
    ("Главное", "num_predict", "Длина ответа (токенов)", "int", 4096, "0 = авто (8192). «Без ограничения» не ставим: зациклившаяся модель молотит часы.", True),
    ("Главное", "admin_password", "Пароль обучения", "str", "", "Для админ-действий.", True),
    ("Главное", "read_roots", "Корни чтения файлов", "str", "D:\\AI", "read_file читает только внутри этих корней (список через ;).", True),
    ("Главное", "auto_mode", "Авторежим", "bool", True, "Вкл: берётся «Температура при АВТОРЕЖИМЕ». Выкл: берётся «Креатив». Твои значения не сбрасываются.", True),
    ("Главное", "stream_tokens", "Стриминг токенов", "bool", True, "Печатать ответ по токенам по мере генерации.", True),
    ("Главное", "think_in_log", "Строки THINK в ходе работы", "bool", True, "Печатать ответ по токенам по мере генерации.", True),
    ("Главное", "show_steps", "Ход работы в ответах", "bool", True, "Печатать ответ по токенам по мере генерации.", True),
    ("Флот", "fleet_autocommit", "Авто-коммит решений", "bool", False, "Коммитить новые скиллы/кейсы в creo-repo автоматически.", True),
    ("Расписание", "night_enable", "Ночной прогон", "bool", True, "Автопрогон тяжёлых задач ночью.", True),
    ("Расписание", "night_hour", "Час прогона", "int", 2, "0-23.", True),
    ("Расписание", "night_minute", "Минута прогона", "int", 0, "0-59.", True),
    ("Расписание", "night_tasks", "Задачи ночи", "str", "scan,index,usage,backup,drafts", "scan/index/usage/backup/drafts через запятую.", True),
    ("Главное", "parallel_tools", "Параллельные инструменты", "bool", False, "Несколько [TOOL] за ход — в потоках.", True),
    ("Главное", "stream_ui", "Стриминг в веб", "bool", False, "Токены в чат по мере генерации.", True),
    ("Главное", "log_mode", "Режим логов 0-3", "int", 1, "0 авто / 1 авто+токены / 2 отладка / 3 полный.", True),
("Главное", "ui_layout", "Вид окна агента", "str", "v2", "Личный вид окна: v1 вкладки сверху / v2 боковое меню / v3 пульт.", True),
    ("Разум", "log_days", "Дней хранить лог", "int", 14, "Автоочистка логов.", True),
    ("Разум", "verbose_trace", "Подробный trace", "bool", False, "Сырые JSON в trace-файл.", False),
    ("Разум", "think_mode", "Глубина рассуждений 0-2", "int", 2, "0=выкл, 1=кратко, 2=полно (блок [THINK] по-русски).", True),
    ("Разум", "llm_timeout", "Таймаут ответа модели, сек", "int", 240, "Предел времени на один ответ. Защита от зацикливания (GPU не жжём впустую).", True),
    ("Разум", "think_lines_max", "Размер размышлений, строк", "int", 8, "Сколько строк мыслей просить в блоке [THINK].", True),
    ("Память", "hist_q_chars", "История диалога: вопрос, знаков", "int", 1000, "Сколько знаков вопроса помнить в контексте.", True),
    ("Память", "hist_a_chars", "История диалога: ответ, знаков", "int", 1500, "Сколько знаков ответа помнить в контексте.", True),
    ("Разум", "think_native", "Служебный канал размышлений (англ.)", "bool", False, "Выкл (рекомендуется): думает только в [THINK] по-русски. Вкл: добавляется английский канал Ollama.", True),
    ("Поиск", "repo_boost", "Буст репозитория", "float", 1.2, "Умножение схожести для repo.", True),
    ("Поиск", "repo_boost_min_sim", "Порог буста", "float", 0.2, "Мин схожесть для буста.", False),
    ("Поиск", "top_chunks", "Топ чанков", "int", 4, "Сколько фрагментов видит модель.", True),
    ("Поиск", "chunk_chars", "Символов в чанке", "int", 900, "Длина фрагмента.", True),
    ("Поиск", "chunk_size", "Размер чанка", "int", 1500, "Нарезка при индексе.", False),
    ("Поиск", "chunk_overlap", "Перекрытие", "int", 200, "Зона перекрытия.", False),
    ("Визия", "vision_backend", "Бэкенд визии", "str", "ollama", "ollama / llamacpp.", True),
    ("Визия", "vision_url", "URL llamacpp", "str", "http://127.0.0.1:8081", "Адрес llama-server.", True),
    ("Визия", "vision_model", "Модель визии", "str", "qwen2-vl:7b", "Vision-модель Ollama.", False),
    ("Визия", "vision_gpu", "GPU-слоёв", "int", 0, "Слоёв на GPU.", False),
    ("Визия", "image_days", "Хранить скрины дней", "int", 7, "Срок хранения.", True),
    ("Creo", "creo_allow_start", "Разрешить агенту стартовать Creo", "bool", False, "Выкл: Creo поднимает только человек (CREO-START.bat). Вкл (админ): агент может поднять Creo — появится его синий сплеш.", True),
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
    ("Пути", "creoson_dir", "Папка CREOSON", "str", r"D:\AI\creoson", "Где creoson_run.bat.", True),
    ("Пути", "pdf_out", "Папка PDF", "str", "", "Пусто = рядом с чертежом.", True),
    ("Пути", "backup_dir", "Папка бэкапов", "str", "", "Пусто = agent/data/backups.", True),
    ("Пути", "trail_dirs", "Папки трейлов", "list", [], "Пусто = trail_dir из Creo + локальная папка Creo.", True),
    ("Creo", "bom_sections", "Порядок разделов спецы", "list", ["Документация", "Комплексы", "Сборочные единицы", "Детали", "Стандартные изделия", "Прочие изделия", "Материалы", "Комплекты"], "Порядок ГОСТ-разделов.", True),
    ("Главное", "steps_max", "steps_max", "int", 6, "Из config.json (авто-регистрация).", True),
    ("Сканер", "scan_roots", "scan_roots", "list", ["D:\\AI\\repo"], "Из config.json (авто-регистрация).", True),
    ("Сканер", "scan_exclude", "scan_exclude", "list", [".git\\", "__pycache__\\", "node_modules\\", "venv\\", ".venv\\", "backup\\", "old\\", "temp\\", "tmp\\", "cache\\", ".idea\\", ".vscode\\", "Thumbs.db", "desktop.ini", "*.tmp", "*.bak", "*~", "*.log", "*.sqlite", "*.db", "*.exe", "*.dll", "*.so", "*.o", "*.obj", "*.pyc", ".DS_Store"], "Из config.json (авто-регистрация).", True),
    ("ИИ-роли", "ollama_keep_alive", "Держать модель в памяти", "str", "1h", "keep_alive Ollama: 1h/30m/-1 (всегда). Дом: одна модель на агент и Cline.", True),
    ("ИИ-роли", "ollama_max_models", "Моделей в памяти, максимум", "int", 1, "1 = только одна модель в памяти (не роняем машину).", True),
    ("ИИ-роли", "model_index", "Модель индексации", "str", "nomic-embed-text:latest", "Эмбеддинги, без чата.", True),
    ("ИИ-роли", "model_chat", "Модель чата", "str", "", "Пусто = llm_model.", True),
    ("ИИ-роли", "model_fast", "Модель рутины", "str", "", "Быстрые/простые ходы.", True),
    ("ИИ-роли", "model_creo", "Модель Creo", "str", "", "Пусто = llm_model.", True),
    ("ИИ-роли", "model_spec", "Модель спец", "str", "", "Пусто = llm_model.", True),
    ("ИИ-роли", "model_trail", "Модель трейлов", "str", "", "Диагностика трейлов.", True),
    ("ИИ-роли", "model_web", "Модель веб", "str", "", "Пусто = llm_model.", True),
    ("ИИ-роли", "model_audit", "Модель аудита", "str", "", "Пусто = llm_model.", False),
    ("ИИ-роли", "model_vision", "Модель визии", "str", "qwen2-vl:7b", "Vision-модель Ollama.", True),

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
            if key == "auto_mode" and value is True:
                for _, k2, _, _, defl2, _, _ in REGISTRY:
                    if k2 in ("creativity", "auto_temperature", "top_p", "steps_max"):
                        d[k2] = defl2
            break
    CONFIG_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    return True

def show_all():
    d = _raw()
    out = []
    for space, k, name, typ, defl, desc, ui in REGISTRY:
        out.append("• [%s] %s = %s — %s" % (space, k, "••••••" if "password" in str(k) else d.get(k, defl), desc))
    return "\n".join(out)

def list_ui():
    d = _raw()
    B = {"log_mode": (0, 3, 1), "night_hour": (0, 23, 1), "night_minute": (0, 59, 1),
         "creativity": (0, 100, 1), "auto_temperature": (0, 100, 1), "top_p": (0, 1, 0.05),
         "log_days": (1, 365, 1), "image_days": (1, 60, 1), "history_days": (1, 365, 1),
         "client_days": (1, 365, 1), "top_chunks": (1, 12, 1), "chunk_chars": (200, 2000, 100),
         "chunk_size": (500, 4000, 250), "chunk_overlap": (0, 1000, 50),
         "repo_boost": (0.5, 3, 0.1), "repo_boost_min_sim": (0, 1, 0.05),
         "vision_gpu": (0, 64, 1), "max_file_mb": (1, 100, 1), "retention": (1, 30, 1),
         "audit_limit": (1, 100, 1), "steps_max": (1, 16, 1), "think_mode": (0, 2, 1), "think_lines_max": (2, 30, 1), "ollama_max_models": (1, 4, 1), "hist_q_chars": (200, 4000, 100), "hist_a_chars": (200, 8000, 100),
         "web_quick_links": (0, 100, 1), "web_deep_pages": (0, 200, 5)}
    out = []
    for space, k, name, typ, defl, desc, ui in REGISTRY:
        if not ui:
            continue
        v = d.get(k, defl)
        if "password" in str(k):
            v = "••••••"
        e = {"space": space, "key": k, "name": name, "type": typ, "value": v, "desc": desc}
        if typ in ("int", "float") and k in B:
            lo, hi, st = B[k]
            e["min"], e["max"], e["step"] = lo, hi, st
            e["kind"] = "range"
        elif typ == "bool":
            e["kind"] = "check"
        else:
            e["kind"] = "text"
        out.append(e)
    return out


def model_for(role):
    v = get("model_" + role)
    return v or get("llm_model")

PERSONAL_KEYS = ["chat_mode", "ui_layout"]
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