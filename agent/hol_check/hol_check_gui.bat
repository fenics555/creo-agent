@echo off
REM Окно проверки таблиц отверстий на каркасе ui_common (волна 3).
chcp 65001 >nul
cd /d "%~dp0"
python -X utf8 gui.py