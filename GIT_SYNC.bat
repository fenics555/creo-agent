@echo off
cd /d D:\AI\tools\agent
git add -A
git commit -m "autosave agent %date% %time%" >nul 2>&1
git push >nul 2>&1
cd /d D:\AI\repo
git add -A
git commit -m "autosave repo %date% %time%" >nul 2>&1
git push >nul 2>&1