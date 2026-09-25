@echo off
rem Re-check: PDF export from a real DRAWING (knockout_1.drw + its part in the same folder).
rem ЗАКОН ДОМА: логи программ пишем в D:\AI\log\<имя>\ (мигрировано 23.09.2026)
set "LOG=D:\AI\log\creo_export"
if not exist "%LOG%" mkdir "%LOG%"
call "%~dp0creo_export.bat" pdf "D:\AI\PROBA\drw_pdf\knockout_1.drw" > "%LOG%\log_pdf.txt" 2>&1
echo DONE >> "%LOG%\log_pdf.txt"
