@echo off
rem orphan_scan_gui.bat — окно поиска чертежей-сирот (настройки + осмотр + отчёт).
rem Настройки окна: D:\AI\tools\agent\data\orphan_scan_settings.json (не в папке инструмента).
setlocal
cd /d "%~dp0"
start "" pythonw.exe gui.py
endlocal