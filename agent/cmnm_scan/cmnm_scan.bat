@echo off
rem cmnm_scan.bat — проверка без окна (класс Р, только чтение).
rem   cmnm_scan.bat <папка> [ещё папки] [--limit N]
rem  -X utf8: в отчёте есть стрелка «→», без utf8 печать может падать (живая находка 23.09.2026).
setlocal
cd /d "%~dp0"
python -X utf8 "%~dp0cmnm_scan.py" %*
exit /b %ERRORLEVEL%