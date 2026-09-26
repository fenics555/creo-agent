@echo off
rem GIT_SYNC.bat - autosave for D:\AI\tools (GitHub: creo-agent)
rem Usage: GIT_SYNC.bat ["commit message"]   (default: autosave <date> <time>)
rem Log: D:\AI\tools\git_sync.log (never committed).
rem NOTE: keep plain ASCII/ANSI - UTF-16 breaks cmd parsing.
set "ROOT=D:\AI\tools"
set "SLOG=%ROOT%\git_sync.log"
set "MSG=%~1"
if "%MSG%"=="" set "MSG=autosave %date% %time%"
cd /d "%ROOT%"
echo ===== %date% %time% ===== >> "%SLOG%"
echo message: %MSG% >> "%SLOG%"
git add -A
git diff --cached --quiet
if %errorlevel% equ 0 echo nothing to commit, working tree clean >> "%SLOG%"
if %errorlevel% equ 0 exit /b 0
git commit -m "%MSG%" >> "%SLOG%" 2>&1
if %errorlevel% neq 0 exit /b %errorlevel%
git push origin master >> "%SLOG%" 2>&1
exit /b %errorlevel%
