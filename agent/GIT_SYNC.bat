@echo off
set "ROOT=D:\AI\tools"
set "SLOG=%ROOT%\git_sync.log"
cd /d "%ROOT%"
git add -A
if %errorlevel% neq 0 exit /b %errorlevel%
git commit -m "autosave %date% %time%" >> "%SLOG%" 2>&1
if %errorlevel% neq 0 exit /b %errorlevel%
git push origin master >> "%SLOG%" 2>&1
exit /b %errorlevel%

