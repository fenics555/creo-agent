@echo off
rem ============================================================================
rem  CREO EXPORT (JLINK) - export a model from a RUNNING Creo. No CREOSON needed.
rem  usage: creo_export.bat FORMAT MODEL [outDir]
rem    FORMAT  step  Step     iges  IGES     vrml   VRML    pdf   PDF from a DRAWING
rem            neutral NEUTRAL    dxf3d DXF 3D  stl  STL ascii  stlb STL binary
rem    MODEL   file name as Creo sees it, e.g. pin_splitk.prt ; a FULL PATH is preferred -
rem            the engine switches the working folder itself
rem    outDir  default .\out - relative to this tool's folder, nothing absolute is hardcoded
rem  Creo must be running. Creo stays alive after the run.
rem
rem  PATHS ARE NOT HARDCODED: they come from settings\creo_export_settings.json; empty keys
rem  are filled by search - registry, all local drives, JAVA_HOME.
rem  Shared source of paths: ..\creo_pdf\creo_pdf_env.py
rem ============================================================================
setlocal
cd /d "%~dp0"
set "ENV_PY=%~dp0..\creo_pdf\creo_pdf_env.py"
if not exist "%ENV_PY%" goto NOENV
rem NOTE: exactly call %%L, NOT "call set %%L" - the latter makes set set NAME=... and stays empty
for /f "usebackq delims=" %%L in (`python -X utf8 "%ENV_PY%" --dump`) do call %%L
if not defined CREO_COMMON goto NOCOMMON
if not defined JAVA_BIN goto NOJAVA
set "ARCH=%CREO_COMMON%\x86e_win64"
if not exist "%ARCH%\lib\pfcasyncmt.dll" goto NODLL
if not exist "pfcasync.jar" if exist "%PFCA_SYNC%" copy /Y "%PFCA_SYNC%" "pfcasync.jar" >nul
if not exist "pfcasync.jar" goto NOJAR
set "PATH=%ARCH%\lib;%ARCH%\obj;%PATH%"
set "PRO_COMM_MSG_EXE=%ARCH%\obj\pro_comm_msg.exe"
rem always compile: sources may be newer than the previous .class
"%JAVA_BIN%\javac.exe" -encoding UTF-8 -cp "pfcasync.jar" CreoExport.java
if errorlevel 1 goto COMPILEFAIL
"%JAVA_BIN%\java.exe" -Dstdout.encoding=UTF-8 -Dstderr.encoding=UTF-8 "-Djava.library.path=%ARCH%\lib;%ARCH%\obj" -cp ".;pfcasync.jar" CreoExport %*
exit /b %ERRORLEVEL%

:NOENV
echo ERR: shared path source not found: "%ENV_PY%"
exit /b 2
:NOCOMMON
echo ERR: Creo Common Files not found.
echo FIX : python -X utf8 "%ENV_PY%" --set creo_install=...
exit /b 2
:NOJAVA
echo ERR: javac not found.
echo FIX : python -X utf8 "%ENV_PY%" --set java_bin=...
exit /b 2
:NODLL
echo ERR: no pfcasyncmt.dll in "%ARCH%\lib" - this is not a Creo Common Files folder.
exit /b 2
:NOJAR
echo ERROR: pfcasync.jar not found - neither next to this bat nor in the Creo installation
exit /b 1
:COMPILEFAIL
echo COMPILE FAILED
exit /b 1
