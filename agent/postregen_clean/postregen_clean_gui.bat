@echo off
REM ОКНО очистки пост-регенерации. Самостоятельная программа: без агента и без Cline.
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
python -X utf8 gui.py