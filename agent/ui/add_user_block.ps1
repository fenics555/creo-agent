$path = 'D:\AI\Tools\agent\ui\index.html'
$content = Get-Content $path -Raw

$oldBtn = '  <button class="btn" id="btn-toggle-right">Статистика</button>'
$newBtn = $oldBtn + @"
  <div class="user-block" id="user-block" style="display:none;">
    <span class="user-name" id="user-name">—</span>
    <button class="btn-admin" id="btn-admin" style="display:none;">Админка</button>
    <button class="btn-logout" id="btn-logout">Выйти</button>
  </div>
"@
if ($content.Contains($oldBtn)) {
    $content = $content.Replace($oldBtn, $newBtn)
    Write-Host "Блок пользователя добавлен в заголовок"
} else {
    Write-Host "Предупреждение: не найдена кнопка btn-toggle-right"
}
$content | Set-Content $path -Encoding UTF8
Write-Host "Готово. Размер:" (Get-Item $path).Length
Remove-Item $PSCommandPath -Force