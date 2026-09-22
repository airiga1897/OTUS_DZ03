"""Проверить распределение HTTP и при явном --fault остановить одну службу web1."""

import argparse
from collections import Counter
import json
import subprocess
import time
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--mode", choices=["round_robin", "hash"], required=True)
    parser.add_argument("--fault", choices=["nginx", "php8.3-fpm"])
    parser.add_argument("--web1-ip")
    parser.add_argument("--ssh-user", default="otus")
    parser.add_argument("--key")
    parser.add_argument("--known-hosts")
    args = parser.parse_args()

    def get(path, health=True):
        request = urllib.request.Request(args.base_url.rstrip("/") + path,
                                         headers={"Host": args.host, "Cache-Control": "no-cache"})
        started = time.monotonic()
        with urllib.request.urlopen(request, timeout=25) as response:
            data = response.read()
            assert response.status == 200, response.status
            assert response.headers.get("X-LB-Method") == args.mode, dict(response.headers)
            node = response.headers.get("X-Backend-Node")
            assert node in ("web1", "web2"), node
            if health:
                decoded = json.loads(data)
                assert decoded == {"node": node, "database": "ok"}, decoded
            return node, round(time.monotonic() - started, 3)

    get("/", health=False)
    get("/static/index.html", health=False)
    paths = [f"/__lab/health/key-{i}" for i in range(40)]
    if args.mode == "round_robin":
        samples = [get(paths[0])[0] for _ in range(30)]
        assert set(samples) == {"web1", "web2"}, samples
        mapping = {path: get(path)[0] for path in paths}
    else:
        mapping = {path: get(path)[0] for path in paths}
        for _ in range(2):
            assert {path: get(path)[0] for path in paths} == mapping, "Hash нестабилен"
        samples = list(mapping.values())
        assert set(samples) == {"web1", "web2"}, samples
    print(json.dumps({"mode": args.mode, "distribution": dict(Counter(samples)),
                      "wordpress": "ok", "static": "ok"}), flush=True)
    if not args.fault:
        return
    if not all((args.web1_ip, args.key, args.known_hosts)):
        parser.error("Для --fault нужны --web1-ip, --key и --known-hosts")
    ssh = ["ssh", "-i", args.key, "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
           "-o", f"UserKnownHostsFile={args.known_hosts}", f"{args.ssh_user}@{args.web1_ip}",
           "sudo", "systemctl"]
    subprocess.run(ssh + ["is-active", "--quiet", args.fault], check=True)
    target_path = next(path for path, node in mapping.items() if node == "web1")
    try:
        subprocess.run(ssh + ["stop", args.fault], check=True)
        results = [get(target_path) for _ in range(12)]
        assert all(node == "web2" for node, _ in results), results
        print(json.dumps({"mode": args.mode, "stopped": f"web1/{args.fault}",
                          "requests": len(results), "all_served_by": "web2",
                          "max_seconds": max(t for _, t in results)}), flush=True)
    finally:
        subprocess.run(ssh + ["start", args.fault], check=True)
    deadline = time.monotonic() + 35
    while time.monotonic() < deadline:
        nodes = {get(path)[0] for path in paths}
        if nodes == {"web1", "web2"}:
            print(json.dumps({"recovered": f"web1/{args.fault}", "nodes": sorted(nodes)}), flush=True)
            break
        time.sleep(2)
    else:
        raise AssertionError("Восстановленный web1 не вернулся в балансировку")


if __name__ == "__main__":
    main()
