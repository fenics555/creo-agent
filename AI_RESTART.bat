@echo off
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul
python D:\AI\tools\agent\ctl.py up --hidden
powershell -NoProfile -Command "$p=Get-Process ollama -ErrorAction SilentlyContinue; if($p){$n=(Get-CimInstance Win32_Processor).NumberOfLogicalProcessors; $leave=[Math]::Max(3,[int]($n*0.17)); $mask=[long]((1 -shl ($n-$leave))-1); $p.ProcessorAffinity=[IntPtr]$mask; $p.PriorityClass='BelowNormal'}"
