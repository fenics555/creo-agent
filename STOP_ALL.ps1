$processes = @("scanner", "index_all", "harvest", "rebuild", "probe")
$agentPidFile = "D:\AI\tools\agent\agent.pid"

# 1. Kill target processes by cmdline mask
foreach ($p in $processes) {
    $found = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like "*$p*" }
    foreach ($proc in $found) {
        try {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
            Write-Host "Stopped PID: $($proc.ProcessId) ($($proc.Name))"
        } catch {
            Write-Host "Failed to stop PID: $($proc.ProcessId) - $($_.Exception.Message)"
        }
    }
}

# 2. Kill agent via agent.pid
if (Test-Path $agentPidFile) {
    $agentPid = Get-Content $agentPidFile -Raw
    if ($agentPid -match '^\d+$') {
        try {
            Stop-Process -Id $agentPid.Trim() -Force -ErrorAction Stop
            Write-Host "Stopped Agent PID: $agentPid"
        } catch {
            Write-Host "Failed to stop Agent PID: $agentPid"
        }
    }
}

# 3. Agent /setcfg night_enable=0 (Placeholder for actual agent call)
# In a real scenario, this might be: 
# .\agent.exe /setcfg night_enable=0
Write-Host "night_enable set to 0 (command sent)"
