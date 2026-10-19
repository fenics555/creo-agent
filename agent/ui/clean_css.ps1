$path = 'D:\AI\Tools\agent\ui\index.html'
$content = Get-Content $path -Raw
$htmlEnd = '</html>'
$htmlEndIdx = $content.LastIndexOf($htmlEnd)
if ($htmlEndIdx -ge 0) {
    $afterHtml = $content.Substring($htmlEndIdx + $htmlEnd.Length)
    $cssBlock = "/* RESIZE РУЧКИ (как в VS Code) */
.panel-toggle.dragging {
  background: #007acc !important;
  opacity: 0.8;
}
#main { position: relative; }
#sidebar { transition: none; }
#right { transition: none; }"
    if ($afterHtml.Trim() -eq $cssBlock.Trim()) {
        $content = $content.Substring(0, $htmlEndIdx + $htmlEnd.Length)
        $content | Set-Content $path -Encoding UTF8
        Write-Host "Дубликат после </html> удален. Размер:" (Get-Item $path).Length
    } else {
        Write-Host "После </html> иное содержимое, не удаляем"
        Write-Host "Содержимое после </html>: [" + $afterHtml.Trim() + "]"
    }
} else {
    Write-Host "</html> не найден"
}
Remove-Item $PSCommandPath -Force