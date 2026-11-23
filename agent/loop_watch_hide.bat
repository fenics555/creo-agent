@echo off
rem Background start: runs minimized. To stop - close the minimized window or kill python PID.
start "loop_watch" /min python -X utf8 D:\AI\tools\agent\loop_watch.py
echo loop_watch started in background (minimized).
echo Alert file: D:\AI\log\urn\cline\LOOP_ALERT.txt
timeout /t 3 >nul