@echo off
powershell -NoProfile -Command "if ((curl.exe -s -o NUL -w '%%{http_code}' http://127.0.0.1:8765/status) -ne '200') { Start-Process -FilePath 'D:\AI\tools\agent\AI_RESTART.bat' -WindowStyle Hidden; Start-Sleep 25 }"
Start-Process python -ArgumentList "D:\AI\tools\agent\qa\qa_run.py" -WindowStyle Hidden -RedirectStandardOutput "D:\AI\tools\agent\data\tmp\qa_out.txt" -RedirectStandardError "D:\AI\tools\agent\data\tmp\qa_err.txt"
python -X utf8 dev\ui_check.py
python -X utf8 dev\ui_check.py
python -X utf8 dev\ui_check.py
python -X utf8 dev\ui_check.py
