@echo off
rem make_lst_gui.bat — окно сборки файла ограничений параметров (list.lst).
setlocal
cd /d "%~dp0"
start "" pythonw.exe gui.py
endlocal