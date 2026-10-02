@echo off
rem orphan_scan.bat — движок из консоли (закон трёх рук: рука агента/планировщика).
rem -X utf8 и chcp 65001 — иначе кириллица в путях Z:\PTC\Work ломает вывод
rem (живая проверка 02.10.2026: в .bat не было ни того, ни другого).
setlocal
chcp 65001 > nul
python -X utf8 "%~dp0orphan_scan.py" %*
endlocal & exit /b %ERRORLEVEL%
