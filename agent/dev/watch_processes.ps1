# НАБЛЮДЕНИЕ ЗА ЗАПУСКАМИ ПРОЦЕССОВ (живая находка 24.09.2026: хозяин просил починить моргание).
# Событийный подход: WMI сообщает каждый старт процесса — видно, ЧТО и с какой командной строкой стартует.
$log = 'D:\AI\log\reports\process_starts.txt'
"старт наблюдения $(Get-Date -Format 'HH:mm:ss')" | Set-Content -Path $log -Encoding UTF8
Unregister-Event -SourceIdentifier PSW -ErrorAction SilentlyContinue
Register-WmiEvent -Query "SELECT * FROM Win32_ProcessStartTrace" -SourceIdentifier PSW -Action {
    $e = $Event.SourceEventArgs.NewEvent
    $cmd = ""
    try {
        $p = Get-CimInstance Win32_Process -Filter ("ProcessId=" + $e.ProcessID) -ErrorAction SilentlyContinue
        if ($p) { $cmd = $p.CommandLine }
    } catch {}
    $line = "{0} | {1,-16} | {2}" -f (Get-Date -Format 'HH:mm:ss'), $e.ProcessName, $cmd
    Add-Content -Path 'D:\AI\log\reports\process_starts.txt' -Value $line -Encoding UTF8
}
Start-Sleep -Seconds 150
Unregister-Event -SourceIdentifier PSW -ErrorAction SilentlyContinue
"конец наблюдения $(Get-Date -Format 'HH:mm:ss')" | Add-Content -Path $log -Encoding UTF8
Write-Output "готово: $log"
