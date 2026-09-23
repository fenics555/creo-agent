@echo off
rem dup_scan_gui.bat — окно ДВОЙНИКОВ (настройки + поиск + перенос в _trash_dup).
setlocal
cd /d "%~dp0"
start "" pythonw.exe gui.py
endlocal