@echo off
rem Single-format re-check: neutral (verifies the "Creo version suffix" handling).
rem ЗАКОН ДОМА: логи программ пишем в D:\AI\log\<имя>\ (мигрировано 23.09.2026)
set "LOG=D:\AI\log\creo_export"
if not exist "%LOG%" mkdir "%LOG%"
call "%~dp0creo_export.bat" neutral pin_splitk.prt > "%LOG%\log_neu.txt" 2>&1
echo DONE >> "%LOG%\log_neu.txt"
