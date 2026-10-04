@echo off
rem PLM Reader - window launch (no console).
rem NOTE 04.10.2026: line 2 was in Russian with an em dash. cmd reads .bat in the system
rem codepage, so UTF-8 Cyrillic here became "is not recognized" on EVERY launch: a comment
rem was executed as a command. Comments in .bat must stay pure ASCII.
cd /d "%~dp0"
start "" pythonw "%~dp0plm_reader.py"
