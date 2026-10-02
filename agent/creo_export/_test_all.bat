@echo off
rem Live acceptance test for creo_export.bat.
rem NOTE 1: call this bat BY FULL PATH - a bare "creo_export.bat" may not be resolved by cmd
rem         when the launcher starts detached (living proof 23.09.2026).
rem NOTE 2: MODELS MUST BE FULL PATHS - without them the export dies with XToolkitNotFound
rem         (this was the old defect here: bare "pin_splitk.prt" failed, full path works).
rem NOTE 3: logs go to D:\AI\log\creo_export\ (law of the house).
rem NOTE 4: THIS BAT IS ASCII ON PURPOSE. Non-ASCII (Cyrillic) in a .bat breaks cmd -
rem         the law of the house: bat = 100% ASCII, encoding must not matter.
rem         Pass test models via CE_TEST_MODEL / CE_TEST_DRW from the caller.
set "SELF=%~dp0"
set "LOG=D:\AI\log\creo_export"
if not defined CE_TEST_MODEL set "CE_TEST_MODEL=D:\AI\PROBA\famcopy2\pin_splitk.prt"
if not defined CE_TEST_DRW   set "CE_TEST_DRW=D:\AI\PROBA\pdftest\kalibr.drw"
cd /d "%SELF%"
if not exist "%LOG%" mkdir "%LOG%"
del /q "%LOG%\t_*.txt" 2>nul
call "%SELF%creo_export.bat" step    "%CE_TEST_MODEL%" > "%LOG%\t_step.txt"    2>&1
call "%SELF%creo_export.bat" iges    "%CE_TEST_MODEL%" > "%LOG%\t_iges.txt"    2>&1
call "%SELF%creo_export.bat" vrml    "%CE_TEST_MODEL%" > "%LOG%\t_vrml.txt"    2>&1
call "%SELF%creo_export.bat" neutral "%CE_TEST_MODEL%" > "%LOG%\t_neutral.txt" 2>&1
call "%SELF%creo_export.bat" dxf3d   "%CE_TEST_MODEL%" > "%LOG%\t_dxf3d.txt"   2>&1
rem PDF only from a DRAWING - a part gives XToolkitInvalidType.
rem CE_TEST_DRW must exist; if the drawing is missing this line is skipped, not fatal.
if exist "%CE_TEST_DRW%" call "%SELF%creo_export.bat" pdf "%CE_TEST_DRW%" > "%LOG%\t_pdf.txt" 2>&1
rem STL is a known limitation: XToolkitNotFound in this session (documented in README)
call "%SELF%creo_export.bat" stl     "%CE_TEST_MODEL%" > "%LOG%\t_stl.txt"     2>&1
echo ALL DONE > "%LOG%\t_done.txt"

