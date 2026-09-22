output "lb_public_ip" {
  description = "Публичный IPv4 балансировщика; показывается после terraform apply."
  value       = yandex_vpc_address.lb.external_ipv4_address[0].address
}

output "site_url" {
  description = "Адрес WordPress через балансировщик."
  value = "http://${yandex_vpc_address.lb.external_ipv4_address[0].address}"
}

output "lab" {
  value = {
    lb_public_ip = yandex_vpc_address.lb.external_ipv4_address[0].address
    ssh_user     = var.ssh_user
    private_ips  = local.addresses
    instance_ids = { for name, node in yandex_compute_instance.node : name => node.id }
    image_id     = var.image_id != null ? var.image_id : data.yandex_compute_image.ubuntu[0].id
  }
}
