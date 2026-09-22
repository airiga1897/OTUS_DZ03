# Запуск Terraform с IAM-токеном в памяти. Пример: .\scripts\tf.ps1 plan '-out=../.local/otus-dz03.tfplan'
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
                Write-Host 'Это нормально перед первым развёртыванием и после destroy.'
                Write-Host 'Публичный IP и другие выходные значения появятся после успешного apply.'
                Write-Host 'Для развёртывания выполните plan, проверьте его и затем выполните apply.'
                exit 0
            }
        } catch {
            # Повреждённый или недоступный state диагностирует сам Terraform.
        }
    } else {
        Write-Host 'Локальный Terraform state ещё не создан: выходных значений нет.'
        Write-Host 'Перед первым развёртыванием это нормально.'
        Write-Host 'Выполните init, затем plan, проверьте план и выполните apply.'
        Write-Host 'После успешного apply появятся публичный IP и другие выходные значения.'
        exit 0
    }
}
& (Join-Path $taskRoot '.tools/venv/Scripts/python.exe') (Join-Path $taskRoot 'scripts/tf.py') @args
exit $LASTEXITCODE
