@echo off
rem ============================================================================
rem  CREO EXPORT (JLINK) - export a model from a RUNNING Creo. No CREOSON needed.
rem  usage: creo_export.bat <format> <model> [outDir]
rem    format: step | iges | vrml | pdf | neutral | dxf3d | stl
rem    model : file name as Creo sees it, e.g. pin_splitk.prt  /  amf75838.asm
rem    outDir: default <this folder>\out
rem  Creo must be running (CREO-START.bat / ctl.py up). Creo stays alive after run.
rem ============================================================================
setlocal
set "CREO=D:\PTC\CREO12\Creo 12.4.2.0\Common Files"
set "ARCH=%CREO%\x86e_win64"
set "JBIN=D:\AI\Java\bin"
set "PATH=%ARCH%\lib;%ARCH%\obj;%PATH%"
set "PRO_COMM_MSG_EXE=%ARCH%\obj\pro_comm_msg.exe"
cd /d "%~dp0"

if not exist "pfcasync.jar" (
  copy /Y "%CREO%\text\java\pfcasync.jar" "pfcasync.jar" >nul
)
if not exist "pfcasync.jar" (
  echo ERROR: pfcasync.jar not found in "%CREO%\text\java"
  exit /b 1
)
rem always compile: sources may be newer than the previous .class
"%JBIN%\javac.exe" -cp "pfcasync.jar" CreoExport.java
if errorlevel 1 ( echo COMPILE FAILED & exit /b 1 )
"%JBIN%\java.exe" "-Djava.library.path=%ARCH%\lib;%ARCH%\obj" -cp ".;pfcasync.jar" CreoExport %*
exit /b %ERRORLEVEL%
