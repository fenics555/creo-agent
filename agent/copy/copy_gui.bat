@echo off
rem copy_gui.bat — окно службы копирования/переименования (порт, старт/стоп, страница, лог).
setlocal
cd /d "%~dp0"
start "" pythonw.exe gui.py
endlocal