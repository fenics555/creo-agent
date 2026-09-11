@echo off
set SLOG=D:\AI\tools\git_sync.log
cd /d D:\AI\tools\agent
git add -A
git commit -m "autosave agent %date% %time%" >> data\tmp\git_sync.log 2>&1
git push >> data\tmp\git_sync.log 2>&1
cd /d D:\AI\repo
git add -A
git commit -m "autosave repo %date% %time%" >> data\tmp\git_sync.log 2>&1
git push >> data\tmp\git_sync.log 2>&1