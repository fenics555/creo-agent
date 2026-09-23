@echo off
rem log_clean_gui.bat — окно УБОРКИ ЛОГОВ (настройки + план + уборка). Класс Р: Creo и агент не нужны.
setlocal
cd /d "%~dp0"
start "" pythonw.exe gui.py
endlocal