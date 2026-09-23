@echo off
rem Re-check: PDF export from a real DRAWING (knockout_1.drw + its part in the same folder).
call "%~dp0creo_export.bat" pdf "D:\AI\PROBA\drw_pdf\knockout_1.drw" > "%~dp0log_pdf.txt" 2>&1
echo DONE >> "%~dp0log_pdf.txt"
