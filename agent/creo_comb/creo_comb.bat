@echo off
rem ============================================================================
rem  ЧЕСАЛКА (CreoComb) — JLINK, без CREOSON
rem  usage: creo_comb.bat tpl-plan [config.pro]      - шаблоны из конфига (без Creo)
rem         creo_comb.bat dump <папка|файл> [имя]    - уравнения+параметры модели
rem         creo_comb.bat scan <папка> [config.pro]  - чего не хватает против шаблонов
rem  ВНИМАНИЕ: dump/scan требуют запущенного Creo (tpl-plan работает без него).
rem ============================================================================
setlocal
set "CREO=D:\PTC\CREO12\Creo 12.4.2.0\Common Files"
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
