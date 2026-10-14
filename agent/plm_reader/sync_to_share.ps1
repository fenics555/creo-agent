# sync_to_share.ps1 - copy ONLY code from main tool to shared working copy
# Source: D:\AI\tools\agent\plm_reader   Target: Z:\PTC\CREO-START\plm_reader
# Excluded: db, settings, __pycache__, *.db, *.pyc (data/cache stay on share)
$ErrorActionPreference = "Stop"
$src = "D:\AI\tools\agent\plm_reader"
$dst = "Z:\PTC\CREO-START\plm_reader"

if (-not (Test-Path $dst)) {
    Write-Host "No access to share: $dst" -ForegroundColor Red
    exit 1
}

$excludeDirs = @("db", "settings", "__pycache__")
$includeExt = @("*.py", "*.ps1", "*.json", "*.md", "*.txt")
$copied = 0

foreach ($ext in $includeExt) {
    Get-ChildItem -Path $src -Filter $ext -Recurse -File | Where-Object {
        $rel = $_.FullName.Substring($src.Length + 1)
        $top = ($rel -split '\\')[0]
        ($excludeDirs -notcontains $top) -and ($rel -notmatch '\\__pycache__\\')
    } | ForEach-Object {
        $rel = $_.FullName.Substring($src.Length + 1)
        $target = Join-Path $dst $rel
        $targetDir = Split-Path $target -Parent
        if (-not (Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force | Out-Null }
        Copy-Item $_.FullName $target -Force
        $copied++
        Write-Host ("  = " + $rel)
    }
}

Write-Host ("Done: copied " + $copied + " files") -ForegroundColor Green
