@echo off
REM План пакетных параметров (без записи, без Creo).
chcp 65001 >nul
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
python -X utf8 batch_params\plan.py %*
exit /b %ERRORLEVEL%