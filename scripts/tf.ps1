# Запуск Terraform с локальным IAM-токеном. Пример: .\scripts\tf.ps1 plan '-out=../.local/otus-dz03.tfplan'
$taskRoot = Split-Path -Parent $PSScriptRoot
# Диагностика только интерактивного output без аргументов.
# Именованные outputs, -json, -raw и другие параметры обрабатывает Terraform.
if ($args.Count -eq 1 -and $args[0] -eq 'output') {
    $taskStatePath = Join-Path $taskRoot 'terraform/terraform.tfstate'
    if (Test-Path -LiteralPath $taskStatePath) {
        try {
            $taskState = Get-Content -LiteralPath $taskStatePath -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
            if ($taskState.version -eq 4 -and $null -ne $taskState.outputs -and
                @($taskState.resources).Count -eq 0 -and
                @($taskState.outputs.PSObject.Properties).Count -eq 0) {
                Write-Host 'Локальный Terraform state пуст: ресурсов и выходных значений нет.'
                Write-Host 'После destroy это нормально. Публичный IP появится после нового apply.'
                Write-Host 'Для развёртывания выполните plan, проверьте его и затем выполните apply.'
                exit 0
            }
        } catch {
            # Повреждённый или недоступный state диагностирует сам Terraform.
        }
    }
}
$env:TF_CLI_CONFIG_FILE = Join-Path $taskRoot 'terraform.rc'
$savedToken = $env:YC_TOKEN
try {
    $taskTokenPath = Join-Path $taskRoot '.local/iam-token'
    if (Test-Path -LiteralPath $taskTokenPath) {
        $env:YC_TOKEN = (Get-Content -LiteralPath $taskTokenPath -Raw).Trim()
    }
    & (Join-Path $taskRoot '.tools/terraform.exe') "-chdir=$taskRoot/terraform" @args
    $taskExitCode = $LASTEXITCODE
} finally {
    $env:YC_TOKEN = $savedToken
}
exit $taskExitCode
