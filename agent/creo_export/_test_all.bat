@echo off
rem Live acceptance test for creo_export.bat (5 formats against a running Creo).
rem NOTE: the bat MUST be called by full path - a bare "creo_export.bat" may not be
rem resolved by cmd when the launcher is started detached (living proof 23.09.2026).
set "SELF=%~dp0"
cd /d "%SELF%"
del /q t_*.txt 2>nul
call "%SELF%creo_export.bat" step    pin_splitk.prt > t_step.txt    2>&1
call "%SELF%creo_export.bat" iges    pin_splitk.prt > t_iges.txt    2>&1
call "%SELF%creo_export.bat" vrml    pin_splitk.prt > t_vrml.txt    2>&1
call "%SELF%creo_export.bat" pdf     pin_splitk.prt > t_pdf.txt     2>&1
call "%SELF%creo_export.bat" neutral pin_splitk.prt > t_neutral.txt 2>&1
echo ALL DONE > t_done.txt

