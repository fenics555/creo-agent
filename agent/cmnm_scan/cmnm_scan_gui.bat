@echo off
rem cmnm_scan_gui.bat — окно проверки внутренних имён Creo (CMNM против имени файла).
setlocal
cd /d "%~dp0"
start "" pythonw.exe gui.py
endlocal