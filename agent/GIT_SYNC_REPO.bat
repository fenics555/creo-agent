@echo off
rem GIT_SYNC_REPO.bat - autosave for D:\AI\repo (Cline, spec54 item2, 17.09.2026)
rem Sibling of GIT_SYNC.bat which covers D:\AI\tools only. Log lives in agent\data (never committed).
set "ROOT=D:\AI\repo"
set "SLOG=D:\AI\tools\agent\data\git_sync_repo.log"
cd /d "%ROOT%"
echo ===== %date% %time% ===== >> "%SLOG%"
git add -A
git diff --cached --quiet
if %errorlevel% equ 0 echo nothing to commit, working tree clean >> "%SLOG%"
if %errorlevel% equ 0 exit /b 0
git commit -m "autosave repo %date% %time%" >> "%SLOG%" 2>&1
if %errorlevel% neq 0 exit /b %errorlevel%
git push origin master >> "%SLOG%" 2>&1
exit /b %errorlevel%
