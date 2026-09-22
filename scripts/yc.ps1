# Передаёт аргументы YC CLI, всегда запрещая автоматический запуск браузера.
$taskRoot = Split-Path -Parent $PSScriptRoot
& (Join-Path $taskRoot '.tools/yc.exe') --no-browser --config (Join-Path $taskRoot '.local/yc-config.yaml') @args
exit $LASTEXITCODE
