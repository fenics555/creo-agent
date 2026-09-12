@echo off
set "ROOT=D:\AI\tools"
set "SLOG=%ROOT%\git_sync.log"
cd /d "%ROOT%"
git add -A
git commit -m "autosave %date% %time%" >> "%SLOG%" 2>&1
git push origin master >> "%SLOG%" 2>&1
exit /b 0

