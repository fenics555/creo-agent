$pids = (Get-NetTCPConnection -LocalPort 8765 -ErrorAction SilentlyContinue).OwningProcess
if ($pids) {
    $pids | Select-Object -Unique | ForEach-Object { 
        Write-Host "Killing PID: $_"
        Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue 
    }
} else {
    Write-Host "No processes found on port 8765"
}
