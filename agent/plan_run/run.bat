@echo off
REM Исполнение плана plan.json (волна 8). Без --approve шаги НЕ начинаются.
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
python -X utf8 plan_run\runner.py %*
exit /b %ERRORLEVEL%
