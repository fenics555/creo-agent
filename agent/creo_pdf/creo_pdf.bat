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
set "CREO=D:\PTC\CREO12\Creo 12.4.2.0\Common Files"
set "ARCH=%CREO%\x86e_win64"
set "JBIN=D:\AI\Java\bin"
set "PATH=%ARCH%\lib;%ARCH%\obj;%PATH%"
set "PRO_COMM_MSG_EXE=%ARCH%\obj\pro_comm_msg.exe"
cd /d "%~dp0"
if not exist "pfcasync.jar" copy /Y "%CREO%\text\java\pfcasync.jar" "pfcasync.jar" >nul
"%JBIN%\javac.exe" -encoding UTF-8 -cp "pfcasync.jar" CreoPdf.java
if errorlevel 1 ( echo COMPILE FAILED & exit /b 1 )
rem  Индекс имён моделей дома (для распознавания чертежей-сирот). Обновляем перед прогонами экспорта.
if /I "%1"=="export" ( python "%~dp0creo_pdf_names.py" --quiet )
if /I "%1"=="pdf"    ( python "%~dp0creo_pdf_names.py" --quiet )
"%JBIN%\java.exe" "-Djava.library.path=%ARCH%\lib;%ARCH%\obj" -Dstdout.encoding=UTF-8 -Dstderr.encoding=UTF-8 -cp ".;pfcasync.jar" CreoPdf %*
exit /b %ERRORLEVEL%
