# sync_check.ps1 - compare code between main tool and shared working copy
$src = "D:\AI\tools\agent\plm_reader"
$dst = "Z:\PTC\CREO-START\plm_reader"
$excludeDirs = @("db", "settings", "__pycache__")

if (-not (Test-Path $dst)) {
    Write-Host "No access to share: $dst" -ForegroundColor Red
    exit 1
}

Write-Host "=== Diff: main tool -> share ===" -ForegroundColor Cyan

Get-ChildItem -Path $src -Filter "*.py" -Recurse -File | Where-Object {
    $rel = $_.FullName.Substring($src.Length + 1)
    $top = ($rel -split '\\')[0]
    ($excludeDirs -notcontains $top) -and ($rel -notmatch '\\__pycache__\\')
} | ForEach-Object {
    $rel = $_.FullName.Substring($src.Length + 1)
    $other = Join-Path $dst $rel
    if (-not (Test-Path $other)) {
        Write-Host ("  MISSING ON SHARE: " + $rel) -ForegroundColor Yellow
    } else {
        $h1 = (Get-FileHash $_.FullName -Algorithm MD5).Hash
        $h2 = (Get-FileHash $other -Algorithm MD5).Hash
        if ($h1 -ne $h2) {
            Write-Host ("  DIFFERS: " + $rel) -ForegroundColor Red
        }
    }
}

Write-Host "=== Done ===" -ForegroundColor Cyan
