@echo off
rem GIT_SYNC_ALL.bat - ONE updater for both house GitHub repos.
rem   D:\AI\tools  -> github.com/fenics555/creo-agent   (code of the house)
rem   D:\AI\repo   -> github.com/fenics555/creo-repo    (rules, skills, specs)
rem Runs both autosave scripts, then prints final statuses and last commits.
setlocal
echo ============================================================
echo  GIT SYNC ALL  %date% %time%
echo ============================================================
echo [1/2] tools - creo-agent ...
call "D:\AI\tools\GIT_SYNC.bat"
echo [2/2] repo  - creo-repo ...
call "D:\AI\repo\GIT_SYNC_REPO.bat"

echo.
echo --- status: tools (creo-agent) ---
cd /d "D:\AI\tools"
git status -sb
git --no-pager log --oneline -1
echo --- status: repo (creo-repo) ---
cd /d "D:\AI\repo"
git status -sb
git --no-pager log --oneline -1
echo.
echo Logs: D:\AI\tools\git_sync.log  ^|  D:\AI\tools\agent\data\git_sync_repo.log
echo Note: if a parallel leg works at the same time, run "git add ^<your files^>"
echo       manually instead - "add -A" would carry its unfinished work.
echo                    .   .   .
pause
endlocal
