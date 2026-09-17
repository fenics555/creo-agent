# CREO-AGENT v15 — дом инженерного агента КБ

**Рантайм:** D:\AI\tools\agent · **Порт:** 8765 · **Обновлено:** 17.09.2026
**Состав:** монолит `agent.py` (голова сервера, планировщик, стриминг, HTTP-хендлеры — распил на sched/loop/http_handlers одобрен, спека 71, не начат), ядро `core.py`, настройки `settings.py`, реестр `tools_registry.py`, сканер `scanner.py` (индекс чанков + purge-предохранитель), PDF-глаза `pdf_tools.py`, пользователи `users.py` (TTL токена 24ч, ensure_admin из secrets.json), контроль `ctl.py` (watch: дебаунс 8с + дедуп по agent.pid) — **38 блоков, 133 инструмента** (цифры с 14.09.2026).

## Как работать с домом
- **Управление:** `python ctl.py up [--browser] [--hidden]` — идемпотентный подъём стека (Ollama 11434, CREOSON 8080, copy 8000, агент 8765).
  Статус: `python ctl.py status` · сторож: `python ctl.py --watch` · стоп: `python ctl.py down` · рестарт: `python ctl.py restart`.
- **Правки UI:** после любых правок в `ui/` запускать `python dev/ui_check.py` и `python dev/ui_probe.py` (правило 10.14).
- **Бекапы:** перед каждой правкой — `.bak` в `data\backup\` с именем `pre_<метка>_<файл>` (правило 4.1).
- **Контент:** в дом только через правки исполнителя или git (правило 10.7); секреты — только `data\secrets.json`, вне git.

## История правок
- **14.09.2026 — спека 34 (ремонт эпохи роста):** восстановлен `agent.py` от SyntaxError U+2014 (строки-хвосты в шапке файла), `scanner.py` вычищен от мёртвого `except`, починен `dev/ui_probe.py` (`ALL PASS`), паспорт и ридми обновлены с датами.
- **17.09.2026 — спеки 66б–66e:** МАНИФЕСТ в system-промпт; /panel восстановлена (401 без токена); /pdfthumb и /pdfimg отдают PNG с токеном из заголовка или query (ранний JSON-вариант /pdfimg снят); purge-предохранитель scanner.py; users: TTL токена 24ч, ensure_admin из secrets.json (дефолт admin/admin снят); ctl: debounce 8с + дедуп агентов по agent.pid; dev/skills_check.py: дельта-снапшот, честные проверки (name, executor, ОШИБКА grep-поле), фон нарушений = 0. Проверки/бекапы этой серии: `data\backup\pre_66b`, `pre_66d`, `pre_spec71_agent.py.bak` (к распилу 71, нога не начата).

## Ссылки
- Паспорт дома: `D:\AI\repo\PASSPORT.md` (источник истины)
- Карта скиллов: `D:\AI\repo\SKILL_index.md`
- Контракт: `D:\AI\.clinerules`