# CREO EXPORT V2 — экспорт модели из ЖИВОГО Creo (JLINK, без CREOSON)

**Что это.** Автономная программа (Java) для выгрузки модели из уже запущенного Creo:
STEP / IGES / VRML / PDF / NEUTRAL / DXF3D / STL. Работает **напрямую через JLINK**
(`pfcasync.jar` + `pfcasyncmt.dll`), CREOSON ей не нужен. После работы **Creo остаётся жив**.

## ГДЕ НАСТРАИВАЕТСЯ — ОДИН ФАЙЛ (V2)
```
creo_export\settings\creo_export_settings.json      ← единственный файл настроек окна
creo_export\settings\backup_settings\              ← бэкапы, ротация: последние 5 по времени
```
Поля: `settings_version`, `format`, `model`, `out`, `open_after`. Чужие ключи не теряются,
битый json не роняет окно (значения по умолчанию). Старый `gui_settings.json` из корня
мигрируется автоматически, копия уходит в `backup_settings`.
**Пути Creo и Java не зашиты в коде.** `creo_export.bat` берёт их из общего источника
`..\creo_pdf\creo_pdf_env.py`: файл настроек → реестр PTC → рекурсивный поиск
`…\Parametric\bin\parametric.exe` на всех локальных дисках → `JAVA_HOME`.
Задать вручную:
```
python -X utf8 ..\creo_pdf\creo_pdf_env.py --set creo_install=D:\PTC\CREO13\Creo 13.4.1.0\Parametric
```
**Папка вывода по умолчанию** — `.\out` относительно папки инструмента (никакого абсолютного пути).

**Зачем.** Когда рутины CREOSON не хватает: пачка экспортов, цикл по сотням моделей,
свой обработчик — берём этот инструмент (или копируем приём в свою программу).

## Запуск

## ОКНО С НАСТРОЙКАМИ
```
creo_export_gui.bat
```
- **Формат** (step, iges, vrml, pdf, neutral, dxf3d, stl), **Модель** (файл или имя модели в сессии Creo),
  **Папка вывода** (по умолчанию `creo_export\out`), галочка «открыть папку после выгрузки»;
- кнопка **ВЫГРУЗИТЬ** — запускает движок и показывает его вывод живьём; рядом **СТОП** (taskkill по дереву);
- кнопка **Проверить Creo** — ищет процесс `parametric.exe` (без запущенного Creo выгрузка не сработает);
- настройки окна — `settings\creo_export_settings.json` (см. выше). Класс Ж: нужен ЖИВОЙ Creo.

## КОНСОЛЬ
```
creo_export.bat <формат> <модель> [папка_вывода]
creo_export.bat step  pin_splitk.prt
creo_export.bat iges  "D:\AI\PROBA\famcopy2\pin_splitk.prt"  D:\temp\out
creo_export.bat pdf   "D:\...\чертеж.drw"
```
⚠️ **Звать только по ПОЛНОМУ пути к bat** (живая находка 23.09.2026): при детач-запуске cmd может
не найти голое имя. Проверенная форма:
```
cmd /c call "D:\AI\tools\agent\creo_export\creo_export.bat" step "D:\...\pin_splitk.prt"
```
⚠️ **Модель — полным путём** (живая находка 02.10.2026): с голым именем `pin_splitk.prt` выгрузка
падала `XToolkitNotFound`; с полным путём движок сам делает `ChangeDirectory` и работает.
Пакетная приёмка всех форматов: `cmd /c "D:\AI\tools\agent\creo_export\_test_all.bat"`
(логи в `D:\AI\log\creo_export\`; модели передаются `CE_TEST_MODEL` / `CE_TEST_DRW`).
- Требование: **Creo запущен** (иначе `AsyncConnection_Connect` не найдёт сессию).
  Подъём Creo: `CREO-START.bat` или `python D:\AI\tools\agent\ctl.py up`.
- Папка вывода по умолчанию — `.\out` (создаётся сама).
- Код возврата: `0` — всё выгрузилось, `1` — были отказы (смотри строки `FAIL` / `ФОРМАТ … НЕ ВЫГРУЖЕН`).
- Bat сам компилирует `CreoExport.java` (каждый раз — файл может быть новее класса) и сам копирует
  `pfcasync.jar` из установки Creo, если его нет рядом.

## ФОРМАТЫ — ПРОВЕРЕНО ЖИВЬЁМ 02.10.2026 (Creo 13.4.1.0)
| формат | результат | примечание |
|---|---|---|
| `step` | `OK pin_splitk.stp 13468 б` | работает |
| `iges` | `OK pin_splitk.igs 55268 б` | работает |
| `vrml` | `OK pin_splitk_prt.wrl 26233 б` | имя файла задаёт сам Creo, ловится `listExt` |
| `pdf` | `OK калибр.pdf 23305 б` | **только с ЧЕРТЕЖА**; на детали `XToolkitInvalidType` |
| `neutral` | `OK pin_splitk.neu.1 74020 б` | Creo добавляет суффикс версии (`.neu.1`, `.neu.2`…) |
| `dxf3d` | `OK pin_splitk.dxf 52584 б` | работает (в прежнем README было «не проверен») |
| `stl` | **`ФОРМАТ stl НЕ ВЫГРУЖЕН: XToolkitNotFound`** | ограничение среды: в этой сессии Creo не загружен модуль экспорта STL. Код выгрузки сверен со справкой PTC (`STLASCIIExportInstructions::Create(cipOptional)`) — ошибка не в коде |
| ошибка одного формата | не роняет прогон | печатается `ФОРМАТ … НЕ ВЫГРУЖЕН: <текст>`, затем `EXPORT DONE WITH FAILURES: N` и корректный `Disconnect` |

### Ошибка формата больше не убивает прогон (02.10.2026)
Раньше исключение из `Export` уходило в `main` и обрывало всё: не было ни `EXPORT DONE`, ни `Disconnect`.
Теперь каждый формат обёрнут в свой `try/catch`, причина печатается дословно.

## ИНСТРУМЕНТ АГЕНТА
`D:\AI\tools\agent\creo_export_tools.py` → инструмент **`creo_export`** (`approval: True`).
Реестр агента (`tools_registry.py`) подключает любой `*_tools.py` автоматически — правки реестра не нужно.
Живая проверка: `реестр: блок <creo_export_tools> подключён автоматически, инструментов: 1`.


### Пакетная приёмка 23.09.2026 (`_test_all.bat`)
| формат | итог |
|---|---|
| step | `OK pin_splitk.stp 13467 bytes` |
| iges | `OK pin_splitk.igs 55268 bytes` |
| vrml | `OK pin_splitk_prt.wrl 26233 bytes` |
| pdf | `OK knockout_1.pdf 26276 bytes` — **с чертежа** `knockout_1.drw` (деталь не годится) |
| neutral | `OK pin_splitk.neu.1 67100 bytes` (Creo добавил суффикс версии; повтор даёт `.neu.2`) |


## Приёмка (живой прогон 23.09.2026)
```
cwd=D:\AI\PROBA\famcopy2\
model=pin_splitk.prt fullname=PIN_SPLITK
format=step out=D:\AI\tools\agent\creo_export\out\
  OK pin_splitk.stp 13467 bytes
EXPORT OK
```
Вызов: `cmd /c "creo_export.bat step pin_splitk.prt"` (Creo запущен, cwd Creo = папка с моделью).

## PDF — ГЛАВНАЯ РУТИНА ДОМА (проверено 23.09.2026)
Три условия, без любого из них — отказ:
1. **Чертёж**, не деталь (на детали `XToolkitInvalidType`).
2. Рабочая папка Creo = папка чертежа, чтобы подтянулась его деталь:
   `session.ChangeDirectory(dir)` + `ModelDescriptor_CreateFromFileName(полный путь)`.
3. **`model.Display()`** перед экспортом — иначе `XToolkitNotDisplayed`.

```java
s.ChangeDirectory("D:\\AI\\PROBA\\drw_pdf");
Model d = s.RetrieveModel(pfcModel.ModelDescriptor_CreateFromFileName(
              "D:\\AI\\PROBA\\drw_pdf\\knockout_1.drw"));
d.Display();
d.Export("D:\\AI\\tools\\agent\\creo_export\\out\\knockout_1.pdf",
         pfcExport.PDFExportInstructions_Create());
```
Живой прогон:
```
cwd=D:\AI\PROBA\famcopy2\  →  cd=D:\AI\PROBA\drw_pdf\
model=knockout_1.drw fullname=KNOCKOUT_1
displayed
  OK knockout_1.pdf 26276 bytes
EXPORT OK
```
Сверка с домашней рутиной (CREOSON `interface:export_pdf`, Python/UTF-8):
```
creo:cd D:/AI/PROBA/drw_pdf                       → OK
file:open knockout_1.drw (display)                → OK
interface:export_pdf {file, filename, dirname, use_drawing_settings:true} → OK
```
Итог сверки: **JLINK 26 276 б** против **CREOSON 26 262 б**, оба `%PDF-1.7` (разница — от `use_drawing_settings`).

**Тонкая настройка PDF (JLINK):** `PDFExportInstructions.SetOptions(PDFOptions)` — список
`PDFOption{GetOptionType(), GetOptionValue()}`. Типы: `PDFOPT_SHEET_RANGE`, `PDFOPT_SHEETS`,
`PDFOPT_FONT_STROKE`, `PDFOPT_COLOR_DEPTH`, `PDFOPT_HIDDENLINE_MODE`, `PDFOPT_SEARCHABLE_TEXT`,
`PDFOPT_RASTER_DPI`, `PDFOPT_LAYER_MODE`, `PDFOPT_PARAM_MODE`, `PDFOPT_HYPERLINKS`,
`PDFOPT_BOOKMARK_ZONES/VIEWS/SHEETS/FLAG_NOTES`, `PDFOPT_TITLE/AUTHOR/SUBJECT/KEYWORDS`,
`PDFOPT_PASSWORD_TO_OPEN`, `PDFOPT_MASTER_PASSWORD`, `PDFOPT_RESTRICT_OPERATIONS`.
Также есть `SetProfilePath(...)` — профиль настроек PDF.

## Грабли (проверено живьём)
1. **DXF 2D/DWG на детали падают** (`XToolkitGeneralError`) — 2D-форматы требуют **чертёж**.
2. Путь `Creo 12.4.2.0` содержит пробелы → `-Djava.library.path` надо квотить ЦЕЛИКОМ,
   иначе JVM получит обрывок пути («Could not find or load main class 12.4.2.0\Common»).
3. `ParamValue` — не строка (нужен типовой геттер); русские имена/пути в консоли видны как `???`
   (данные при этом корректны, писать в файл UTF-8).
4. Среда обязательна: `PATH` += `x86e_win64\{lib,obj}`, `PRO_COMM_MSG_EXE`, `java.library.path`,
   иначе `UnsatisfiedLinkError: Can't find dependent libraries`.
5. **Модель — полным путём.** Голое `pin_splitk.prt` → `XToolkitNotFound`; полный путь движок
   разбирает сам (`ChangeDirectory` + `CreateFromFileName`) — проверено 02.10.2026.
6. **BAT = 100 % ASCII.** Кириллица в bat ломает разбор `cmd`: прогон молча обрывается.
   Русские пояснения — здесь в README, в bat только латиница.
7. **Скобки с `exit /b` внутри bat** дают пустой вывод и код 1 — ветки ошибок пишутся через
   `goto :label` (обойдено при переносе путей на общий источник 02.10.2026).
8. **`call set %%L` вместо `call %%L`** обнуляет переменные (получается `set set NAME=…`).
9. **`javac -encoding UTF-8`** обязателен при не-ASCII в исходнике, а **`-Dstdout.encoding=UTF-8`**
   иначе ломает кириллицу в выводе (было `model=������.drw`, стало `калибр.pdf`).
10. **Относительный `out` надо приводить к абсолютному ДО `mkdirs`** — иначе Creo получает путь
    относительно своей рабочей папки и отвечает `XToolkitInvalidDir`.
11. **Ошибка одного формата не должна обрывать прогон**: у каждого формата свой `try/catch`,
    иначе исключение уходит в `main`, теряются `EXPORT DONE` и `Disconnect`.
12. **«Работает» ≠ «настроено правильно»**: с зашитым `CREO=D:\PTC\CREO12\...` инструмент
    успешно подключался к живому **Creo 13** — DLL версионно-совместимы. Зашитый путь — мина.

## Состав
```
creo_export\
  CreoExport.java     - исходник (подключение, RetrieveModel, Export, Disconnect)
  creo_export.bat     - запуск: env + компиляция + java
  pfcasync.jar        - JLINK API PTC (копия из Creo\Common Files\text\java)
  out\                - результаты
```
Родня: пробы `D:\AI\PROBA\jlink_probe\DirectProbe{1,2,3}.java`; скилл
`D:\AI\repo\Creo\SKILL_creo_jlink_direct.md` (полное прямое управление Creo из программы).
## ЖИВЫЕ НАХОДКИ 23.09.2026 (приёмка через сам движок, Creo запущен)
1. **Имя модели — БЕЗ версии Creo.** `pdf d25.prt.1` → `XUnknownModelExtension`; `pdf d25.prt` принимается.
   (то же правило, что у CREOSON: версия `.1` считается расширением.)
2. **PDF выгружается из ЧЕРТЕЖА.** Из детали `d25.prt` → `XToolkitInvalidType` (для детали нужен чертёж).
   Проверено живьём: `pdf ыва.drw` → `OK ыва.pdf 17931 bytes`, `EXPORT OK`, код 0.
3. **Чертёж-сирота даёт `XToolkitNotFound`** — это НЕ поломка программы: модели рядом с чертежом нет,
   Creo такой чертёж открыть не может (см. `orphan_scan`). Проверено на `замена_шифров.drw`.
4. **Звать только по полному пути и лучше через батник-обёртку.** Запуск из PowerShell через
   `Start-Process cmd /c "creo_export.bat ... > файл"` калечит кавычки (`Синтаксическая ошибка в имени файла`).
   Надёжно: свой бат с `call "<полный путь>\creo_export.bat" pdf "<модель>" "<папка>" > файл 2>&1`
   или окно `creo_export_gui.bat`.