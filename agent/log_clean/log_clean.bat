@echo off
rem log_clean.bat — уборка логов без окна (класс Р). Без ключей — только план.
rem   log_clean.bat                       — план по D:\AI\log
rem   log_clean.bat --apply               — убрать старое В КОРЗИНУ
rem   log_clean.bat --apply --delete      — удалить навсегда
rem Коды возврата: 0 успех · 2 нет такой папки · 3 неверный --days · 4 ошибка выполнения.
rem ЖИВАЯ НАХОДКА 03.10.2026 (аудит): бат НЕ ПЕРЕДАВАЛ код возврата (`python …` без `exit /b`),
rem поэтому движок честно отдавал 2 и 3, а через bat всегда приходил 0. И не было `-X utf8` —
rem русский в консоли шёл кракозябрами (та же беда, что чинили в make_lst).
setlocal
chcp 65001 > nul
cd /d "%~dp0"
python -X utf8 engine.py %*
set RC=%ERRORLEVEL%
endlocal & exit /b %RC%