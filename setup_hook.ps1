$hookPath = 'D:\AI\tools\.git\hooks\pre-push'
$testPath = 'D:\AI\tools\agent\plm_reader\tests\test_audit_fixes_v220.py'
$cmd = "pytest $testPath"

if (Test-Path $hookPath) {
    $content = Get-Content $hookPath -Raw
    if ($content -notlike "*$testPath*") {
        Add-Content $hookPath "`n$cmd"
        Write-Host "Test added to existing hook."
    } else {
        Write-Host "Test already exists in hook."
    }
} else {
    Set-Content $hookPath $cmd
    Write-Host "New hook created."
}
