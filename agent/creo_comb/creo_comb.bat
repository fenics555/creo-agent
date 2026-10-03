@echo off
rem ============================================================================
rem  ЧЕСАЛКА (CreoComb) — JLINK, без CREOSON
rem  usage: creo_comb.bat tpl-plan [config.pro]      - шаблоны из конфига (без Creo)
rem         creo_comb.bat dump <папка|файл> [имя]    - уравнения+параметры модели
rem         creo_comb.bat scan <папка> [config.pro]  - чего не хватает против шаблонов
rem  ВНИМАНИЕ: dump/scan требуют запущенного Creo (tpl-plan работает без него).
rem ============================================================================
setlocal
rem === ГДЕ БЕРЁМ CREO (02.10.2026) ==================================================
rem Путь ищет creo_find.py (единый поиск дома agent\agent\creo_path.py):
rem   1) боевой бат запуска Z:\PTC\CREO-START\START-STD\CREO-START.bat (CREO_EXE=…)
rem   2) настройки data\creo_comb_settings.json
rem   3) автопоиск D:\PTC\CREO*\Creo *\Common Files (берётся та, где есть x86e_win64\lib)
rem ЖИВАЯ НАХОДКА 03.10.2026 (аудит data\, Д8): запасной путь был зашит на CREO12 —
rem при переезде дома на CREO14 и сносе 12-й версии он стал бы битым. Теперь последний
rem рубеж — НОВЕЙШАЯ рабочая установка на диске (её тоже ищет python, без версии в коде).
set "CREO_FALLBACK="
for /f "delims=" %%i in ('python -X utf8 -c "import sys;sys.path.insert(0,r'%~dp0..');import creo_path;f=creo_path.creo_find_if_exists();print(f or '')"') do set "CREO_FALLBACK=%%i"
set "CREO="
for /f "delims=" %%i in ('python -X utf8 "%~dp0creo_find.py"') do set "CREO=%%i"
if not defined CREO set "CREO=%CREO_FALLBACK%"
if not defined CREO goto NO_CREO
if not exist "%CREO%\x86e_win64\obj\pro_comm_msg.exe" goto NO_CREO
echo CREO: %CREO%
goto CREO_OK
:NO_CREO
echo CREO NOT FOUND: "%CREO%" - нет pro_comm_msg.exe. Укажи путь в agent\data\creo_comb_settings.json (ключ creo_common)
exit /b 3
:CREO_OK
rem ==================================================================================
set "ARCH=%CREO%\x86e_win64"
set "JBIN=D:\AI\Java\bin"
set "PATH=%ARCH%\lib;%ARCH%\obj;%PATH%"
set "PRO_COMM_MSG_EXE=%ARCH%\obj\pro_comm_msg.exe"
cd /d "%~dp0"
if not exist "pfcasync.jar" copy /Y "%CREO%\text\java\pfcasync.jar" "pfcasync.jar" >nul
"%JBIN%\javac.exe" -encoding UTF-8 -cp "pfcasync.jar" CreoComb.java
if errorlevel 1 ( echo COMPILE FAILED & exit /b 1 )
"%JBIN%\java.exe" "-Djava.library.path=%ARCH%\lib;%ARCH%\obj" -Dstdout.encoding=UTF-8 -Dstderr.encoding=UTF-8 -cp ".;pfcasync.jar" CreoComb %*
exit /b %ERRORLEVEL%
