@echo off
rem plm_tree V1 -- PLM "v lob" (CLI). Usage: plm_tree.bat scan | where MODEL | changes
cd /d "%~dp0"
python "%~dp0plm_tree.py" %*
