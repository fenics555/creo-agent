@echo off
rem config_audit_gui.bat — окно проверки путей config.pro.
setlocal
cd /d "%~dp0"
start "" pythonw.exe gui.py
endlocal