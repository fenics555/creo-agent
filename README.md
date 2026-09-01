# АГЕНТ v12 — ИИ-напарник КБ (Creo Parametric)

Веб-агент: чат с локальной LLM (Ollama), живые данные Creo через CREOSON,
база знаний, трейлы, ГОСТ-спецификации, флот. Только стандартная библиотека Python.

## Вход
По умолчанию: `admin` / `admin` (роль Администратор). Смена: 👤 → Сменить пароль.
Сброс: на сервере `python -c "import users; print(users.admin_reset_password('admin','admin'))"`.

## Быстрый старт
1. Python 3.10+, Ollama, CREOSON, Creo 8–13.
2. `AI_START.bat` (или `python ctl.py up --browser`).
3. Открыть http://127.0.0.1:8765 (или сетевой_IP:8765).
Рестарт — `AI_RESTART.bat`, стоп — `AI_STOP.bat`, статус — `python ctl.py status`.

## Пути — где править
- Панель → НАСТРОЙКИ → группа «Пути»: creoson_url, creoson_dir, pdf_out,
  backup_dir, trail_dirs. Лежат в `agent/data/config.json`, можно править руками.
- Корни индекса и исключения: `kb_roots.txt` и `kb_exclude.txt` рядом с агентом.
- Корень установки (BASE, REPO): `core.py` и `ctl.py` (TOOLS) — править при
  переезде на другую машину.
- Папка CREOSON: НАСТРОЙКИ → Пути → creoson_dir (ctl.py читает из config.json).

## CREOSON и окно «устаревшая опция конфигурации»
Creo 7+ требует код allow_deprecated_config для старых опций config.pro.
Агент сам вызывает `creo:set_creo_version` (Creo 12) сразу после подключения.
Если окно остаётся — обновите CREOSON до 7.0.2+ и укажите новую папку в
creoson_dir, либо уберите устаревшие опции (regen_failure_handling) из config.pro.

## Блоки (автоподключение *_tools.py)
CREO (чтение), CREO-ОПЕРАЦИИ (запись, под щитом ✅), SPEC (ГОСТ XLSX),
FIND/USAGE (поиск и «где используется»), ЗНАНИЯ/СКАНЕР, ПАМЯТЬ/ТРЕЙЛЫ/LEARN,
1С, ПАСПОРТ, ДОСТУПЫ, ФЛОТ, ЧАТ, ВИЗИЯ, WEB, БЭКАПЫ, ДИАГНОСТИКА.
Новый блок = файл `my_tools.py` со списком TOOLS + рестарт.

## Диагностика
`diag_run` — полная самопроверка (вердикт ПРОЙДЕН/НЕ ПРОЙДЕН), `diag_test` —
быстрая, `creoson_full_test` — пишущий цикл на копии, `probe_run` — все читающие.
Логи: `agent_log_*.txt`, `agent_trace_*.txt`, `diag_full.log`, `diag_creoson.log`.

## Git
`GIT_SYNC.bat` коммитит агент и репо. `data/`, логи, *.sqlite вне git (.gitignore).

## Смежный репозиторий
`creo-repo` — скиллы и справочники (Creo, Python, инженерные, производство).
