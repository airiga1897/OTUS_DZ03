locals {
  project_root = abspath("${path.module}/..")
  # В Windows используется проектный venv, на Linux — .venv.
  deploy_python = fileexists("${local.project_root}/.tools/venv/Scripts/python.exe") ? "${local.project_root}/.tools/venv/Scripts/python.exe" : "${local.project_root}/.venv/bin/python"
  configuration_files = concat(
    [for name in sort(tolist(fileset("${path.module}/../ansible", "**"))) : "ansible/${name}" if !startswith(name, "inventory")],
    [for name in sort(tolist(fileset("${path.module}/../scripts", "*.py"))) : "scripts/${name}"],
    [for name in sort(tolist(fileset("${path.module}/../scripts", "*.sh"))) : "scripts/${name}"]
  )
}

# Заменяется только этап настройки, а не ВМ. Ошибка provisioner оставляет
# ресурс tainted: следующий apply повторит настройку без автоматического destroy.
resource "terraform_data" "configuration" {
  triggers_replace = {
    instances = { for name, node in yandex_compute_instance.node : name => node.id }
    public_ip = yandex_vpc_address.lb.external_ipv4_address[0].address
    ssh_user  = var.ssh_user
    addresses = local.addresses
    sources   = sha256(jsonencode({ for name in local.configuration_files : name => filesha256("${path.module}/../${name}") }))
  }

  depends_on = [yandex_vpc_security_group.lb, yandex_vpc_security_group.web, yandex_vpc_security_group.db, yandex_vpc_route_table.egress]

  lifecycle {
    precondition {
      condition     = fileexists(local.deploy_python) && fileexists("${local.project_root}/.local/secrets.yml") && fileexists("${local.project_root}/.local/otus_dz03")
      error_message = "Сначала подготовьте проектный Python venv, ключи, secrets.yml и авторизацию YC по README."
    }
  }

  provisioner "local-exec" {
    working_dir = local.project_root
    # Передаём путь к Python отдельным аргументом, без cmd.exe / shell quoting.
    interpreter = [local.deploy_python, "-u", "-c"]
    command     = "import runpy; runpy.run_path('scripts/apply_deploy.py', run_name='__main__')"
    environment = {
      PYTHONIOENCODING = "utf-8"
      # Не читаем terraform output внутри apply: outputs ещё могут быть не записаны.
      OTUS_LAB_JSON = jsonencode({
        lb_public_ip = yandex_vpc_address.lb.external_ipv4_address[0].address
        ssh_user     = var.ssh_user
        private_ips  = local.addresses
        instance_ids = { for name, node in yandex_compute_instance.node : name => node.id }
      })
    }
  }
}
