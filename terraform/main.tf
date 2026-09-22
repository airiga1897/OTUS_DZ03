locals {
  nodes = {
    lb   = { host = 10, memory = 2, disk = 15, role = "lb" }
    web1 = { host = 11, memory = 2, disk = 15, role = "web" }
    web2 = { host = 12, memory = 2, disk = 15, role = "web" }
    db   = { host = 20, memory = 2, disk = 20, role = "db" }
  }
  addresses = { for name, node in local.nodes : name => cidrhost(var.subnet_cidr, node.host) }
  security_groups = {
    lb  = yandex_vpc_security_group.lb.id
    web = yandex_vpc_security_group.web.id
    db  = yandex_vpc_security_group.db.id
  }
}

data "yandex_compute_image" "ubuntu" {
  count  = var.image_id == null ? 1 : 0
  family = "ubuntu-2404-lts"
}

resource "yandex_vpc_network" "lab" {
  name = var.name_prefix
}

resource "yandex_vpc_gateway" "egress" {
  name = "${var.name_prefix}-nat"
  shared_egress_gateway {}
}

resource "yandex_vpc_route_table" "egress" {
  name       = "${var.name_prefix}-egress"
  network_id = yandex_vpc_network.lab.id

  static_route {
    destination_prefix = "0.0.0.0/0"
    gateway_id         = yandex_vpc_gateway.egress.id
  }
}

resource "yandex_vpc_subnet" "lab" {
  name           = var.name_prefix
  zone           = var.zone
  network_id     = yandex_vpc_network.lab.id
  v4_cidr_blocks = [var.subnet_cidr]
  route_table_id = yandex_vpc_route_table.egress.id
}

resource "yandex_vpc_address" "lb" {
  name = "${var.name_prefix}-lb"
  external_ipv4_address {
    zone_id = var.zone
  }
}

resource "yandex_compute_instance" "node" {
  for_each    = local.nodes
  name        = "${var.name_prefix}-${each.key}"
  hostname    = "${var.name_prefix}-${each.key}"
  platform_id = "standard-v3"
  zone        = var.zone

  labels = {
    project = var.name_prefix
    role    = each.value.role
  }

  resources {
    cores         = 2
    core_fraction = var.core_fraction
    memory        = each.value.memory
  }

  boot_disk {
    auto_delete = true
    initialize_params {
      image_id = var.image_id != null ? var.image_id : data.yandex_compute_image.ubuntu[0].id
      size     = each.value.disk
      type     = "network-hdd"
    }
  }

  network_interface {
    subnet_id          = yandex_vpc_subnet.lab.id
    ip_address         = local.addresses[each.key]
    nat                = each.key == "lb"
    nat_ip_address     = each.key == "lb" ? yandex_vpc_address.lb.external_ipv4_address[0].address : null
    security_group_ids = [local.security_groups[each.value.role]]
  }

  metadata = {
    user-data = "#cloud-config\n${yamlencode({
      users = [{
        name                = var.ssh_user
        groups              = ["sudo"]
        shell               = "/bin/bash"
        sudo                = ["ALL=(ALL) NOPASSWD:ALL"]
        lock_passwd         = true
        ssh_authorized_keys = [trimspace(file(pathexpand(var.ssh_public_key_path)))]
      }]
      ssh_pwauth = false
    })}"
  }
}
