rem ============================================================================
rem  MASS PROBE (JLINK) - MassProperty of a model from a RUNNING Creo. No CREOSON.
rem  usage: mass_probe.bat MODEL.prt [MODEL2.prt ...]
rem  prints:  NAME   MASS=%.17g   VOLUME=%.17g   AREA=%.17g
rem  Creo must be running. Creo stays alive after the run (Disconnect only).
rem  Paths come from settings\creo_export_settings.json via ..\creo_pdf\creo_pdf_env.py
rem ============================================================================
@echo off
setlocal
cd /d "%~dp0"
set "ENV_PY=%~dp0creo_pdf_env.py"
if not exist "%ENV_PY%" set "ENV_PY=%~dp0..\creo_pdf\creo_pdf_env.py"
if not exist "%ENV_PY%" set "ENV_PY=%~dp0..\..\creo_pdf\creo_pdf_env.py"
if exist "%ENV_PY%" for /f "usebackq delims=" %%L in (`python -X utf8 "%ENV_PY%" --dump`) do call %%L
if not defined CREO_COMMON goto AUTOFIND
if not defined JAVA_BIN goto NOJAVA
goto HAVEPATHS

:AUTOFIND
if not defined CREO_COMMON for /f "usebackq delims=" %%R in (`powershell -NoProfile -Command "(Get-ItemProperty 'HKLM:\SOFTWARE\PTC\PTC Creo Parametric\*' -Name CommonFilesLocation -ErrorAction SilentlyContinue).CommonFilesLocation -ne ''"`) do call set "CREO_COMMON=%%R"
if not defined CREO_COMMON goto NOCOMMON
if not defined JAVA_BIN for /f "usebackq delims=" %%J in (`where javac.exe 2^>nul`) do if not defined JAVA_BIN call set "JAVA_BIN=%%~dpJ"
if not defined JAVA_BIN if defined JAVA_HOME if exist "%JAVA_HOME%\bin\javac.exe" set "JAVA_BIN=%JAVA_HOME%\bin"
if not defined JAVA_BIN goto NOJAVA

:HAVEPATHS
set "ARCH=%CREO_COMMON%\x86e_win64"
if not exist "%ARCH%\lib\pfcasyncmt.dll" goto NODLL
if not exist "pfcasync.jar" if exist "%PFCA_SYNC%" copy /Y "%PFCA_SYNC%" "pfcasync.jar" >nul
if not exist "pfcasync.jar" goto NOJAR
set "PATH=%ARCH%\lib;%ARCH%\obj;%PATH%"
set "PRO_COMM_MSG_EXE=%ARCH%\obj\pro_comm_msg.exe"
"%JAVA_BIN%\javac.exe" -encoding UTF-8 -cp "pfcasync.jar" MassProbe.java
if errorlevel 1 goto COMPILEFAIL
"%JAVA_BIN%\java.exe" -Dstdout.encoding=UTF-8 -Dstderr.encoding=UTF-8 "-Djava.library.path=%ARCH%\lib;%ARCH%\obj" -cp ".;pfcasync.jar" MassProbe %*
exit /b %ERRORLEVEL%

:NOCOMMON
echo ERR: Creo Common Files not found.
exit /b 2
:NOJAVA
echo ERR: javac not found.
exit /b 2
:NODLL
echo ERR: no pfcasyncmt.dll in "%ARCH%\lib"
exit /b 2
:NOJAR
echo ERR: pfcasync.jar not found
exit /b 1
:COMPILEFAIL
echo COMPILE FAILED
exit /b 1