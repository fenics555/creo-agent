@echo off
rem skills_index_gui.bat — окно ПОИСКА ПО СМЫСЛУ (эмбеддинги скиллов дома). Класс Р: Creo не нужен; Ollama — только для поиска/перестройки индекса.
setlocal
cd /d "%~dp0"
start "" pythonw.exe gui.py
endlocal
