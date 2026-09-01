# АГЕНТ v12 — ИИ-напарник КБ (Creo Parametric)

Веб-агент: чат с локальной LLM (Ollama), живые данные Creo через CREOSON,
база знаний, трейлы, ГОСТ-спецификации, флот. Только стандартная библиотека Python.

## Вход
По умолчанию: `admin` / `admin` (роль Администратор). Смена: 👤 → Сменить пароль.

## Быстрый старт
1. Python 3.10+, Ollama, CREOSON 3.x, Creo 8–13.
2. `AI_START.bat` (или `python ctl.py up --browser`).
3. Открыть http://127.0.0.1:8765 (или сетевой_IP:8765).
Рестарт — `AI_RESTART.bat`, стоп — `AI_STOP.bat`, статус — `python ctl.py status`.

## Пути — где править
Панель → НАСТРОЙКИ → группа «Пути»: creoson_url, creoson_dir, pdf_out,
backup_dir, trail_dirs. Лежат в `agent/data/config.json`, можно править руками.
Корни индекса и исключения — `kb_roots.txt` / `kb_exclude.txt` рядом с агентом.
Корень установки (BASE, REPO) — `core.py` и `ctl.py` (TOOLS) при переезде.

## Блоки (автоподключение *_tools.py)
CREO (чтение), CREO-ОПЕРАЦИИ (запись под щитом ✅), SPEC (ГОСТ XLSX),
FIND/USAGE, ЗНАНИЯ/СКАНЕР, ПАМЯТЬ/ТРЕЙЛЫ/LEARN, 1С, ПАСПОРТ, ДОСТУПЫ,
ФЛОТ, ЧАТ, ВИЗИЯ, WEB, БЭКАПЫ, ДИАГНОСТИКА.
Новый блок = файл `my_tools.py` со списком TOOLS + рестарт.

## Диагностика
`diag_run` — полная самопроверка (вердикт ПРОЙДЕН/НЕ ПРОЙДЕН),
`diag_test` — быстрый прогон, `creoson_full_test` — пишущий цикл на копии.
Логи: `agent_log_*.txt`, `diag_full.log`, `diag_creoson.log`.

## Правки
Один файл `doctor.py`: перезаписать содержимое, затем
`python doctor.py`, `.\AI_RESTART.bat`, `.\GIT_SYNC.bat`.

## Смежный репозиторий
`creo-repo` — скиллы и справочники (Creo, Python, инженерные, производство).
