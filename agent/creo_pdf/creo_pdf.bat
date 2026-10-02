@echo off
rem ============================================================================
rem  CREO PDF SCANNER (JLINK, без CREOSON)
rem  usage: creo_pdf.bat scan   <папка>              - отчёт: где нет PDF / PDF старше чертежа
rem         creo_pdf.bat export <папка> [лимит]      - создать недостающие/устаревшие PDF
rem         creo_pdf.bat pdf    <папка> <имя> [out]  - один чертёж
rem         creo_pdf.bat config-read [config.pro]   - ключевые опции живой сессии
rem         creo_pdf.bat config-load <config.pro>   - применить боевой config.pro
rem  ВНИМАНИЕ: export/pdf/config-* требуют запущенного Creo; scan работает без Creo.
rem ============================================================================
setlocal
cd /d "%~dp0"
rem --- ЕДИНЫЙ ИСТОЧНИК ПУТЕЙ: settings\creo_pdf_settings.json + автопоиск ---
rem     показать  python -X utf8 creo_pdf_env.py --show  |  --find-creo  |  --find-java
rem     задать    python -X utf8 creo_pdf_env.py --set creo_install=...
rem  ВАЖНО: именно call %%L, а НЕ "call set %%L" — иначе получится "set set NAME=..." и переменные пустые.
for /f "usebackq delims=" %%L in (`python -X utf8 "%~dp0creo_pdf_env.py" --dump`) do call %%L
rem  предупреждения — простым вызовом, БЕЗ for: текст с пробелами нельзя отдавать в bat через for
python -X utf8 "%~dp0creo_pdf_env.py" --warnings
rem  пути логов/индекса — из того же источника (инструмент может лежать на любом диске)
if not defined CREO_COMMON (
  echo ERR: не найден Common Files установки Creo.
  echo Задай путь: python -X utf8 "%~dp0creo_pdf_env.py" --set creo_common=...
  exit /b 2
)
if not defined JAVA_BIN (
  echo ERR: не найден javac.
  echo Задай путь: python -X utf8 "%~dp0creo_pdf_env.py" --set java_bin=...
  exit /b 2
)
set "ARCH=%CREO_COMMON%\x86e_win64"
if not exist "%ARCH%\lib\pfcasyncmt.dll" (
  echo ERR: в "%ARCH%\lib" нет pfcasyncmt.dll - это не Common Files установки Creo.
  exit /b 2
)
if not exist "pfcasync.jar" if exist "%PFCA_SYNC%" copy /Y "%PFCA_SYNC%" "pfcasync.jar" >nul
set "PATH=%ARCH%\lib;%ARCH%\obj;%PATH%"
set "PRO_COMM_MSG_EXE=%ARCH%\obj\pro_comm_msg.exe"
"%JAVA_BIN%\javac.exe" -encoding UTF-8 -cp "pfcasync.jar" CreoPdf.java
if errorlevel 1 ( echo COMPILE FAILED & exit /b 1 )
rem  Индекс имён моделей дома (для распознавания чертежей-сирот). Путь — из настроек.
if /I "%1"=="export" ( python "%~dp0creo_pdf_names.py" --quiet )
if /I "%1"=="pdf"    ( python "%~dp0creo_pdf_names.py" --quiet )
"%JAVA_BIN%\java.exe" "-Djava.library.path=%ARCH%\lib;%ARCH%\obj" -Dstdout.encoding=UTF-8 -Dstderr.encoding=UTF-8 -cp ".;pfcasync.jar" CreoPdf %*
exit /b %ERRORLEVEL%
