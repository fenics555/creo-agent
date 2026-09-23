@echo off
rem Single-format re-check: neutral (verifies the "Creo version suffix" handling).
call "%~dp0creo_export.bat" neutral pin_splitk.prt > "%~dp0log_neu.txt" 2>&1
echo DONE >> "%~dp0log_neu.txt"
