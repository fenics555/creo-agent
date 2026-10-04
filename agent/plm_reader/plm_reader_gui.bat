@echo off
rem PLM Reader - window launch (no console).
rem NOTE 04.10.2026 #1: line 2 was in Russian. cmd reads .bat in the system codepage, so UTF-8
rem Cyrillic in a comment became a COMMAND and the launch died with "Access is denied".
rem RULE for every .bat in this house: comments are ASCII only. No exceptions.
rem NOTE 04.10.2026 #2: background threads of this program print to stdout; under pythonw
rem without a console that print crashed the process and the window died after 4-8 seconds.
rem Redirecting the output to a log keeps the window alive. Hence no "start" here.
cd /d "%~dp0"
rem path: plm_reader -> agent -> tools -> D:\AI, so log is THREE levels up
if not exist "..\..\..\log\plm_reader" mkdir "..\..\..\log\plm_reader"
pythonw.exe "%~dp0plm_reader.py" >> "..\..\..\log\plm_reader\gui_run.log" 2>&1
