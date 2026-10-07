@echo off
rem PLM Reader - window launch (no console).
rem NOTE: comments ASCII only; cmd reads .bat in the system codepage.
rem NOTE: pythonw without a console crashes when the program prints, so stdout is redirected to a log.
rem Log location: house-wide D:\AI\log if this machine has it, else a "log" folder NEXT TO the tool.
rem DO NOT use "..\..\..\log": on a share copy (Z:\PTC\CREO-START\plm_reader) that lands in Z:\log.
cd /d "%~dp0"
set "LOGDIR=%~dp0log"
if exist "D:\AI\log" set "LOGDIR=D:\AI\log\plm_reader"
if not exist "%LOGDIR%" mkdir "%LOGDIR%"
pythonw.exe "%~dp0plm_reader.py" >> "%LOGDIR%\gui_run.log" 2>&1
