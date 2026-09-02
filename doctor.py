# -*- coding: utf-8 -*-
import io
from pathlib import Path
AG = Path(r"D:\AI\tools\agent")
BASE = AG.parent
SHARE = Path(r"Z:\PTC\CREO-START\START-STD")

PS1 = r'''# netdiag.ps1 — диагностика сети машина -> CREO-START (без Python, чистый PowerShell)
$ErrorActionPreference = 'SilentlyContinue'
$share = "Z:\PTC\CREO-START\START-STD"
if (-not (Test-Path $share)) { $share = "\\192.168.88.159\PTC\CREO-START\START-STD" }
$outDir = Join-Path $share "netdiag"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
$log = Join-Path $outDir "$env:COMPUTERNAME.log"
$L = @()
$L += ("== " + (Get-Date -Format "yyyy-MM-dd HH:mm:ss") + " $env:COMPUTERNAME user=$env:USERNAME ==")
foreach ($a in (Get-NetAdapter | Where-Object Status -eq 'Up')) {
    $L += ("ADAPTER: {0} | {1} | Link={2} | MAC={3}" -f $a.Name, $a.InterfaceDescription, $a.LinkSpeed, $a.MacAddress)
}
$netuse = (net use Z: 2>$null | Out-String) -replace "\s+"," "
$L += ("NETUSE Z:" + $netuse.Trim())
$server = ""
if ($netuse -match '\\\\([A-Za-z0-9.\-]+)\\') { $server = $Matches[1] }
if ($server) {
    $p = Test-Connection -ComputerName $server -Count 3
    if ($p) {
        $lat = $p | ForEach-Object { if ($_.PSObject.Properties['Latency']) { $_.Latency } else { $_.ResponseTime } }
        $L += ("PING {0}: avg {1:N0} ms" -f $server, (($lat | Measure-Object -Average).Average))
    } else { $L += "PING $server: НЕТ ОТВЕТА" }
}
function Speed($mb) {
    $tmp = Join-Path $outDir "tmp_$env:COMPUTERNAME.bin"
    $data = New-Object byte[] ($mb * 1MB)
    $sw = [System.Diagnostics.Stopwatch]::StartNew(); [IO.File]::WriteAllBytes($tmp, $data); $w = $sw.Elapsed.TotalSeconds
    $sw = [System.Diagnostics.Stopwatch]::StartNew(); $null = [IO.File]::ReadAllBytes($tmp); $r = $sw.Elapsed.TotalSeconds
    Remove-Item $tmp -Force
    return ("SPEED {0} MB: запись {1:N1} MB/s | чтение {2:N1} MB/s" -f $mb, ($mb/$w), ($mb/$r))
}
$L += (Speed 1)
$L += (Speed 100)
$L | Out-File -FilePath $log -Encoding utf8 -Append
'''

nd = SHARE / "netdiag"
nd.mkdir(parents=True, exist_ok=True)
(nd / "netdiag.ps1").write_text(PS1, encoding="utf-8")
(AG / "netdiag.ps1").write_text(PS1, encoding="utf-8")
print("[+] netdiag.ps1 на шаре и локально")

bat = SHARE / "CREO-START.bat"
line = 'REM powershell -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0netdiag\\netdiag.ps1"'
if bat.exists():
    t = bat.read_text(encoding="utf-8", errors="ignore")
    if "netdiag.ps1" not in t:
        bat.write_text(t.rstrip() + "\n" + line + "\n", encoding="utf-8")
        print("[+] CREO-START.bat: строка добавлена (REM — раскомментируй руками)")
    else:
        print("[~] CREO-START.bat: строка уже есть")
else:
    print("[x] CREO-START.bat не найден на шаре")

# скан в отдельный процесс — веб больше не виснет
ap = AG / "agent.py"
a = ap.read_text(encoding="utf-8")
ch = False
if "import subprocess" not in a:
    a = a.replace("import json, re, socket, threading, time, datetime",
                  "import json, re, socket, threading, time, datetime, subprocess, sys", 1); ch = True
old1 = 'threading.Thread(target=scanner.index_all, daemon=True).start()'
new1 = 'subprocess.Popen([sys.executable, "-c", "import scanner; scanner.index_all()"], cwd=str(core.BASE))'
if old1 in a: a = a.replace(old1, new1, 1); ch = True
old2 = 'threading.Thread(target=scanner.scan_models, daemon=True).start()'
new2 = 'subprocess.Popen([sys.executable, "-c", "import scanner; scanner.scan_models()"], cwd=str(core.BASE))'
if old2 in a: a = a.replace(old2, new2, 1); ch = True
if ch:
    ap.write_text(a, encoding="utf-8")
    print("[+] agent: скан/индекс в отдельном процессе (GIL не душит веб)")
else:
    print("[~] agent: уже в отдельном процессе")
print("ГОТОВО: .\\AI_RESTART.bat")