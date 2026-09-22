"""Запуск Terraform с IAM-токеном только в окружении дочернего процесса."""

import os
import subprocess
import sys
from yc_auth import ROOT, get_token


def main():
    env = dict(os.environ)
    env["TF_CLI_CONFIG_FILE"] = str(ROOT / "terraform.rc")
    # Локальные команды не требуют авторизации в облаке.
    local_commands = {"init", "fmt", "validate", "output", "show", "version", "providers"}
    if len(sys.argv) > 1 and sys.argv[1] not in local_commands:
        env["YC_TOKEN"] = get_token()
    executable = ROOT / ".tools" / ("terraform.exe" if sys.platform == "win32" else "terraform")
    return subprocess.call([str(executable), "-chdir=terraform", *sys.argv[1:]], cwd=ROOT, env=env)


if __name__ == "__main__":
    sys.exit(main())
