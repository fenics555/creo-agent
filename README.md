# АГЕНТ v14 — локальный ИИ-напарник конструкторского бюро (Creo Parametric)

> Обновление 11.09.2026: честная UTF-8 кодировка ядра, удалён дубль `/status`,
> `read_file` ограничен корнями `read_roots` (панель → Главное), QA-секреты →
> `data/secrets.json`, `doctor.py` удалён. Индекс — «История обновлений» в конце.

Веб-агент на чистом Python (stdlib) + Ollama + CREOSON: чат с локальной LLM,
живые данные Creo, база знаний, индекс «где используется», ПЛМ-реестр,
ГОСТ-спецификации, трейлы, флот, бэкапы, ночные прогоны. Без внешних фреймворков.

## Возможности
- Чат с протоколом `[TOOL]/[ANSWER]`: один ход = один блок; пишущие операции — под щитом ✅ согласования.
- Живое чтение Creo через CREOSON (17 инструментов чтения) + 16 пишущих операций.
- База знаний: скан файлов и 3D-моделей, эмбеддинги (nomic-embed-text), поиск `search_kb`/`models_find`.
- Индекс «где используется» (usage): деталь → сборки из бинарных `.asm`.
- ПЛМ: реестр изделий, BOM, ревизии, извещения ИИ по ГОСТ 2.503.
- Визия: скриншоты Ctrl+V → vision-модель (minicpm-v:8b).
- Мастер 🧙: копия сборки (план/факт), аудит папки Creo, пересборка usage, ночной прогон.
- Память, трейлы, обучение (SKILL_*.md), команда 💬, роли и админка 👤.
- Флот: статусы машин, git-синхронизация, автокоммит решений.
- Ночной прогон по расписанию: scan, index, usage, backup.

## Архитектура и порты
| Компонент | Порт | Назначение |
|---|---|---|
| agent.py | 8765 | HTTP-сервер, веб-UI, run_loop, стриминг токенов |
| CREOSON | 8080 | мост к Creo (чтения + запись) |
| copy-server | 8000 | страница «Копия сборки» |
| Ollama | 11434 | локальные LLM и эмбеддинги |

Ядро: `core.py` (пути, логи, sqlite WAL, Ollama, CREOSON), `settings.py`
(REGISTRY-кортежи ровно по 7 элементов), `tools_registry.py` (автоподключение
`*_tools.py`), `scanner.py` (files/chunks/models), `agent.py` (сервер + PAGE).

## Блоки (31, 117 инструментов; по живому реестру 11.09 — источник правды tools_registry)
backup(2) · behavior(1) · calc(3) · chat(1) · copy(1) · creo_ops(16) · creo(17) ·
diagnostic(7) · find(3) · fleet(2) · git(4) · help(2) · knowledge(3) · learn(2) ·
memory(6) · nightly(2) · one_c(1) · passport(2) · pdf(4) · plm(7) · predict(1) ·
role(3) · scanner(3) · settings(3) · spec(2) · sync(5) · trail(4) · usage(3) ·
users(3) · vision(1) · web(3)

Новый блок = файл `my_tools.py` + рестарт:
```python
def tool_hello(q="", **kw):
    return "привет: %s" % q
TOOLS = [
    {"name": "hello", "desc": "Пример", "params": {"q": "текст"},
     "approval": False, "fn": tool_hello},
]
```

## Двухъярусный промт (agent.py — build_system)
Системный промт автоматически делит инструменты на два яруса:
- **Ядро (15)** — частые, с полным описанием и параметрами в системном промпте:
  `creo_get_active, creo_status, creo_session, creo_list_files, models_find,
  models_where, models_stats, usage_state, search_kb, read_file, trail_predict,
  trail_problems, settings_show, help, tools_help`.
- **Остальные (102)** — только имена компактным списком. Полное описание блока
  доступно по запросу: `[TOOL: tools_help] {"block": "creo"} [/TOOL]` (или
  `web/trail/plm/...`).

Это сокращает промт на ~25% и радикально улучшает соблюдение моделью формата.

## Требования и старт
```

## Требования и старт
Windows 10/11, Python 3.10+, Ollama, CREOSON 3.x, Creo 8–13.
- `AI_START.bat` / `AI_RESTART.bat` / `AI_STOP.bat` (или `python ctl.py up`).
- Веб: `http://<IP>:8765`. Вход по умолчанию `admin/admin`; смена пароля: 👤.
- После каждого рестарта агента — **Ctrl+F5** в браузере (JS кешируется).

## Пути и данные
- Код: `D:\AI\tools\agent`; данные: `D:\AI\tools\agent\data`
  (`agent.sqlite`, `config.json`, `user_prefs.json`, бэкапы).
- Логи: `D:\AI\tools\agent_log_<host>.txt`, `diag_full.log`, `diag_creoson.log`.
- Корни/исключения скана: `kb_roots.txt` / `kb_exclude.txt` рядом с агентом.
- Репо знаний: `D:\AI\repo` — `SKILL_*.md`, `Ошибки/ERR_*`, `Изменения/ИИ_*`,
  `Трейлы/TRAIL_JOURNAL.md`.
- Таблицы БД: `files`, `chunks`, `models`, `usage(+meta)`, `history`,
  `items`, `bom`, `revisions`, `changes`.

## Модели (Ollama) и роли
- Боевой чат: `qwen2.5-coder:14b` (`llm_model`); для сложных вопросов —
  `qwen2.5-coder:32b-instruct-q4_K_M` (Панель → МОДЕЛЬ ИИ).
- Рутина/трейлы: `qwen2.5-coder:7b`; эмбеддинги: `nomic-embed-text`;
  визия: `minicpm-v:8b`. Авторежим: температура 0.1 (инженерная строгость).
- Рекомендация: `set OLLAMA_NUM_THREADS=16` в `OLLAMA-WD.bat`
  (оставить CPU системе и Creo).

## Веб-UI
Верх: ❓ справка · 🧙 мастер · Лог · Панель · 👤 профиль/админка · 💬 команда · Выйти.
Панель: ДЕЙСТВИЯ (без ИИ), МОДЕЛЬ ИИ (клик — смена), БЫСТРЫЕ ЗАДАЧИ,
группы блоков, НАСТРОЙКИ (ползунки/галочки; «Авторежим» возвращает
креатив/температуру к дефолтам). Скриншоты — Ctrl+V в поле ввода.
Пишущие операции показывают ✅ выполнить / ❌ отмена.

## Диагностика
`diag_run` — полная самопроверка (вердикт ПРОЙДЕН/НЕ ПРОЙДЕН);
`diag_test` — матрица CREOSON + ключевые инструменты;
`probe_run` — автопрогон всех инструментов (только чтение);
`creoson_full_test` — пишущий цикл на копии (под ✅);
`diag_learn` — обучение на активной модели; `diag_usage` — семантика индекса;
`diag_web` — веб-стек + внешний URL. Строка «поведение: ok/warn/bad» в логе —
соблюдение моделью протокола.

## Правки: как править (doctor.py удалён 11.09)
`doctor.py` был временным хирургическим инструментом и удалён из репо; старые
doctor-скрипты повторно НЕ запускать — они ломают новые правки. Правки кода —
по контракту `D:\AI\.clinerules` (v5.1, read-only, правит только человек):
бекап в `data\backup\pre_*` → правка → `py_compile` → одна целевая проба →
отчёт; два провала — откат из бекапа. Живая самопроверка — `diag_run`
(см. «Диагностика»). Типовые прошлые фиксы — в таблице ниже.

| Симптом | Причина / фикс |
|---|---|
| `diag_web` FAIL | нет `fetch_html` → алиас `fetch_html = fetch` |
 | `plm_where/plm_lifecycle/plm_ii` NameError | `db()` вместо `_db()` |
 | Индекс виснет при overlap ≥ size | `chunker`: `s += max(1, size - ov)` |
 | Скан 0 моделей | `scanner.db()` на локальную `data/agent.sqlite`; `is_excluded` понимает Path |
 | Ответ «текст» / «не понял ваш запрос» | echo_guard: модель копирует подсказку → детектится, пользователю отдаётся результат инструмента (`last_res`), а не мусор; refusal guard: «нет доступа/не могу» → ретрай с подсказкой `_ACCESS_NUDGE` «доступ ЕСТЬ, у тесть БД/CRE/SKILL» |
 | `[TOOL] имя` без двоеточия/JSON | парсер принимает и такой формат (fallback) |
 | Настройки не сохраняются после рестарта | выключить `auto_mode` и панелью поставить дефолтные температуру/креатив |
 | `REGISTRY` кортеж не 7 элементов | проверять через `list_ui`; правка руками (doctor удалён) |
`.\AI_RESTART.bat` → Ctrl+F5 → `GIT_SYNC.bat` (лог: `D:\AI\tools\git_sync.log`).

## История обновлений (индекс)
- 11.09.2026 (вечер): PAGE (HTML/CSS/JS панели, 169 строк) вынесен из `agent.py`
  в `panel_ui.py` (agent ~60→37 КБ, правка UI теперь не трогает логику);
  `ctl.py`: `--browser` открывает `127.0.0.1:8765` (был захардкод IP) и починен
  `\t`-escape в пути `copy_err.txt`; `qa\qa_run.py` считает `LOG_FILE` по HOST;
  зеркала `PASSPORT.md` кладутся в `D:\AI\repo` (github-страховка).
- 11.09.2026: agent.py/qa_run.py перекодированы в честный UTF-8 (системный промт
  и QA без кракозябр); удалён дубль `/status` (мёртвый elif в do_GET); `read_file`
  ограничен корнями `read_roots` (панель → Главное, дефолт `D:\AI`, лимит 2 МБ);
  QA-секреты вынесены в `data/secrets.json` (в git не попадают); `doctor.py`
  удалён как временный инструмент; `GIT_SYNC.bat` пишет лог; задача AI-WATCH
  исправлена (пугала пусками несуществующего `D:\AI\agent.py`); счёт обновлён
  по живому реестру — 31 блок / 117 инструментов (+pdf(4), help 1→2).
- 09.07.2026: блок calc_tools (+3), счёт 30 блоков / 113 инструментов.
- 09.04.2026: базовая редакция README v14.

## Известные грабли и их лечение
| Симптом | Причина / фикс |
|---|---|
| Настройки/модель «не сохраняются» | ключи в PERSONAL_KEYS писались в личный слой, который никто не читал → `PERSONAL_KEYS = []` |
| Ответ «текст» вместо инструмента | отравленная история (few-shot) + SKILL без грамматики + склейка токенов с пробелом → чистка `DELETE FROM history`, `SKILL_agent_protocol.md` в `.bak`, `"".join(parts)`; предохранитель `stream_tokens=False` |
| `database is locked` | параллельные записи → WAL + `timeout=60` в `core.db()` |
| `too many values to unpack (expected 7)` | кортеж REGISTRY ≠ 7 элементов |
| Фон: `ModuleNotFoundError: scanner` | subprocess стартовал не из папки агента → `cwd=D:\AI\tools\agent` |
| `diag_web` FAIL | нет `fetch_html` → алиас `fetch_html = fetch` |
| `plm_where/plm_lifecycle/plm_ii` NameError | `db()` вместо `_db()` |
| Индекс виснет при overlap ≥ size | `chunker`: `s += max(1, size - ov)` |
| Скан 0 моделей | `scanner.db()` на локальную `data/agent.sqlite`; `is_excluded` понимает Path |

## Смежные репозитории
`fenics555/creo-agent` (код, ветка master) · `fenics555/creo-repo` (скиллы).
Оперативное состояние и открытые пункты — `PASSPORT.md`.