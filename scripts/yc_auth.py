"""Получение IAM-токена только в памяти; значение не выводится."""

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def get_token():
    token = os.environ.get("YC_TOKEN", "").strip()
    if not token:
        executable = ROOT / ".tools" / ("yc.exe" if sys.platform == "win32" else "yc")
        result = subprocess.run(
            [str(executable), "--no-browser", "--config", str(ROOT / ".local/yc-config.yaml"),
             "iam", "create-token"],
            capture_output=True, text=True, encoding="utf-8",
        )
        if result.returncode:
            raise SystemExit("Не удалось получить IAM-токен. Выполните yc init через обёртку проекта с --no-browser.")
        token = result.stdout.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{80,}", token):
        raise SystemExit("Некорректный IAM-токен. Значение скрыто; проверьте авторизацию YC и YC_TOKEN.")
    return token


if __name__ == "__main__":
    get_token()
    print("Авторизация YC проверена. IAM-токен на диск не записывался.")
