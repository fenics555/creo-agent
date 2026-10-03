@echo off
REM Окно планов задач plan_run на каркасе ui_common (волна 8).
chcp 65001 >nul
cd /d "%~dp0"
python -X utf8 gui.py
