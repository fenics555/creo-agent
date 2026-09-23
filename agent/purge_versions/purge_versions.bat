@echo off
rem purge_versions.bat — ЧИСТИЛЬЩИК (движок, без окна). Класс Р: Creo и агент не нужны.
rem   purge_versions.bat -r <папка> -k 2            — показать план (ничего не переносится)
rem   purge_versions.bat -r <папка> -k 2 --execute  — перенести лишние версии в бэкап
setlocal
cd /d "%~dp0"
python engine.py --root %1 --keep %2 %3 %4 %5 %6
endlocal