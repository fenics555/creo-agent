# netdiag.ps1 — диагностика сети машина -> CREO-START (без Python, чистый PowerShell)
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
