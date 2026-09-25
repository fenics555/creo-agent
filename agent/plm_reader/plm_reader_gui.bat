@echo off
rem PLM Reader — запуск с окном (без консоли)
cd /d "%~dp0"
start "" pythonw "%~dp0plm_reader.py"
