# ЧЕСАЛКА (creo_comb) — JLINK, без CREOSON

**Класс Ж** (живое Creo): причёсывает детали и сборки по ЭТАЛОНУ — шаблонам, прописанным
в `config.pro`. Сейчас готово только **чтение** (пробы и отчёт), запись (`add`) — следующим шагом.

## ОКНО (для рук)
```
creo_comb.bat tpl-plan                      — какие шаблоны прописаны в конфиге и есть ли файлы (без Creo)
creo_comb.bat refs                          — уравнения и параметры ЭТАЛОНОВ (нужен Creo)
creo_comb.bat dump <папка|файл> [имя]        — уравнения+параметры одной модели
creo_comb.bat scan <папка> [config.pro]      — чего не хватает моделям папки против эталонов
```

## ДВИЖОК (для ИИ и скриптов)
`creo_comb.bat <режим> [аргументы]` — все режимы пишут отчёт в консоль (перенаправляется в файл).
Запись в модели появится отдельным режимом `add` и только с копией `pre_`.

## Правила дома, уже вшитые
* **Эталон — из config.pro**, а не из головы: `template_solidpart`, `template_designasm`,
  `template_sheetmetalpart`. Creo-версии разрешаются: `mm_part.prt` → `mm_part.prt.1`.
* **Читаем оба вида уравнений**: обычные (`GetRelations`) и **пострегенерации**
  (`GetPostRegenerationRelations`) — там живёт `MASS = PRO_MP_MASS`.
* Рабочий каталог сессии сохраняется и возвращается на место; открытые модели убираются из сессии.
* Если живых сессий Creo несколько, JLINK даёт `XToolkitAmbiguous` — правило дома: **одна сессия Creo**.

## Приёмка (23.09.2026)
* `tpl-plan` на боевом config.pro: `mm_part.prt.1`, `sborka_mm.asm.1`, `mm_sheet.prt.1`,
  `pressforma-mm_mold.asm.1`, `komponovka_form_mm_cast.asm.1`, `sborka_mfg.asm.1` — файлы есть;
  **`template_mold_layout` (`mm_mold_lay.asm`) — файла нет (битая настройка)**;
  `template_drawing`, `template_boardpart`, `template_new_ecadasm` — через `$PRO_DIRECTORY\ШАБЛОНЫ[s]`
  (каталога нет, в `ШАБЛОНЫs` опечатка).
* `refs`/`scan` на живой сессии — в работе (сессия вышла во время пробы).
* STATUS: чтение — READY, запись (`add`) — НЕ ГОТОВО.
