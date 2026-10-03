@echo off
REM Окно единого прогона проверок дома (волна 5).
chcp 65001 >nul
cd /d "%~dp0.."
python -X utf8 checks\gui.py