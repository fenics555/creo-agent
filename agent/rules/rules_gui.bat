@echo off
REM Окно редактора правил дома (волна 4). Каркас ui_common.
chcp 65001 >nul
cd /d "%~dp0"
python -X utf8 gui.py