# ПРОВЕРКИ ДОМА (checks) — каркас и единый прогон

**Класс Р:** только читает и считает. Ничего не чинит.

## ЗАЧЕМ
Проверки дома жили разрозненно: `hol_check`, `config_audit`, `cmnm_scan`, `plm_audit`, трейлы —
у каждой свой отчёт и свой запуск. Этап 3 плана требует: **«прогнать все проверки по папке»
даёт один отчёт**, а каждая старая проверка продолжает работать и по-своему.

## КАК ЗАПУСТИТЬ
```
python checks.py               # все проверки
python checks.py hole_charts   # только область
```
Из агента: `checks_list` (реестр), `checks_run` (прогон), `checks_report` (отчёты).

## ПАСПОРТ ПРОВЕРКИ
```python
@check("hol_check", "Таблицы отверстий .hol читаемы", "check", "hole_charts",
       "error", app="hol_check")
def _run_hol():
    ...
    return _res(ok, total, failed, warned, detail, items)
```
Результат — единый вид `{ok, total, failed, warned, detail, items}`, поэтому сводка
считается по любым проверкам.

## ЗАРЕГИСТРИРОВАНО (19)
Полный список всегда берётся из кода: `python checks.py --list` (инструмент `checks_list`).
Таблица «5 проверок» устарела 23.11.2026. Сейчас в прогоне: `hol_check`, `hol_backups`,
`config_paths`, `plugins_registry`, `rules`, `tool_contracts`, `services_live`, `db_size`,
`window_design`, `ui_integrity`, `culture`, `window_launch`, `registry_contracts`,
`model_facts`, `drawing_notes`, `hatch_audit`, `cmnm_names`, `dup_files`, `encoding_files`.

## ГЛАВНОЕ СВОЙСТВО
**Падение одной проверки не роняет прогон.** Исключение внутри проверки превращается в
строку «провал» в сводке (проверено живой пробой с намеренно падающей проверкой) — иначе
одна битая проверка уронила бы весь отчёт.

## СВОДКА
`checks_run` возвращает `percent` — **процент соответствия** (константа 4 волны 1):
сколько проверок прошло из запущенных. Живой прогон 03.10.2026: 5 проверок, 113 объектов,
100 % соответствия, RC 0. Отчёт: `D:\AI\log\reports\REPORT_checks_run_*.md`.