@echo off
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul
python D:\AI\tools\agent\ctl.py up --hidden
