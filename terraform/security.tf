resource "yandex_vpc_security_group" "lb" {
  name       = "${var.name_prefix}-lb"
  network_id = yandex_vpc_network.lab.id

  ingress {
    protocol       = "TCP"
    port           = 80
    v4_cidr_blocks = ["0.0.0.0/0"]
    description    = "Публичный HTTP"
  }
  ingress {
    protocol       = "TCP"
    port           = 22
    v4_cidr_blocks = var.admin_cidrs
    description    = "SSH администратора и доступ через управляющий узел"
  }
  egress {
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "yandex_vpc_security_group" "web" {
  name       = "${var.name_prefix}-web"
  network_id = yandex_vpc_network.lab.id

  dynamic "ingress" {
    for_each = toset([22, 80])
    content {
      protocol          = "TCP"
      port              = ingress.value
      security_group_id = yandex_vpc_security_group.lb.id
    }
  }
  egress {
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "yandex_vpc_security_group" "db" {
  name       = "${var.name_prefix}-db"
  network_id = yandex_vpc_network.lab.id

  ingress {
    protocol          = "TCP"
    port              = 22
    security_group_id = yandex_vpc_security_group.lb.id
  }
  dynamic "ingress" {
    for_each = toset([3306, 2049])
    content {
      protocol          = "TCP"
      port              = ingress.value
      security_group_id = yandex_vpc_security_group.web.id
      description       = "MySQL или NFSv4 от веб-узлов"
    }
  }
  egress {
    protocol       = "ANY"
    v4_cidr_blocks = ["0.0.0.0/0"]
  }
}
