# D:\AI\tools — программы и агент дома

**Обновлено:** 23.09.2026 · Полный каталог с паспортами: `agent\dev\PROGRAM_REGISTRY.md`

В каталоге два хозяина:
- `agent\` — агент (порт 8765) и **все программы дома**, каждая в своей папке;
- корень — служба дома: `GIT_SYNC.bat` (синхронизация репозиториев), `STOP_ALL.ps1`, `data\`.

## Что значит «автономная программа»
Автономная = запускается сама и работает **без агента**:
1) всё своё — в своей папке (движок, `.bat`, собственный `README.md`);
2) живой Creo нужен, только если это прямо написано в таблице ниже (подключение к **уже запущенному** Creo, без CREOSON);
3) ничего не берёт из кода агента (`core.py`, `*_tools.py`), настройки — свои файлы;
4) логи пишет в `D:\AI\log\<имя>\`, бэкапы держит рядом в `_pre\`;
5) у каждой свой **README.md** (образец для подражания — `agent\creo_pdf\README.md`).

## A. Автономные, живой Creo НЕ нужен
| Программа | Папка / файл | Чем живёт | Запуск | README |
|---|---|---|---|---|
| **dup_scan** (двойники) | `agent\dup_scan` | Python; sha1 по содержимому; `--apply` → `_trash_dup` | `dup_scan.bat <папка> [--apply]` | ✅ |
| **cmnm_scan** (внутренние имена) | `agent\cmnm_scan` | Python; поле `#- CMNM` против имени файла (модель не откроется, если расходятся) | `python cmnm_scan.py <папка>` | ✅ |
| **make_lst** (ограничения параметров) | `agent\make_lst` | Python; собирает `list.lst` (cp1251) + бэкап прежнего | `make_lst.bat [--dry] [--from refs.txt]` | ✅ |
| **config_audit** (аудит config.pro) | `agent\config_audit` | Python; проверяет **каждый путь** config.pro на диске | `config_audit.bat [путь\config.pro]` | ✅ |
| **orphan_scan** (чертежи-сироты) | `agent\orphan_scan` | Python; нужны базы дома `data\agent.sqlite`, `data\harvest.db` и `Z:\PTC\Work\search.pro` | `orphan_scan.bat "<папка>"` (без аргумента — по `search.pro`) | ✅ |
| **log_clean** (уборка логов) | `agent\log_clean.py` | читает `D:\AI\log\retention.json`, чистка по срокам | `python log_clean.py` | — |
| **purge_versions** (ЧИСТИЛЬЩИК версий) | `agent\purge_versions` | переносит лишние версии Creo в бэкап (**ничего не удаляет**); **окно с настройками** | `purge_gui.bat` (окно) / `purge_versions.bat -r <папка> -k 2` | ✅ |
| **copy_server** | `agent\copy\copy_server.py` | HTTP-приём/отдача файлов, порт **8000** | `python copy_server.py` | — |
| **skills_check** | `agent\dev\skills_check.py` | шапки скиллов + baseline `data\skills_check_baseline.txt` | `python dev\skills_check.py` | — |
| **excel** (export/import) | `agent\excel` | XLSX **без внешних библиотек** (модули для спецы) | импортируется кодом | — |

## B. Автономные, нужен ЖИВОЙ Creo (JLINK, без CREOSON)
| Программа | Папка | Что делает | Запуск | README |
|---|---|---|---|---|
| **creo_pdf** | `agent\creo_pdf` | скан и обновление PDF чертежей; окно с настройками и отчётом | `creo_pdf_gui.bat` | ✅ |
| **creo_export** | `agent\creo_export` | выгрузка из живой сессии: step, iges, vrml, pdf, neutral, dxf3d, stl | `creo_export.bat <формат> <модель>` | ✅ |
| **creo_comb** (чесалка) | `agent\creo_comb` | параметры/уравнения/ограничения: `tpl-plan`, `refs`, `roles`, `scan`, `add`, `typcheck`… | `creo_comb.bat <режим> [папка]` | ✅ |

⚠️ Creo-программы звать **только по полному пути** (живая находка 23.09.2026: при детач-запуске голое имя
бата может не найтись). Требование одно: Creo **уже запущен** и стартовал из папки боевого `config.pro`.

## C. Это НЕ программы, а части агента (сами не работают)
`agent.py`, `loop.py`, `core.py`, `http_handlers.py`, `settings.py`, `scanner.py`, все `*_tools.py`
(в т.ч. `creo_tools.py`, `plm_tools.py`, `pdf_tools.py`), `harvest*.py`, `pdf_refresh_*.py`,
`qa\`, `ui\`, `backup_spec87\` — тело, руки и витрина агента: им нужны агент, его база `data\agent.sqlite`
и настройки. Отдельно от дома не запускаются.
## Как перенести автономную программу на другую машину
1) скопировать **папку целиком** (движок + `.bat` + `README.md`) — у каждой программы всё своё;
2) на новой машине посмотреть в её README раздел «ПЕРЕНОС» (у `creo_pdf`: свой `pfcasync.jar`,
   свой `gui_settings.json`, путь к `config.pro`);
3) логи и бэкапы **не копируются** — они лежат в `D:\AI\log\<имя>\` и в `_pre\` рядом с данными;
4) Creo-программам нужен работающий Creo (для `creo_pdf` есть кнопка «Запустить Creo (штатно)» —
   она поднимает Creo с рабочей папкой = папка выбранного `config.pro`);
5) Java-программы (`creo_pdf`, `creo_export`, `creo_comb`) сами компилируют свой `.class` при первом
   запуске из `.java` и сами копируют `pfcasync.jar` из своей папки.

## Служба дома (не программы)
| Что | Зачем |
|---|---|
| `GIT_SYNC.bat` | синхронизация репозиториев (задача планировщика `creo-sync`) |
| `STOP_ALL.ps1` | остановить стек одним махом |
| `agent\ctl.py up / status / down / --watch` | подъём и сторож стека (Ollama 11434, CREOSON 8080 — по требованию, copy-server 8000, агент 8765) |
| боевой `CREO-START.bat` | старт Creo из папки боевого `config.pro` (`Z:\PTC\CREO-START\START-STD\`) |

## Правила дома, которые касаются всех программ
1. **Перед правкой — копия.** Рабочие файлы в `Z:` — только с бэкапом в `БЕКАП\` и записью в `БЕКАП\ЖУРНАЛ.md`.
2. **Чужие данные — только чтение.** Свои таблицы в базах — с префиксом (`plm_`).
3. **Логи — в `D:\AI\log\<имя>\`**, временные файлы — в свою урну (`_trash`, `_trash_dup`), не в папку программы.
4. **Сначала отчёт, потом правка.** Пишущие режимы отделены: `--apply`, `add`, `--empty-first`.
5. **Паспорт программы — строка в `agent\dev\PROGRAM_REGISTRY.md`** (класс, вход, логи, состояние).