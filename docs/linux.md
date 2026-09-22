# Работа с Linux

Инструкция для отдельного рабочего места Ubuntu 24.04 с Bash. Terraform и YC
работают на рабочем месте; Ansible — на ВМ lb. Credentials YC и Terraform state
на lb не переносить. Это инструкция для последующего запуска: полный цикл
с Linux-рабочего места пока не проверен. Она не предназначена для обхода
текущего обнаружения Python антивирусом на Windows.

## Новое рабочее место

Системные пакеты устанавливаются через apt, Python-зависимости — только в venv
проекта. Команды ниже не изменяют PATH и не требуют активации venv.

```bash
sudo apt-get update
sudo apt-get install -y git curl ca-certificates openssh-client python3 python3-venv
mkdir -p "$HOME/projects"
cd "$HOME/projects"
git clone --branch develop https://github.com/airiga1897/OTUS_DZ03.git
cd OTUS_DZ03
umask 077
mkdir -p .tools .local
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-local.txt
.venv/bin/python scripts/install_tools.py
export TF_CLI_CONFIG_FILE="$PWD/terraform.rc"
export YC_CLI_DISABLE_UPDATE_CHECK=1
export PYTHONIOENCODING=utf-8
.tools/terraform version
.tools/yc --no-browser --config "$PWD/.local/yc-config.yaml" version
```

Окружения Windows `.tools/venv` и Linux `.venv` не копируются между ОС:
на каждом рабочем месте venv создаётся заново. Инструменты Linux устанавливаются
в `.tools/terraform` и `.tools/yc`; установщик выбирает архитектуру машины.

## Доступ к YC и параметры нового стенда

Из корня проекта, в той же сессии Bash:

```bash
.tools/yc --no-browser --config "$PWD/.local/yc-config.yaml" init
.venv/bin/python scripts/prepare_local.py
.venv/bin/python -u scripts/yc_auth.py
chmod 700 .local
chmod 600 .local/otus_dz03 .local/secrets.yml .local/iam-token \
  .local/yc-config.yaml terraform/terraform.tfvars.json
```

Ссылку авторизации открыть вручную. Проверить выбранные cloud/folder и
`admin_cidrs` в локальном `terraform/terraform.tfvars.json`. При необходимости
на первой подготовке передать `--admin-cidr ВАШ_IP/32` в `prepare_local.py`.
При смене адреса отредактировать существующий tfvars и применить отдельный
Terraform plan. Скрипт не перезаписывает существующие параметры и секреты.

## Продолжение уже созданного стенда с другого компьютера

Один git clone не содержит состояние существующей инфраструктуры. До plan/apply
перенести по защищённому каналу из актуального рабочего каталога:

- `terraform/terraform.tfstate` и резервную копию state, если она есть;
- `terraform/terraform.tfvars.json`;
- `.local/otus_dz03`, `.local/otus_dz03.pub`, `.local/secrets.yml`.

Не создавать новые пароли и SSH-ключ вместо действующих. На новом рабочем месте
авторизоваться в том же cloud/folder через YC и получить новый IAM-токен.
Не переносить `.terraform`, venv и сохранённые планы между рабочими местами;
выполнить init и построить новый план. `.terraform.lock.hcl` берётся из Git.
Не работать одновременно с двумя копиями локального state: выбрать одно
рабочее место владельцем state, сохранить предыдущую копию как резервную.
Ограничить права перенесённых файлов командой `chmod 600`.

## Terraform

В каждой новой сессии перейти в корень проекта и определить функцию:

```bash
export TF_CLI_CONFIG_FILE="$PWD/terraform.rc"
tf() {
  YC_TOKEN="$(cat .local/iam-token)" .tools/terraform -chdir=terraform "$@"
}
tf init -input=false
tf fmt -check
tf validate
tf plan -input=false -out=../.local/otus-dz03.tfplan
tf show ../.local/otus-dz03.tfplan
# После проверки cloud/folder и всех изменений в плане:
tf apply ../.local/otus-dz03.tfplan
tf output
```

Функция передаёт токен только процессу Terraform. Не включать `set -x` при работе
с секретами. При истечении токена повторить `scripts/yc_auth.py` через `.venv/bin/python`.
Для существующего стенда неожиданный план повторного создания всех ВМ — повод
проверить state, а не выполнять apply.

## Подготовка и управление Ansible с рабочего места

```bash
.venv/bin/python -u scripts/controller.py prepare
.venv/bin/python -u scripts/controller.py run site.yml --syntax-check
.venv/bin/python -u scripts/controller.py run site.yml
.venv/bin/python -u scripts/controller.py run verify.yml
```

`prepare` автоматически получает SSH host keys через авторизованный YC API
до первого SSH-подключения. Отдельный `trust` нужен только для диагностики.
После успешного получения ключей `prepare` загружает
код, формирует inventory и устанавливает зависимости на lb. Коллекции входят
в пакет `ansible==14.4.0` из PyPI; отдельный доступ к API Galaxy не нужен.
При ошибке загрузки проверить доступ к PyPI и повторить prepare. Наличие
одного ansible-core ещё не означает готовность коллекций или приложения.

После изменения исходников:

```bash
.venv/bin/python -u scripts/controller.py upload
.venv/bin/python -u scripts/controller.py run site.yml
```

## Работа непосредственно на Linux-контроллере

Подключение с рабочего места после успешного `prepare`:

В проекте публичный адрес находится внутри output `lab`:

```bash
LB_IP="$(tf output -json lab | .venv/bin/python -c 'import json,sys; print(json.load(sys.stdin)["lb_public_ip"])')"
ssh -i .local/otus_dz03 -o IdentitiesOnly=yes \
  -o StrictHostKeyChecking=yes -o UserKnownHostsFile=.local/known_hosts "otus@$LB_IP"
```

В SSH-сессии на lb после успешного prepare:

```bash
cd /home/otus/otus-dz03/ansible
../.venv/bin/ansible-playbook site.yml --syntax-check
../.venv/bin/ansible-playbook site.yml
../.venv/bin/ansible-playbook verify.yml
../.venv/bin/ansible-playbook balance.yml -e nginx_lb_method=hash
../.venv/bin/ansible-playbook balance.yml -e nginx_lb_method=round_robin
```

Для повторной установки зависимостей непосредственно на lb:

```bash
cd /home/otus/otus-dz03
.venv/bin/python -m pip install -r ansible/requirements.txt
.venv/bin/ansible-galaxy collection list ansible.mysql
.venv/bin/ansible-galaxy collection list ansible.posix
```

Проверка обоих алгоритмов с остановкой Nginx и PHP-FPM на web1:

```bash
cd /home/otus/otus-dz03
# Заменить значение публичным IP из output lab на рабочем месте.
PUBLIC_IP=YOUR_LB_PUBLIC_IP
bash scripts/run_checks.sh "$PUBLIC_IP"
```

Этот сценарий временно останавливает службы web1 и возвращает round-robin.
При принудительном завершении или потере соединения проверить восстановление
служб по инструкции в README. Для проверки идемпотентности повторить site.yml;
ожидаемый результат — `changed=0`, без failed/unreachable.

## Удаление стенда

Выполнять **на рабочем месте с актуальным state**, не на удаляемой ВМ lb.
Сначала сохранить нужную БД и файлы uploads вне стенда. Удаляются четыре ВМ
вместе с дисками и управляемые этим state сетевые ресурсы.
Функцию `tf` определить как в разделе Terraform.

```bash
tf state list
tf plan -destroy -input=false -out=../.local/otus-dz03-destroy.tfplan
tf show ../.local/otus-dz03-destroy.tfplan
# После просмотра плана: следующая команда удаляет ресурсы
# без дополнительного интерактивного подтверждения.
tf apply ../.local/otus-dz03-destroy.tfplan
tf state list
```

После успешного apply список state должен быть пуст. Дополнительно проверить
в консоли YC отсутствие ресурсов DZ03. При частичной ошибке не удалять state:
устранить причину, построить и проверить новый destroy-план. Пустой state нового
клона не удалит ранее созданный стенд. Destroy по этой инструкции не выполнялся.
