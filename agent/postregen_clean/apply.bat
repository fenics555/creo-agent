@echo off
REM Запись плана в Creo. Без --approve запись НЕ начинается (RC 3).
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python -X utf8 apply.py %*
exit /b %ERRORLEVEL%