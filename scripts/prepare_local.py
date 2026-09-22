"""Подготовить отдельные ключи, секреты и параметры DZ03 из локального профиля YC."""

import argparse
import json
import secrets
import shutil
import urllib.request
from pathlib import Path

import yaml
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--previous", type=Path, help="Необязательный предыдущий проект с профилем YC")
    parser.add_argument("--admin-cidr", help="IPv4 адрес рабочего места с маской /32")
    args = parser.parse_args()
    local = ROOT / ".local"
    local.mkdir(exist_ok=True)
    profile = local / "yc-config.yaml"
    if not profile.exists():
        if not args.previous:
            parser.error("Сначала выполните scripts/yc.ps1 init или укажите --previous")
        shutil.copy2(args.previous / ".local" / "yc-config.yaml", profile)
        source_credentials = args.previous / ".local" / "credentials"
        if source_credentials.exists():
            shutil.copytree(source_credentials, local / "credentials", dirs_exist_ok=True)
    config = yaml.safe_load(profile.read_text(encoding="utf-8"))
    selected = config["profiles"][config["current"]]
    key = local / "otus_dz03"
    if not key.exists():
        private = Ed25519PrivateKey.generate()
        key.write_bytes(private.private_bytes(serialization.Encoding.PEM,
                                             serialization.PrivateFormat.OpenSSH,
                                             serialization.NoEncryption()))
        public = private.public_key().public_bytes(serialization.Encoding.OpenSSH,
                                                  serialization.PublicFormat.OpenSSH)
        key.with_suffix(".pub").write_bytes(public + b" otus-dz03\n")
    tfvars = ROOT / "terraform" / "terraform.tfvars.json"
    if not tfvars.exists():
        import ipaddress
        if args.admin_cidr:
            admin_cidr = str(ipaddress.IPv4Network(args.admin_cidr))
            if not admin_cidr.endswith('/32'):
                parser.error("--admin-cidr должен содержать один адрес /32")
        else:
            # При GeoPolicy зарубежный ipify может видеть другой выход, чем YC.
            with urllib.request.urlopen("https://ipv4-internet.yandex.net/api/v0/ip", timeout=20) as response:
                address = json.load(response)
            ipaddress.IPv4Address(address)
            admin_cidr = address + "/32"
        tfvars.write_text(json.dumps({
            "cloud_id": selected["cloud-id"],
            "folder_id": selected["folder-id"],
            "admin_cidrs": [admin_cidr],
            "ssh_public_key_path": "../.local/otus_dz03.pub",
        }, indent=2) + "\n", encoding="utf-8")
    secret_file = local / "secrets.yml"
    if not secret_file.exists():
        secret_file.write_text(yaml.safe_dump({
            "wordpress_db_password": secrets.token_urlsafe(32),
            "wordpress_admin_password": secrets.token_urlsafe(24),
            "wordpress_salts": {name: secrets.token_urlsafe(48) for name in (
                "AUTH_KEY", "SECURE_AUTH_KEY", "LOGGED_IN_KEY", "NONCE_KEY",
                "AUTH_SALT", "SECURE_AUTH_SALT", "LOGGED_IN_SALT", "NONCE_SALT")},
        }, sort_keys=False), encoding="utf-8")
    print("Профиль YC, отдельный SSH-ключ, tfvars и секреты DZ03 подготовлены; значения не выводятся.")


if __name__ == "__main__":
    main()
