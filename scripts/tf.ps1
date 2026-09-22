# Запуск Terraform с локальным IAM-токеном. Пример: .\scripts\tf.ps1 plan '-out=../.local/otus-dz03.tfplan'
$taskRoot = Split-Path -Parent $PSScriptRoot
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
