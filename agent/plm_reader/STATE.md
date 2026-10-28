# STATE — ЖИВОЕ СОСТОЯНИЕ PLM READER (обновлять при КАЖДОМ шаге)

> Правило: «Сессия смертна. Всё, что не в файле — потеряно». Три строки, дата замера,
> источник каждого утверждения. Версия формата — 28.10.2026 (предложение эстафеты, §3 «чего не хватает»).

**Обновлено:** 28.10.2026, 22:15 · нога Cline

```
на диске:  engine.py (CREO_EXTS 167-170, role_by_path 707/719, _base_dir 1113), creo_read.py (role by ext 224/243),
           STRATEGY_PLM.md §2.2+§2.3+§2.4 (276), AGENTS.md правила 5-6, version.json V140/22 (замер RESULT: OK)
в git:     tools master 1801c42 (впереди origin на 7 коммитов, push не делал) + repo 352354c (GRABLI 102-105, карта);
           git status чист, кроме ?? _s.txt — per-run вывод смоука, НАМЕРЕННО вне git
работает:  скан склада 3.6 с (new/skip/errors в результате), публикация в папку active_db(), роли по расширению,
           приёмка _smoke_v87.py → SMOKE OK + «ЦЕЛОСТНОСТЬ ПОСТАВКИ» (22 файла, все SHA256)
не работает: значения family-таблицы (в библиотечных файлах их нет — только имена), размеры dN из байтов
           (только J-Link), plm_links.py НЕ внедрён (расчёт: 38 мест построения связей), мусор links 22 646 строк
не сделано: GRABLI §102/§103; DELETE мусора в links (только по слову владельца); built 23 240 из 92 963 (25 %)
```

## Как проверять (команды дома)

```powershell
# поставка цела? (Get-FileHash ЗАПРЕЩЁН — GRABLI §100, только нормализующий хашер)
cd D:\AI\tools\agent\plm_reader; python make_version_json.py "проверка"   # пересобирает, затем сверить files==sha256
python _smoke_v87.py                                                       # ожидается SMOKE OK
python -m py_compile engine.py creo_read.py plm_queries.py plm_links.py plm_build_links.py
# что не закоммичено?
cd D:\AI\tools; git status --short; git diff HEAD --stat -- agent/plm_reader
```

## Что НЕ трогать без слова владельца

- шара `Z:\PTC\CREO-START\plm_reader` — **агент не касается** (GRABLI §82, SKILL_plm_reader_sync);
- боевая база (она на шаре) — пробы только на **копии**;
- одна база / связи по структуре файла, не по имени (GRABLI §85, §95).
