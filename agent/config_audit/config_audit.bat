@echo off
rem config_audit.bat — проверка ВСЕХ путей config.pro на диске (класс Р, Creo не нужен).
rem   config_audit.bat                 — проверить боевой Z:\PTC\CREO-START\START-STD\config.pro
rem   config_audit.bat <путь\config.pro> — проверить другой конфиг
setlocal
cd /d "%~dp0"
rem chcp 65001 + -X utf8: без них русский вывод в консоли идёт кракозябрами
rem (живая проверка 02.10.2026: было "����� CONFIG.PRO").
chcp 65001 > nul
python -X utf8 config_audit.py %*
endlocal & exit /b %ERRORLEVEL%