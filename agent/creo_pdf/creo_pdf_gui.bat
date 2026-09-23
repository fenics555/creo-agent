@echo off
rem ============================================================================
rem  CREO PDF — ОКНО: скан и обновление PDF рядом с чертежами (JLINK, без CREOSON)
rem  Движок: creo_pdf.bat (scan / export / config-find / config-read / config-load)
rem  Нужен Python в PATH. Для экспорта PDF — запущенный Creo.
rem ============================================================================
title CREO PDF — окно
cd /d "%~dp0"
python creo_pdf_gui.py
if errorlevel 1 pause
