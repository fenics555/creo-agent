@echo off
rem orphan_scan_gui.bat — окно поиска чертежей-сирот (настройки + осмотр + отчёт).
setlocal
cd /d "%~dp0"
start "" pythonw.exe gui.py
endlocal