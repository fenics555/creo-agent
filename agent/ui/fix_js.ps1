$path = 'D:\AI\Tools\agent\ui\app.js'
$content = [System.IO.File]::ReadAllText($path)
# Исправляем сломанные $('...') которые превратились в (...) в PowerShell here-string
$content = $content -replace "login-screen\.classList", "$('login-screen').classList"
$content = $content -replace "user-block\.style", "$('user-block').style"
$content = $content -replace "btn-admin\.style", "$('btn-admin').style"
$content = $content -replace "btn-do-login", "$('btn-do-login')"
$content = $content -replace "btn-do-reg", "$('btn-do-reg')"
$content = $content -replace "btn-logout", "$('btn-logout')"
$content = $content -replace "btn-admin", "$('btn-admin')"
$content = $content -replace "login-login", "$('login-login')"
$content = $content -replace "login-pw", "$('login-pw')"
$content = $content -replace "login-screen", "$('login-screen')"
[System.IO.File]::WriteAllText($path, $content, ([System.Text.UTF8Encoding]::new($false)))
Write-Host 'Исправлено. Размер:' (Get-Item $path).Length
Remove-Item $PSCommandPath -Force