@echo off
rem drawing_audit.bat - аудит чертежа без Creo (класс Р). RC 0/1/2
cd /d %~dp0..
set PYTHONIOENCODING=utf-8
python -X utf8 drawing_audit\drawing_audit.py %*
exit /b %ERRORLEVEL%