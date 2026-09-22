# Подключение: . .\scripts\env.ps1. Меняется только текущая сессия PowerShell.
$taskRoot = Split-Path -Parent $PSScriptRoot
$env:TF_CLI_CONFIG_FILE = Join-Path $taskRoot 'terraform.rc'
$env:YC_CONFIG_PATH = Join-Path $taskRoot '.local\yc-config.yaml'
$env:YC_CLI_DISABLE_UPDATE_CHECK = '1'
$env:TF_IN_AUTOMATION = '1'
$env:PYTHONIOENCODING = 'utf-8'
Write-Host 'Профиль YC: .local/yc-config.yaml; Terraform: локальное зеркало провайдера.'
