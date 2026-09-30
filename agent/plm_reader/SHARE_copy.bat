@echo off
rem SHARE_copy.bat - copy PLM Reader for sharing WITHOUT data and settings.
rem "db" (database + cache) is skipped: the base is your data, not shared.
rem "settings" (settings.json + backup_settings) is skipped: each machine keeps its own.
rem The receiver gets code only and configures paths on first run.
rem Usage:  SHARE_copy.bat "D:\where\to\share\plm_reader"
setlocal
set "SRC=%~dp0"
set "DST=%~1"
if "%DST%"=="" echo Usage: SHARE_copy.bat "target folder" & pause & exit /b 1
robocopy "%SRC%" "%DST%" /E /XD db settings __pycache__ /XF *.db *.pyc *.bak settings.json scan_cache.json /NFL /NDL /NJH /NJS /NP
echo.
echo DONE. "db" and "settings" were NOT copied - share stays code-only.
echo Target: %DST%
pause
endlocal
