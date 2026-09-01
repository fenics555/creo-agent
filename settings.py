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
    ("Creo", "audit_limit", "Лимит аудита", "int", 20, "Моделей за аудит.", True),
    ("Creo", "audit_params", "Параметры аудита", "list", ["ОБОЗНАЧЕНИЕ", "НАИМЕНОВАНИЕ", "MASS"], "Что требуем от модели.", True),
    ("Память", "history_days", "Дней хранить историю", "int", 365, "Автоочистка истории.", False),
    ("Память", "client_days", "Дней хранить сессии", "int", 365, "Автоочистка клиентов.", False),
    ("Сканер", "max_file_mb", "Макс файл МБ", "int", 4, "Крупнее — не индексируем.", True),
    ("Сканер", "retention", "Глубина бэкапов", "int", 7, "Копий базы храним.", True),
    ("Пути", "creoson_url", "URL CREOSON", "str", "http://127.0.0.1:8080/creoson", "Мост Creo.", True),
    ("Пути", "creoson_dir", "Папка CREOSON", "str", r"D:\AI\creoson\CreosonServer-3.0.2-win64", "Где creoson_run.bat.", True),
    ("Пути", "pdf_out", "Папка PDF", "str", "", "Пусто = agent/pdf_out.", True),
    ("Пути", "backup_dir", "Папка бэкапов", "str", "", "Пусто = data/backups.", True),
    ("Creo", "bom_sections", "Порядок разделов спецы", "list", ["Документация", "Комплексы", "Сборочные единицы", "Детали", "Стандартные изделия", "Прочие изделия", "Материалы", "Комплекты"], "Порядок ГОСТ-разделов.", True),
    ("Creo", "copy_synonyms", "Синонимы поиска", "str", "турновер=переворот, turnover=переворот, ворошитель=переворот", "Для models_find.", True),
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
            CONFIG_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            return True
    return False

def show_all():
    d = _raw()
    out = []
    for space, k, name, typ, defl, desc, ui in REGISTRY:
        out.append("• [%s] %s = %s — %s" % (space, k, d.get(k, defl), desc))
    return "\n".join(out)