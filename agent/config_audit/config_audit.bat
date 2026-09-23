@echo off
rem config_audit.bat — проверка ВСЕХ путей config.pro на диске (класс Р, Creo не нужен).
rem   config_audit.bat                 — проверить боевой Z:\PTC\CREO-START\START-STD\config.pro
rem   config_audit.bat <путь\config.pro> — проверить другой конфиг
setlocal
cd /d "%~dp0"
python config_audit.py %*
endlocal