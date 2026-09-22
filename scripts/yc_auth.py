"""Получить IAM-токен, показывая ссылку входа, но не сам токен."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    executable = ROOT / ".tools" / ("yc.exe" if sys.platform == "win32" else "yc")
    process = subprocess.Popen(
        [str(executable), "--no-browser", "--config", str(ROOT / ".local/yc-config.yaml"),
         "iam", "create-token"],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
    )
    token = None
    for line in process.stdout:
        value = line.strip()
        if re.fullmatch(r"[A-Za-z0-9_.-]{80,}", value):
            token = value
        elif value:
            print(re.sub(r"(?<![A-Za-z0-9])[A-Za-z0-9_.-]{80,}", "<скрыто>", value), flush=True)
    if process.wait() != 0 or token is None:
        raise SystemExit("Не удалось получить IAM-токен. Секреты не выводились.")
    (ROOT / ".local/iam-token").write_text(token, encoding="utf-8")
    print("IAM-токен сохранён в исключённый из Git .local/iam-token.")


if __name__ == "__main__":
    main()
