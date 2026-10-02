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
rem Single source of paths: next to this bat first, then a sibling tool.
set "ENV_PY=%~dp0creo_pdf_env.py"
if not exist "%ENV_PY%" set "ENV_PY=%~dp0..\creo_pdf\creo_pdf_env.py"
if not exist "%ENV_PY%" set "ENV_PY=%~dp0..\..\creo_pdf\creo_pdf_env.py"
rem NOTE: exactly call %%L, NOT "call set %%L" - the latter makes set set NAME=... and stays empty
if exist "%ENV_PY%" for /f "usebackq delims=" %%L in (`python -X utf8 "%ENV_PY%" --dump`) do call %%L
if not defined CREO_COMMON goto AUTOFIND
if not defined JAVA_BIN goto NOJAVA
goto HAVEPATHS

:AUTOFIND
rem Fallback: the tool searches Creo (registry) and javac by itself, with no external source.
echo shared path source not found - searching Creo and Java on this machine...
if not defined CREO_COMMON for /f "usebackq delims=" %%R in (`powershell -NoProfile -Command "(Get-ItemProperty 'HKLM:\SOFTWARE\PTC\PTC Creo Parametric\*' -Name CommonFilesLocation -ErrorAction SilentlyContinue).CommonFilesLocation -ne ''"`) do call set "CREO_COMMON=%%R"
if not defined CREO_COMMON goto NOCOMMON
if not defined JAVA_BIN (
  for /f "usebackq delims=" %%J in (`where javac.exe 2^>nul`) do if not defined JAVA_BIN call set "JAVA_BIN=%%~dpJ"
)
if not defined JAVA_BIN if defined JAVA_HOME if exist "%JAVA_HOME%\bin\javac.exe" set "JAVA_BIN=%JAVA_HOME%\bin"
if not defined JAVA_BIN goto NOJAVA

:HAVEPATHS
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

:NOCOMMON
echo ERR: Creo Common Files not found.
echo FIX : run once  python -X utf8 "..\creo_pdf\creo_pdf_env.py" --set creo_install=...
exit /b 2
:NOJAVA
echo ERR: javac not found.
echo FIX : run once  python -X utf8 "..\creo_pdf\creo_pdf_env.py" --set java_bin=...
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
