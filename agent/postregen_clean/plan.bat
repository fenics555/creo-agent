@echo off
REM План очистки пост-регенерации (только чтение, записей нет).
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python -X utf8 plan.py %*
exit /b %ERRORLEVEL%