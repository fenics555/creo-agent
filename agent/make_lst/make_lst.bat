@echo off
rem make_lst.bat — запуск сборки файла ограничений параметров (класс Р, Creo не нужен).
rem   make_lst.bat                 — записать боевой list.lst (с бэкапом)
rem   make_lst.bat --dry           — только показать
rem   make_lst.bat --from refs.txt — сверить с отчётом чесалки и записать
setlocal
cd /d "%~dp0"
python make_lst.py %*
endlocal