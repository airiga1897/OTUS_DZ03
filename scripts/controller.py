"""Подготовка Linux-контроллера и запуск Ansible по SSH с проверкой ключей через YC."""

import argparse
import base64
import json
import os
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path

import paramiko
from yc_auth import get_token

ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".local"


def terraform_output():
    if "OTUS_LAB_JSON" in os.environ:
        return json.loads(os.environ["OTUS_LAB_JSON"])
    executable = ROOT / ".tools" / ("terraform.exe" if sys.platform == "win32" else "terraform")
    return json.loads(subprocess.check_output(
        [str(executable), "-chdir=terraform", "output", "-json", "lab"], cwd=ROOT))


def remote_exec(client, command):
    print(f"Выполнение на контроллере: {command}", flush=True)
    channel = client.get_transport().open_session()
    channel.set_combine_stderr(True)
    channel.exec_command(command)
    while not channel.exit_status_ready() or channel.recv_ready():
        if channel.recv_ready():
            sys.stdout.write(channel.recv(65536).decode("utf-8", errors="replace"))
            sys.stdout.flush()
        else:
            time.sleep(0.2)
    result = channel.recv_exit_status()
    if result:
        raise RuntimeError(f"Удалённая команда завершилась с кодом {result}")


def host_keys(lab):
    """Доверенный источник ключей — serial console через авторизованный API YC."""
    executable = ROOT / ".tools" / ("yc.exe" if sys.platform == "win32" else "yc")
    env = dict(os.environ)
    env["YC_IAM_TOKEN"] = get_token()
    lines = []
    for node, instance_id in lab["instance_ids"].items():
        found = None
        for attempt in range(30):
            raw = subprocess.check_output(
                [str(executable), "--no-browser", "--config", str(LOCAL / "yc-config.yaml"),
                 "compute", "instance", "get-serial-port-output", "--id", instance_id,
                 "--format", "json"], env=env)
            contents = json.loads(raw)["contents"]
            section = re.search(r"BEGIN SSH HOST KEY KEYS.*?END SSH HOST KEY KEYS", contents, re.S)
            found = re.search(r"ssh-ed25519\s+([A-Za-z0-9+/=]+)", section.group()) if section else None
            if found:
                break
            if attempt == 0:
                print(f"Ожидание ключа SSH в serial console: {node}", flush=True)
            time.sleep(5)
        if not found:
            raise RuntimeError(f"В доверенном выводе YC нет SSH host key для {node}; подключение запрещено")
        key = found[1]
        paramiko.Ed25519Key(data=base64.b64decode(key))
        addresses = [lab["private_ips"][node]]
        if node == "lb":
            addresses.append(lab["lb_public_ip"])
        lines.append(f"{','.join(addresses)} ssh-ed25519 {key}\n")
        print(f"Ключ {node} получен из YC serial console.", flush=True)
    (LOCAL / "known_hosts").write_text("".join(lines), encoding="utf-8")


def connect(lab):
    client = paramiko.SSHClient()
    client.load_host_keys(str(LOCAL / "known_hosts"))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(lab["lb_public_ip"], username=lab["ssh_user"], key_filename=str(LOCAL / "otus_dz03"),
                   look_for_keys=False, allow_agent=False, timeout=20, banner_timeout=30)
    return client


def upload(client, lab):
    base = f"/home/{lab['ssh_user']}/otus-dz03"
    remote_exec(client, f"mkdir -p {base}/.local {base}/ansible {base}/scripts && chmod 700 {base}/.local")
    sftp = client.open_sftp()

    def mkdir(path):
        try:
            sftp.stat(path)
        except FileNotFoundError:
            mkdir(str(Path(path).parent).replace('\\', '/'))
            sftp.mkdir(path, mode=0o755)

    for directory in ("ansible", "scripts"):
        for path in (ROOT / directory).rglob("*"):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            relative = path.relative_to(ROOT).as_posix()
            remote = f"{base}/{relative}"
            mkdir(remote.rsplit("/", 1)[0])
            # Текстовые файлы всегда LF, независимо от рабочего дерева Windows.
            with sftp.open(remote, "w") as target:
                target.write(path.read_text(encoding="utf-8").replace("\r\n", "\n"))
            sftp.chmod(remote, 0o644)
    for name in ("otus_dz03", "secrets.yml", "known_hosts"):
        sftp.put(str(LOCAL / name), f"{base}/.local/{name}")
        sftp.chmod(f"{base}/.local/{name}", 0o600)
    inventory = {"all": {"vars": {
        "ansible_user": lab["ssh_user"], "ansible_become": True,
        "ansible_ssh_private_key_file": f"{base}/.local/otus_dz03",
        "ansible_ssh_common_args": f"-o StrictHostKeyChecking=yes -o UserKnownHostsFile={base}/.local/known_hosts",
    }, "children": {
        "loadbalancer": {"hosts": {"lb": {"ansible_connection": "local", "ansible_host": "127.0.0.1",
            "private_ip": lab["private_ips"]["lb"], "public_ip": lab["lb_public_ip"]}}},
        "web": {"hosts": {node: {"ansible_host": lab["private_ips"][node],
                                 "private_ip": lab["private_ips"][node]} for node in ("web1", "web2")}},
        "database": {"hosts": {"db": {"ansible_host": lab["private_ips"]["db"],
                                      "private_ip": lab["private_ips"]["db"]}}},
    }}}
    with sftp.open(f"{base}/ansible/inventory.json", "w") as target:
        target.write(json.dumps(inventory, indent=2))
    sftp.chmod(f"{base}/ansible/inventory.json", 0o600)
    sftp.close()
    print("Исходники и только секреты DZ03 загружены. Credentials YC не копировались.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["deploy", "trust", "prepare", "upload", "run", "exec"])
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    lab = terraform_output()
    print(f"Балансировщик: {lab['lb_public_ip']} | Сайт: http://{lab['lb_public_ip']}", flush=True)
    if args.action in ("trust", "prepare", "deploy"):
        host_keys(lab)
    if args.action == "trust":
        return
    with connect(lab) as client:
        base = f"/home/{lab['ssh_user']}/otus-dz03"
        if args.action in ("prepare", "deploy", "upload"):
            upload(client, lab)
        if args.action in ("prepare", "deploy"):
            remote_exec(client, "sudo cloud-init status --wait && sudo apt-get update -qq && "
                        "sudo env DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv")
            remote_exec(client, f"cd {base} && python3 -m venv .venv && "
                        ".venv/bin/python -m pip install -r ansible/requirements.txt")
        if args.action == "deploy":
            for playbook_args in (("site.yml", "--syntax-check"),
                                  ("verify_balance.yml", "--syntax-check"),
                                  ("site.yml",), ("verify.yml",), ("verify_balance.yml",)):
                remote_exec(client, f"cd {base}/ansible && ../.venv/bin/ansible-playbook "
                            + shlex.join(playbook_args))
            print(f"Развёртывание, verify.yml и проверка балансировки завершены: http://{lab['lb_public_ip']}", flush=True)
        if args.action == "run":
            if not args.arguments:
                raise SystemExit("Укажите playbook, например site.yml --syntax-check")
            remote_exec(client, f"cd {base}/ansible && ../.venv/bin/ansible-playbook " + shlex.join(args.arguments))
        if args.action == "exec":
            remote_exec(client, " ".join(args.arguments))


if __name__ == "__main__":
    main()
