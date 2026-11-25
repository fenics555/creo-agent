@echo off
rem ПЕРЕНОСИМО: %~dp0 = папка этого .bat, работает на любой машине (без абсолютных путей).
title loop_watch - leg loop watcher (loop mode)
echo ==============================================
echo  loop_watch: watching newest Cline session
echo  poll 4 sec. Close this window to stop.
echo  Alert file: D:\AI\log\urn\cline\LOOP_ALERT.txt
echo ==============================================
python -X utf8 "%~dp0loop_watch.py"
echo.
echo loop_watch stopped. Exit code: %ERRORLEVEL%
pause