#!/usr/bin/env bash
# Запускать на балансировщике: bash scripts/run_checks.sh PUBLIC_IP [WEB1_PRIVATE_IP]
set -euo pipefail
cd "$(dirname "$0")/.."
public_ip="${1:?Укажите публичный IP балансировщика}"
web1_ip="${2:-10.30.0.11}"

restore_mode() {
    (cd ansible && ../.venv/bin/ansible-playbook balance.yml -e nginx_lb_method=round_robin)
}
trap restore_mode EXIT

for method in round_robin hash; do
    (cd ansible && ../.venv/bin/ansible-playbook balance.yml -e "nginx_lb_method=$method")
    for service in nginx php8.3-fpm; do
        .venv/bin/python scripts/verify_http.py \
            --base-url http://127.0.0.1 --host "$public_ip" --mode "$method" \
            --fault "$service" --web1-ip "$web1_ip" --ssh-user "$(id -un)" \
            --key .local/otus_dz03 --known-hosts .local/known_hosts
    done
done
