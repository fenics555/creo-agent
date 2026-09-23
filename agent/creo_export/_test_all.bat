@echo off
rem Live acceptance test for creo_export.bat (5 formats against a running Creo).
rem NOTE: the bat MUST be called by full path - a bare "creo_export.bat" may not be
rem resolved by cmd when the launcher is started detached (living proof 23.09.2026).
rem ЗАКОН ДОМА: логи программ пишем в D:\AI\log\<имя>\ (мигрировано 23.09.2026)
set "SELF=%~dp0"
set "LOG=D:\AI\log\creo_export"
cd /d "%SELF%"
if not exist "%LOG%" mkdir "%LOG%"
del /q "%LOG%\t_*.txt" 2>nul
call "%SELF%creo_export.bat" step    pin_splitk.prt > "%LOG%\t_step.txt"    2>&1
call "%SELF%creo_export.bat" iges    pin_splitk.prt > "%LOG%\t_iges.txt"    2>&1
call "%SELF%creo_export.bat" vrml    pin_splitk.prt > "%LOG%\t_vrml.txt"    2>&1
call "%SELF%creo_export.bat" pdf     pin_splitk.prt > "%LOG%\t_pdf.txt"     2>&1
call "%SELF%creo_export.bat" neutral pin_splitk.prt > "%LOG%\t_neutral.txt" 2>&1
echo ALL DONE > "%LOG%\t_done.txt"

