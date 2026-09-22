param([string]$ReuseProject = '')

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
Push-Location $taskRoot
try {
    if ($ReuseProject) {
        python scripts/install_tools.py --reuse $ReuseProject
    } else {
        python scripts/install_tools.py
    }
    if ($LASTEXITCODE -ne 0) { throw 'Не удалось установить Terraform и YC CLI.' }

    New-Item -ItemType Directory -Force .local/tmp | Out-Null
    $savedTemp = $env:TEMP
    $savedTmp = $env:TMP
    try {
        $env:TEMP = Join-Path $taskRoot '.local/tmp'
        $env:TMP = $env:TEMP
        python -m venv .tools/venv
        if ($LASTEXITCODE -ne 0) { throw 'Не удалось создать локальный Python venv.' }
        & ./.tools/venv/Scripts/python.exe -m pip install --disable-pip-version-check --no-cache-dir -r requirements-local.txt
        if ($LASTEXITCODE -ne 0) { throw 'Не удалось установить Python-зависимости.' }
    } finally {
        $env:TEMP = $savedTemp
        $env:TMP = $savedTmp
    }
    Write-Host 'Локальные инструменты готовы. Для текущей сессии: . .\scripts\env.ps1'
} finally {
    Pop-Location
}
