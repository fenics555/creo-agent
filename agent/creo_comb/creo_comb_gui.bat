@echo off
rem creo_comb_gui.bat — окно «чесалки» Creo (режимы, аргументы, флаги записи, живой лог).
setlocal
cd /d "%~dp0"
start "" pythonw.exe gui.py
endlocal