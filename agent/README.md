# CREO-AGENT v15 — дом инженерного агента КБ

**Рантайм:** D:\AI\tools\agent · **Порт:** 8765 · **Обновлено:** 14.09.2026
**Состав:** монолит `agent.py`, ядро `core.py`, настройки `settings.py`, реестр `tools_registry.py` — **38 блоков, 133 инструмента**.

## Как работать с домом
- **Управление:** `python ctl.py up [--browser] [--hidden]` — идемпотентный подъём стека (Ollama 11434, CREOSON 8080, copy 8000, агент 8765).
  Статус: `python ctl.py status` · сторож: `python ctl.py --watch` · стоп: `python ctl.py down` · рестарт: `python ctl.py restart`.
- **Правки UI:** после любых правок в `ui/` запускать `python dev/ui_check.py` и `python dev/ui_probe.py` (правило 10.14).
- **Бекапы:** перед каждой правкой — `.bak` в `data\backup\` с именем `pre_<метка>_<файл>` (правило 4.1).
- **Контент:** в дом только через правки исполнителя или git (правило 10.7); секреты — только `data\secrets.json`, вне git.

## История правок
- **14.09.2026 — спека 34 (ремонт эпохи роста):** восстановлен `agent.py` от SyntaxError U+2014 (строки-хвосты в шапке файла), `scanner.py` вычищен от мёртвого `except`, починен `dev/ui_probe.py` (`ALL PASS`), паспорт и ридми обновлены с датами.

## Ссылки
- Паспорт дома: `D:\AI\repo\PASSPORT.md` (источник истины)
- Карта скиллов: `D:\AI\repo\SKILL_index.md`
- Контракт: `D:\AI\.clinerules`