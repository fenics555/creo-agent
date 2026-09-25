@echo off
rem PLM Reader — запуск без окна (в консоли): plm_reader.bat --folder "Z:\PTC\Work" --csv items.csv
cd /d "%~dp0"
python "%~dp0plm_reader.py" %*
