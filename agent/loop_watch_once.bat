@echo off
title loop_watch - one shot check
echo ==============================================
echo  loop_watch --once: checking newest session
echo ==============================================
python -X utf8 D:\AI\tools\agent\loop_watch.py --once
echo.
echo Exit code: %ERRORLEVEL%
echo Alert file: D:\AI\log\urn\cline\LOOP_ALERT.txt
pause