# АГЕНТ v12 — ИИ-напарник для Creo Parametric

Веб-агент для конструкторского бюро: отвечает по-русски, работает с живыми
данными (Creo, файлы, база знаний, трейлы) и не выдумывает: живые данные —
только через инструменты.

## Что умеет
- Чат с локальной LLM (Ollama) + инструменты: Creo через CREOSON, поиск
  моделей по имени и папкам, «где используется деталь», векторный поиск по
  базе знаний, разбор трейлов, бэкапы, настройки.
- Пишущие операции в Creo — только после согласования пользователем (✅/❌).
- ГОСТ-спецификации в XLSX (разделы, позиции, картинки моделей), чтение
  чужих XLSX-спецификаций.
- Командный чат, профили и роли пользователей, админка, флот-мониторинг
  агентов в сети.

## Архитектура
- `agent.py` — HTTP-сервер :8765 (веб-панель + JSON API), без внешних зависимостей.
- `*_tools.py` — блоки инструментов; подключаются автоматически через
  `tools_registry.py`. Новый блок = новый файл со списком `TOOLS`.
- `core.py` — инфраструктура: SQLite, логи, запросы к Ollama.
- `ctl.py` — пуск/стоп/сторож стека (Ollama, CREOSON, агент), скрытый режим.
- CREOSON Server :8080 — JSON-мост к Creo (J-link).
- Ollama :11434 — локальные модели.

## Требования
- Windows 10/11, Python 3.10+ (стандартная библиотека).
- Creo Parametric 8–13 + CREOSON 3.x (github.com/SimplifiedLogic/creoson).
- Ollama с моделями: `qwen2.5-coder:14b` (чат), `nomic-embed-text` (поиск);
  опционально `deepseek-r1:14b`, `qwen2-vl:7b` (визия). GPU от 8 ГБ желателен.

## Быстрый старт
1. Клонируйте репо в `D:\AI\tools\agent` (пути зашиты в `core.py`/`ctl.py` —
   поправьте под себя).
2. Поднимите CREOSON и Ollama.
3. `python ctl.py up --browser` — поднимет стек и откроет панель.
   `AI_RESTART.bat` — перезапуск без лишних окон.
4. Откройте http://127.0.0.1:8765 (или сетевой_IP:8765).
5. Вход: `admin` / `admin`. Сразу смените пароль (👤 → Сменить пароль).

## Блоки инструментов (автоподключение)
creo_tools (чтение Creo), creo_ops_tools (запись, с согласованием),
scanner_tools/knowledge_tools (скан и база знаний), find_tools (поиск моделей),
usage_tools («где используется»), spec_tools + excel_export/excel_import
(ГОСТ-спецификации), trail_tools (трейлы), chat_tools (командный чат),
users_tools (роли), backup_tools, fleet_tools, vision_tools, web_tools,
learn_tools, memory_tools, passport_tools, settings_tools, diagnostic_tools.

## Разработчику
Новый блок — файл `my_tools.py`:
```python
TOOLS = [{"name": "my_tool", "desc": "описание", "params": {},
          "approval": False, "fn": my_fn}]