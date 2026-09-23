@echo off
rem ============================================================================
rem  ДВОЙНИКИ (dup_scan) — отдельная программа класса Р: одинаковые файлы по sha1
rem  usage: dup_scan.bat <папка> [ещё папки] [--min-mb N] [--ext prt,asm,drw,pdf] [--apply]
rem  БЕЗ --apply ничего не меняет. С --apply лишние копии уходят в _trash_dup.
rem ============================================================================
setlocal
cd /d "%~dp0"
python -X utf8 "%~dp0dup_scan.py" %*
exit /b %ERRORLEVEL%
