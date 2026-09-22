"""Запустить настройку из Terraform, сохранив журнал и код возврата."""

from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    logs = ROOT / ".local" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log_path = logs / f"deploy-{datetime.now():%Y%m%d-%H%M%S-%f}.log"
    print(f"Журнал настройки: {log_path}", flush=True)
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    with log_path.open("w", encoding="utf-8") as log:
        with subprocess.Popen(
            [sys.executable, "-u", str(ROOT / "scripts/controller.py"), "deploy"],
            cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace",
        ) as process:
            for line in process.stdout:
                print(line, end="", flush=True)
                log.write(line)
                log.flush()
            result = process.wait()
    if result:
        print(f"Настройка не завершена. ВМ сохранены. Журнал: {log_path}", flush=True)
        print("Исправьте причину, создайте новый plan и повторите apply. Удаление — только отдельным destroy.", flush=True)
    return result


if __name__ == "__main__":
    sys.exit(main())
