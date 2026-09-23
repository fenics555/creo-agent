@echo off
rem skills_check_gui.bat — окно проверки скиллов (шапки, дубли, «краши») + отчёт.
setlocal
cd /d "%~dp0"
start "" pythonw.exe skills_check_gui.py
endlocal