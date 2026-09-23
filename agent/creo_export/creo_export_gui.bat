@echo off
rem creo_export_gui.bat — окно выгрузки из живого Creo (формат, модель, папка вывода, лог).
setlocal
cd /d "%~dp0"
start "" pythonw.exe gui.py
endlocal