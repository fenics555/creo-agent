# АГЕНТ v14 — локальный ИИ-напарник конструкторского бюро (Creo Parametric)

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

## Блоки (29, 109 инструментов)
backup(2) · behavior(1) · chat(1) · copy(1) · creo_ops(16) · creo(17) ·
diagnostic(7) · find(3) · fleet(2) · git(4) · help(1) · knowledge(3) ·
learn(2) · memory(6) · nightly(2) · one_c(1) · passport(2) · plm(7) ·
predict(1) · role(3) · scanner(3) · settings(3) · spec(2) · sync(5) ·
trail(4) · usage(3) · users(3) · vision(1) · web(3)

Новый блок = файл `my_tools.py` + рестарт:
```python
def tool_hello(q="", **kw):
    return "привет: %s" % q
TOOLS = [
    {"name": "hello", "desc": "Пример", "params": {"q": "текст"},
     "approval": False, "fn": tool_hello},
]
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

## Правки: workflow doctor
Один файл `doctor.py`: перезаписать содержимое → `python doctor.py` →
`.\AI_RESTART.bat` → Ctrl+F5 → `GIT_SYNC.bat`.
⚠️ Старые doctor-скрипты повторно НЕ запускать — они ломают новые правки.
Каждая правка — с guard-ом и CHECK-выводом дисковой правды.

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