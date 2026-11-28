# API PLM READER — управление без вспомогательных скриптов

> Раздел-заготовка для README PLM (вставляется при боевой интеграции, Этап 4б/5б).
> Создан в `D:\AI\PROBA\agent_api_probe\plm_adapter\README_API_SECTION.md` (28.11.2026).

## Зачем

PLM Reader умеет управлять собой через **файловый API**: ИИ (или внешний вызов) кладёт
JSON-команду в `api\in\<имя>.json` — PLM исполняет её **своим методом** (как кнопку) и кладёт
ответ в `api\out\<имя>.json`. **Никаких внешних скриптов-обёрток.**

Единый механизм для всех подпрограмм агента — каркас `agent_api` (образец — `AGENT_SETTINGS\pult_api`).

## Транспорт

```
ИИ → api\in\<имя>.json   (UTF-8 без BOM; {"cmd": "...", ...})
PLM (поток) исполняет     (раз в 1.5 с; журнал api\out\_api_journal.log)
PLM → api\out\<имя>.json  (ответ {"ok": true/false, "cmd": ...}; файл из in удаляется)
```

## Безопасность

- **read-команды** — свободно;
- **write-команды** (`settings_set`, `settings_reset`, `db_backup`, `db_repair`, `scan_start`) —
  требуют флаг `"apply": true`; без него — отказ (сухой прогон);
- запись настроек — **только через `plm_settings`** (реестр `SETTINGS_SPEC`), с бэкапом `.pre_<метка>`;
- база — **только через `plm_database`**; `db_query` — **только SELECT/WITH/PRAGMA** (лимит строк);
- **`Z:` и UNC — только чтение** (запись блокируется: флаг `writable:false` в `db_info`);
- файлы Creo читает ТОЛЬКО `plm_scanner.py` (API напрямую их не читает).

## Команды (21)

| Группа | Команда | Тип | Что делает |
|---|---|---|---|
| A | `status` | read | версия, файл/число настроек, база |
| A | `ping` / `schema` | read | жив/версия · самодокумент (все команды) |
| B | `settings_get` | read | настройки (все или по `key`) |
| B | `settings_spec` | read | реестр настроек (группы/типы/границы) |
| B | `settings_set` | write | записать настройку (бэкап, валидация) |
| B | `settings_reset` | write | вернуть настройку к умолчанию |
| C | `db_info` | read | путь/размер/таблицы/`writable` |
| C | `db_stats` | read | счётчики по всем таблицам |
| C | `db_tables` | read | таблицы с колонками |
| C | `db_query` | read | **только SELECT** (+ `limit`) |
| C | `db_doctor` | read | аудит базы |
| C | `db_backup` | write | бэкап базы |
| C | `db_repair` | write | починка (dry-run по умолчанию) |
| D | `log_list` | read | какие логи есть |
| D | `log_tail` | read | последние N строк лога |
| D | `window_state` | read | снимок состояния |
| E | `op_where` / `op_tree` | read | где используется · состав вниз |
| E | `op_changes` / `op_check` | read | журнал · актуально/нужен скан |
| E | `scan_start` | write | запустить скан (фоном) |
| E | `scan_status` | read | идёт ли скан |

## Пример

```json
{"cmd": "db_stats"}
```
→ `api\out\<имя>.json`: `{"ok": true, "db": "Z:\\...\\plm_reader.db", "count": 31, "tables": {...}}`

```json
{"cmd": "settings_set", "key": "max_size_mb", "value": 32, "apply": true}
```
→ `{"ok": true, "key": "max_size_mb", "old": 24, "new": 32, "backup": "...pre_...", "applied": true}`

## Ограничения

- API-поток живёт внутри процесса окна PLM — окно должно быть **запущено** (не `-WindowStyle Hidden`);
- скан (`scan_start`) идёт фоном и **не блокирует** API (ping отвечает во время скана).
