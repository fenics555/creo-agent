@echo off
rem navigator_gui.bat — окно НАВИГАТОРА: поиск сборок, деталировка, PDF с «рыбьим глазом».
setlocal
cd /d "%~dp0"
start "" pythonw.exe gui.py
endlocal