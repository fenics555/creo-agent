# ============================================================================
# bench_telemetry.ps1 — телеметрия локальных моделей Ollama (FIX 24.11.2026)
# ЧТО БЫЛО СЛОМАНО: список моделей строился как `ollama list | % { ($_ -split '\s+') }`
#   — брались ВСЕ токены строки, поэтому в отчёт попадали «ago», «days», «GB», «11», «18»
#   (сотни строк ERR/404) и те же модели задваивались под своими ID-хешами.
# ЧТО ТЕПЕРЬ: берём ПЕРВЫЙ токен строки (имя модели), уникализируем, чистые строки-IDs
#   не нужны — Ollama сам резолвит имя. Плюс параметр -Models для быстрой проверки.
# ЗАПУСК:
#   powershell -NoProfile -ExecutionPolicy Bypass -File bench_telemetry.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File bench_telemetry.ps1 -Models gemma4:26b,laguna-xs-2.1:latest
# ВЫХОД: консольная таблица + Markdown в D:\AI\log\urn\cline\bench_audit\BENCH_TELEMETRY_<дата>.md
# ============================================================================
param(
    [string[]]$Models = @(),
    [int]$NumCtx = 16384,
    [int]$NumPredict = 600,
    [string]$OutDir = 'D:\AI\log\urn\cline\bench_audit'
)

$outFile = Join-Path $OutDir ("BENCH_TELEMETRY_" + (Get-Date -Format 'yyyyMMdd_HHmm') + ".md")
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# --- ФИКС: только ИМЯ модели (первый токен), без мусора и без дублей по ID ---
if ($Models.Count -gt 0) {
    # при вызове через -File аргумент приходит одной строкой «a,b» — разбираем по запятой
    $use = @($Models | ForEach-Object { $_ -split ',' } | Where-Object { $_.Trim() } | ForEach-Object { $_.Trim() } | Select-Object -Unique)
} else {
    $use = ollama list | Select-Object -Skip 1 |
        ForEach-Object { ($_ -split '\s+')[0] } |
        Where-Object { $_ -and $_ -notmatch '(?i)embed' } |
        Select-Object -Unique
}
Write-Host ("Модели к замеру: " + ($use -join ', ')) -ForegroundColor Cyan

$bodyBase = @{
    messages = @(
        @{ role = 'system'; content = 'Ты агент с инструментами. Если пользователь просит вызвать функцию, вызови её без лишних предисловий.' },
        @{ role = 'user'; content = "Вызови инструмент check_health с параметром target='db'." }
    )
    stream = $false
    keep_alive = 0
    options = @{ num_ctx = $NumCtx; num_predict = $NumPredict; temperature = 0.0 }
    tools = @(@{
        type = 'function'
        function = @{
            name = 'check_health'
            description = 'Проверка состояния подсистемы'
            parameters = @{
                type = 'object'
                required = @('target')
                properties = @{ target = @{ type = 'string'; description = 'Имя модуля' } }
            }
        }
    })
}

$results = foreach ($m in $use) {
    Write-Host "Снимаю телеметрию: $m ..." -ForegroundColor Cyan
    $family = '-'; $params = '-'; $quant = '-'; $ctxMax = '-'
    try {
        $info = Invoke-RestMethod 'http://localhost:11434/api/show' -Method Post -Body (@{ model = $m } | ConvertTo-Json) -ContentType 'application/json' -TimeoutSec 15
        if ($info.details) { $family = $info.details.family; $params = $info.details.parameter_size; $quant = $info.details.quantization_level }
        if ($info.model_info) {
            # окно живёт в model_info.<arch>.context_length — имя архитектуры у моделей разное
            foreach ($p in $info.model_info.PSObject.Properties) {
                if ($p.Name -like '*context_length*') { $ctxMax = [int]$p.Value; break }
            }
        }
    } catch { }

    $b = $bodyBase.Clone(); $b.model = $m
    $json = $b | ConvertTo-Json -Depth 10
    try {
        $r = Invoke-RestMethod 'http://localhost:11434/api/chat' -Method Post -Body $json -ContentType 'application/json' -TimeoutSec 300
        $loadSec = [math]::Round($r.load_duration / 1e9, 2)
        $promptTps = if ($r.prompt_eval_duration -gt 0) { [math]::Round($r.prompt_eval_count / ($r.prompt_eval_duration / 1e9), 1) } else { 0 }
        $genTps = if ($r.eval_duration -gt 0) { [math]::Round($r.eval_count / ($r.eval_duration / 1e9), 1) } else { 0 }
        $thinkLen = 0
        if ($r.message.thinking) { $thinkLen = $r.message.thinking.Length }
        elseif ($r.message.content -match '(?s) thinking(.*?)</think>') { $thinkLen = $matches[1].Length }
        $hasTool = [bool]($r.message.tool_calls -and $r.message.tool_calls.Count -gt 0)
        $toolMode = 'НЕТ'
        if ($hasTool) { $toolMode = 'Native JSON' }
        elseif ($r.message.content -match '\{\s*"name"\s*:\s*"check_health"') { $toolMode = 'JSON в тексте' }
        elseif ($r.message.content -match 'check_health') { $toolMode = 'Текст/XML' }
        [PSCustomObject]@{
            'Модель' = $m; 'Семейство' = $family; 'Параметры' = $params; 'Квант' = $quant; 'ОкноMax' = $ctxMax
            'Загрузка (с)' = $loadSec; 'Чтение (ток/с)' = $promptTps; 'Генер. (ток/с)' = $genTps
            'Thinking (симв)' = $thinkLen; 'Вызов Tools' = $toolMode; 'Статус' = 'OK'
        }
    } catch {
        $err = ($_.Exception.Message -replace '\r?\n', ' ').Trim()
        [PSCustomObject]@{
            'Модель' = $m; 'Семейство' = $family; 'Параметры' = $params; 'Квант' = $quant; 'ОкноMax' = $ctxMax
            'Загрузка (с)' = 0; 'Чтение (ток/с)' = 0; 'Генер. (ток/с)' = 0
            'Thinking (симв)' = 0; 'Вызов Tools' = 'ERR'; 'Статус' = $err.Substring(0, [Math]::Min(90, $err.Length))
        }
    }
}

$sorted = $results | Sort-Object 'Генер. (ток/с)' -Descending
$sorted | Format-Table -AutoSize

$md = @(
    "# Телеметрия моделей Ollama ($(Get-Date -Format 'yyyy-MM-dd HH:mm')) — ctx=$NumCtx predict=$NumPredict temp=0",
    "",
    "| Модель | Семейство | Параметры | Квант | ОкноMax | Загрузка (с) | Чтение (ток/с) | Генер. (ток/с) | Thinking (симв) | Вызов Tools | Статус |",
    "|---|---|---|---|---:|---:|---:|---:|---:|---|---|"
)
foreach ($row in $sorted) {
    $md += "| $($row.'Модель') | $($row.'Семейство') | $($row.'Параметры') | $($row.'Квант') | $($row.'ОкноMax') | $($row.'Загрузка (с)') | $($row.'Чтение (ток/с)') | $($row.'Генер. (ток/с)') | $($row.'Thinking (симв)') | $($row.'Вызов Tools') | $($row.'Статус') |"
}
$md | Out-File -FilePath $outFile -Encoding UTF8
Write-Host "`nОтчёт сохранён в: $outFile" -ForegroundColor Green