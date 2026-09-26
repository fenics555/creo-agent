@echo off
rem SHARE_copy.bat - copy PLM Reader for sharing WITHOUT the database.
rem The "db" folder (plm_reader.db + scan_cache.json) is skipped on purpose:
rem the base is your data, it is not shared. The receiver builds its own base by scanning.
rem Usage:  SHARE_copy.bat "D:\where\to\share\plm_reader"
setlocal
set "SRC=%~dp0"
set "DST=%~1"
if "%DST%"=="" echo Usage: SHARE_copy.bat "target folder" & pause & exit /b 1
robocopy "%SRC%" "%DST%" /E /XD db _old __pycache__ /XF *.db *.pyc scan_cache.json gui_settings.json /NFL /NDL /NJH /NJS /NP
echo.
echo DONE. Database (db folder) was NOT copied - share stays code-only.
echo Target: %DST%
pause
endlocal
