"""Установить инструменты в .tools; системный PATH не меняется."""

import argparse
import hashlib
import io
import json
import os
import platform
import shutil
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TERRAFORM_VERSION = "1.16.3"


def fetch(url):
    with urllib.request.urlopen(url, timeout=120) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reuse", type=Path, help="Каталог предыдущего проекта с .tools")
    args = parser.parse_args()
    system = {"Windows": "windows", "Linux": "linux"}[platform.system()]
    arch = {"AMD64": "amd64", "x86_64": "amd64", "aarch64": "arm64"}[platform.machine()]
    suffix = ".exe" if system == "windows" else ""
    target = ROOT / ".tools"
    target.mkdir(exist_ok=True)
    (ROOT / ".local").mkdir(exist_ok=True)
    for tool in ("terraform", "yc"):
        name = tool + suffix
        destination = target / name
        if destination.exists():
            print(f"Уже установлен: {destination}")
            continue
        if args.reuse:
            source = args.reuse / ".tools" / name
            shutil.copy2(source, destination)
            if hashlib.sha256(source.read_bytes()).digest() != hashlib.sha256(destination.read_bytes()).digest():
                raise RuntimeError(f"Ошибка копирования {name}")
        elif tool == "terraform":
            archive_name = f"terraform_{TERRAFORM_VERSION}_{system}_{arch}.zip"
            base = f"https://releases.hashicorp.com/terraform/{TERRAFORM_VERSION}/"
            sums = fetch(base + f"terraform_{TERRAFORM_VERSION}_SHA256SUMS").decode()
            expected = next(line.split()[0] for line in sums.splitlines() if line.split()[-1] == archive_name)
            archive = fetch(base + archive_name)
            if hashlib.sha256(archive).hexdigest() != expected:
                raise RuntimeError("Не совпала SHA256 архива Terraform")
            with zipfile.ZipFile(io.BytesIO(archive)) as package:
                destination.write_bytes(package.read(name))
        else:
            # Официальный HTTPS-дистрибутив YC CLI; версия записывается отдельно после установки.
            extension = "zip" if system == "windows" else "tar.gz"
            archive = fetch(f"https://storage.yandexcloud.net/yandexcloud-yc/release/yc_{system}_{arch}.{extension}")
            if system == "windows":
                with zipfile.ZipFile(io.BytesIO(archive)) as package:
                    member = next(n for n in package.namelist() if Path(n).name == name)
                    destination.write_bytes(package.read(member))
            else:
                with tarfile.open(fileobj=io.BytesIO(archive)) as package:
                    member = next(m for m in package.getmembers() if Path(m.name).name == name and m.isfile())
                    destination.write_bytes(package.extractfile(member).read())
        if system != "windows":
            os.chmod(destination, 0o755)
        print(f"Установлен: {destination}")
    manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in target.iterdir() if p.is_file()}
    (ROOT / ".local" / "tool-sha256.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
