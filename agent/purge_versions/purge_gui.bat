@echo off
rem purge_gui.bat — окно ЧИСТИЛЬЩИКА (настройки + план + чистка). Класс Р: Creo и агент не нужны.
setlocal
cd /d "%~dp0"
start "" pythonw.exe gui.py
endlocal