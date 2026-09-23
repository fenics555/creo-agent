@echo off
rem log_clean.bat — уборка логов без окна (класс Р). Без ключей — только план.
rem   log_clean.bat                       — план по D:\AI\log
rem   log_clean.bat --apply               — убрать старое В КОРЗИНУ
rem   log_clean.bat --apply --delete      — удалить навсегда
setlocal
cd /d "%~dp0"
python engine.py %*
endlocal