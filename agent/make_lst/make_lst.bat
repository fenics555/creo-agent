@echo off
rem make_lst.bat — запуск сборки файла ограничений параметров (класс Р, Creo не нужен).
rem   make_lst.bat                 — записать боевой list.lst (с бэкапом)
rem   make_lst.bat --dry           — только показать
rem   make_lst.bat --from refs.txt — сверить с отчётом чесалки и записать
rem   make_lst.bat --target <путь> — другой файл (для пробы)
rem Коды возврата: 0 — записано/показано; 2 — неверный ключ или не записалось.
rem ЖИВАЯ НАХОДКА 03.10.2026 (аудит): бат НЕ ПЕРЕДАВАЛ код возврата (`python …` без `exit /b`),
rem поэтому `make_lst.bat --nosuchkey` отдавал 0, хотя движок отдавал 2. И не было `-X utf8` —
rem русский в консоли шёл кракозябрами (та же беда, что у config_audit до его правки).
setlocal
chcp 65001 > nul
cd /d "%~dp0"
python -X utf8 make_lst.py %*
set RC=%ERRORLEVEL%
endlocal & exit /b %RC%