@echo off
rem excel_gui.bat — окно просмотра спецификации XLSX (только чтение).
setlocal
cd /d "%~dp0"
start "" pythonw.exe gui.py
endlocal