# CREO EXPORT — экспорт модели из ЖИВОГО Creo (JLINK, без CREOSON)

**Что это.** Автономная программа (Java) для выгрузки модели из уже запущенного Creo:
STEP / IGES / VRML / PDF / NEUTRAL / DXF3D / STL. Работает **напрямую через JLINK**
(`pfcasync.jar` + `pfcasyncmt.dll`), CREOSON ей не нужен. После работы **Creo остаётся жив**.

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
- настройки окна — `gui_settings.json` рядом с программой. Класс Ж: нужен ЖИВОЙ Creo.

## КОНСОЛЬ
```
creo_export.bat <формат> <модель> [папка_вывода]
creo_export.bat step  pin_splitk.prt
creo_export.bat iges  pin_splitk.prt  D:\temp\out
creo_export.bat vrml  amf75838.asm
```
⚠️ **Звать только по ПОЛНОМУ пути** (живая находка 23.09.2026): при детач-запуске cmd может не найти
голое имя. Проверенная форма:
```
cmd /c call "D:\AI\tools\agent\creo_export\creo_export.bat" step pin_splitk.prt
```
Пакетная приёмка всех форматов: `cmd /c "D:\AI\tools\agent\creo_export\_test_all.bat"`
(пишет логи в `D:\AI\log\creo_export\`: `t_step.txt`, `t_iges.txt`, `t_vrml.txt`, `t_pdf.txt`, `t_neutral.txt`, `t_done.txt`).
- Требование: **Creo запущен** (иначе `AsyncConnection_Connect` не найдёт сессию).
  Подъём Creo: `CREO-START.bat` или `python D:\AI\tools\agent\ctl.py up`.
- Папка вывода по умолчанию — `creo_export\out`.
- Код возврата: `0` — всё выгрузилось, `1` — были отказы (смотри строки `FAIL`).
- Bat сам компилирует `CreoExport.java` (если нет `.class`) и сам копирует `pfcasync.jar`.

## Форматы
| формат | как создаётся | примечание |
|---|---|---|
| `step` | `pfcExport.STEP3DExportInstructions_Create(EXPORT_ASM_SINGLE_FILE, GeometryFlags.SetAsSolids)` | проверено: 13 466 б |
| `iges` | `pfcExport.IGES3DNewExportInstructions_Create(..., flags)` | проверено: 55 268 б |
| `vrml` | `pfcModel.VRMLModelExportInstructions_Create(папка)` + `Export("", instr)` | имя игнорируется, файл `<модель>_prt.wrl` |
| `pdf` | `pfcExport.PDFExportInstructions_Create()` + **`Model.Display()`** | **✓ для ЧЕРТЕЖА**: `OK knockout_1.pdf 26276 б`; на детали ✗ `XToolkitInvalidType` |
| `neutral` | `pfcExport.NEUTRALFileExportInstructions_Create()` | **✓ работает**, но Creo добавляет суффикс версии: файл ложится как `pin_splitk.neu.1` |
| `dxf3d` | `pfcExport.DXF3DExportInstructions_Create()` | не проверен |
| `stl` | `pfcModel.STLASCIIExportInstructions_Create("")` | не проверен |

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